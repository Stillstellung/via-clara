from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import requests
import os
import time
import json
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic

# Import new modules
from config import config
from constants import *
from scene_matcher import SceneMatcher
from api_utils import handle_lifx_response, error_response, success_response, validate_request_data
from auth import (
    get_db, get_current_user, get_user_permissions, user_is_admin,
    filter_lights, filter_scenes, can_control_light, get_user_allowed_selectors,
    require_admin, require_login, init_db
)
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# Default system prompt for Claude AI natural language processing
DEFAULT_SYSTEM_PROMPT = """You are a smart home assistant for LIFX lights. Based on the user's natural language request and the current state of lights and scenes, determine what actions to take.

Available actions:
1. Toggle individual lights: PUT /api/toggle/{light_id}
2. Activate scenes: PUT /api/scene/{scene_uuid}
3. Toggle room/group: PUT /api/group/{group_id}/toggle
4. Set light state (color/brightness): PUT /api/lights/{selector}/state with body containing state data

For setting colors and brightness, use action type 4 with these guidelines:
- Color formats: "red", "blue", "green", "white", "#ff0000", "hue:120 saturation:1.0", "kelvin:2700"
- Brightness: 0.0 to 1.0 (where 1.0 = 100%)
- ALWAYS include "power": "on" AND "brightness": 1.0 when setting colors (unless user specifies different brightness)
- Duration: 1.0 seconds (default)
- IMPORTANT: If a light has brightness: 0, you MUST set brightness in the request or it will remain invisible

CRITICAL: When referencing rooms/groups, you MUST use the EXACT group names and IDs from the provided context. Do not guess or invent room names.

SELECTOR FORMATS:
- Individual lights: Use "id:{light_id}" from the lights data
- Groups/rooms: Use "group_id:{group_id}" from the group data in lights
- All lights: Use "all"

IMPORTANT EXAMPLES:
- "make bedroom lights red" → First find lights with group.name containing "bedroom", then use "group_id:{actual_group_id}"
- "set living room to 50% brightness" → Find group with name containing "living", use "group_id:{actual_group_id}"
- "turn bedroom lights blue at 75% brightness" → Use exact group ID from context data

MULTI-ZONE DEVICES (LIFX Beam, Z Strip):
Multi-zone devices have individually addressable zones (typically 10 zones per Beam segment, 1 per corner).

Zone Selector Syntax:
- Single zone: "id:{light_id}|{zone}" (e.g., "id:d073d5123456|0" for zone 0)
- Zone range: "id:{light_id}|{start}-{end}" (e.g., "id:d073d5123456|0-4" for zones 0-4)
- All zones: "id:{light_id}" (no zone specifier - affects all zones with same color)

CREATING GRADIENTS ON MULTI-ZONE DEVICES:
- Gradients require MULTIPLE actions with different zone ranges
- Split zones evenly between colors
- Example: "purple and red gradient" on 10-zone Beam:
  * Action 1: Set zones 0-4 to purple using "id:{light_id}|0-4"
  * Action 2: Set zones 5-9 to red using "id:{light_id}|5-9"

IDENTIFYING MULTI-ZONE DEVICES:
- Look for product.name containing: "Beam", "Z", "Strip", "Lightstrip"
- Each light in context has "product" field with "name"
- If user mentions gradients/multiple colors for ONE device, treat as multi-zone
- For rooms with mixed devices, handle Beam separately from regular lights

IMPORTANT: You can ONLY control the lights shown in the context below. If the user asks about lights not in the context, explain that those lights are not available.

Return a JSON response with:
- "actions": array of action objects with "method", "endpoint", "description", and "body" (for state changes)
- "summary": brief description of what will be done
- "error": if the request cannot be fulfilled

Example responses:

Single light toggle:
{
  "actions": [
    {"method": "PUT", "endpoint": "/api/toggle/d073d5123456", "description": "Turn on bedroom light"}
  ],
  "summary": "Turning on the bedroom light"
}

Group color change:
{
  "actions": [
    {"method": "PUT", "endpoint": "/api/lights/group:bedroom/state", "body": {"power": "on", "color": "red", "brightness": 1.0, "duration": 1.0}, "description": "Set bedroom lights to red"}
  ],
  "summary": "Setting bedroom lights to red"
}

Multi-zone gradient (for Beam/Strip devices):
{
  "actions": [
    {"method": "PUT", "endpoint": "/api/lights/id:d073d5123456|0-4/state", "body": {"power": "on", "color": "purple", "brightness": 1.0, "duration": 1.0}, "description": "Set Beam zones 0-4 to purple"},
    {"method": "PUT", "endpoint": "/api/lights/id:d073d5123456|5-9/state", "body": {"power": "on", "color": "red", "brightness": 1.0, "duration": 1.0}, "description": "Set Beam zones 5-9 to red"}
  ],
  "summary": "Creating purple and red gradient on Beam"
}

Only return valid JSON. Do not include any other text."""

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'via-clara-secret-key-change-in-production')

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[FLASK_DEFAULT_RATE_LIMIT]
)

# Load credentials from config
LIFX_TOKEN = config.get('lifx_token')
CLAUDE_API_KEY = config.get('claude_api_key')
BASE_URL = LIFX_API_BASE_URL

def get_claude_client():
    """Get Claude client with current API key from config"""
    return anthropic.Anthropic(api_key=config.get('claude_api_key'))

def get_lifx_headers():
    """Get LIFX API headers with current token from config"""
    return {"Authorization": f"Bearer {config.get('lifx_token')}"}

class RateLimitTracker:
    def __init__(self):
        self.reset_time = 0
        self.remaining = LIFX_RATE_LIMIT_MAX

    def update_from_headers(self, response_headers):
        self.remaining = int(response_headers.get('X-RateLimit-Remaining', LIFX_RATE_LIMIT_MAX))
        self.reset_time = int(response_headers.get('X-RateLimit-Reset', time.time() + 60))

    def can_make_request(self):
        if time.time() > self.reset_time:
            self.remaining = LIFX_RATE_LIMIT_MAX
            return True
        return self.remaining > 0

rate_tracker = RateLimitTracker()

def make_lifx_request(method, url, **kwargs):
    if not rate_tracker.can_make_request():
        wait_time = rate_tracker.reset_time - time.time()
        return jsonify({"error": f"Rate limit exceeded. Wait {int(wait_time)} seconds"}), HTTP_RATE_LIMIT

    try:
        if method.upper() == 'GET':
            response = requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(url, **kwargs)

        rate_tracker.update_from_headers(response.headers)

        if response.status_code == HTTP_RATE_LIMIT:
            return jsonify({"error": "LIFX API rate limit exceeded"}), HTTP_RATE_LIMIT

        return response
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), HTTP_SERVER_ERROR


# ===========================
# AUTH ROUTES
# ===========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin')
def admin_page():
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return redirect('/login')
    return render_template('admin.html')


# ===========================
# MAIN ROUTES
# ===========================

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html',
                           user=user,
                           is_admin=user_is_admin(user),
                           is_logged_in=bool(session.get('user_id')))


@app.route('/api/auth/status')
def auth_status():
    """Return current auth state for the frontend."""
    user = get_current_user()
    return jsonify({
        'logged_in': bool(session.get('user_id')),
        'username': user.get('username') if user else 'guest',
        'is_admin': user_is_admin(user),
        'is_guest': bool(user.get('is_guest')) if user else True,
        'nlp_enabled': bool(user.get('nlp_enabled')) if user else False
    })


# ===========================
# SCOPED API ROUTES
# ===========================

@app.route('/api/lights')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_lights():
    response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=get_lifx_headers())
    if isinstance(response, tuple):
        return response

    user = get_current_user()
    lights_data = response.json()

    if user:
        lights_data = filter_lights(lights_data, user)

    return jsonify(lights_data)


@app.route('/api/scenes')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_scenes():
    response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=get_lifx_headers())
    if isinstance(response, tuple):
        return response

    user = get_current_user()
    scenes_data = response.json()

    if user:
        scenes_data = filter_scenes(scenes_data, user)

    return jsonify(scenes_data)


@app.route('/api/toggle/<selector>', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def toggle_light(selector):
    user = get_current_user()
    if not user:
        return error_response("Unauthorized", HTTP_UNAUTHORIZED)

    # Check permission for this selector
    check_selector = f"id:{selector}" if not selector.startswith('id:') and not selector.startswith('group') and selector != 'all' else selector
    if not can_control_light(user, check_selector):
        return error_response("You don't have permission to control this light", 403)

    # Rewrite "all" for non-admin
    effective_selector = selector
    if selector == 'all' and not user.get('is_admin'):
        effective_selector = get_user_allowed_selectors(user)
        if not effective_selector:
            return error_response("No lights available", 403)

    response = make_lifx_request('POST', f"{BASE_URL}/lights/{effective_selector}/toggle", headers=get_lifx_headers())
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})


@app.route('/api/scene/<scene_uuid>', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def activate_scene(scene_uuid):
    user = get_current_user()
    if not user:
        return error_response("Unauthorized", HTTP_UNAUTHORIZED)

    # Check scene permission
    if not user.get('is_admin'):
        perms = get_user_permissions(user['id'])
        if scene_uuid not in perms.get('scenes', set()):
            return error_response("You don't have permission to activate this scene", 403)

    response = make_lifx_request('PUT', f"{BASE_URL}/scenes/scene_id:{scene_uuid}/activate",
                          headers=get_lifx_headers())
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})


@app.route('/api/scenes/status/batch')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_all_scene_statuses():
    """Get status for all scenes using SceneMatcher"""
    try:
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=get_lifx_headers())
        if isinstance(lights_response, tuple):
            return lights_response

        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=get_lifx_headers())
        if isinstance(scenes_response, tuple):
            return scenes_response

        user = get_current_user()
        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        # Filter for user scope
        if user:
            scenes_data = filter_scenes(scenes_data, user)

        scene_statuses = {
            scene['uuid']: SceneMatcher.check_scene_status(scene, lights_data)
            for scene in scenes_data
        }

        return jsonify(scene_statuses)

    except Exception as e:
        return error_response(str(e), HTTP_SERVER_ERROR)


@app.route('/api/scene/<scene_uuid>/status')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_scene_status(scene_uuid):
    """Get status for a specific scene using SceneMatcher"""
    try:
        user = get_current_user()
        if user and not user.get('is_admin'):
            perms = get_user_permissions(user['id'])
            if scene_uuid not in perms.get('scenes', set()):
                return error_response("Scene not found", HTTP_NOT_FOUND)

        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=get_lifx_headers())
        if isinstance(lights_response, tuple):
            return lights_response

        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=get_lifx_headers())
        if isinstance(scenes_response, tuple):
            return scenes_response

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        target_scene = next(
            (scene for scene in scenes_data if scene['uuid'] == scene_uuid),
            None
        )

        if not target_scene:
            return error_response("Scene not found", HTTP_NOT_FOUND)

        status = SceneMatcher.check_scene_status(target_scene, lights_data)
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e), "active": False}), HTTP_SERVER_ERROR


@app.route('/api/scene/<scene_uuid>/debug')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def debug_scene_status(scene_uuid):
    """Debug endpoint - admin only"""
    user = get_current_user()
    if not user_is_admin(user):
        return error_response("Admin access required", 403)

    try:
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=get_lifx_headers())
        if isinstance(lights_response, tuple):
            return lights_response

        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=get_lifx_headers())
        if isinstance(scenes_response, tuple):
            return scenes_response

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        target_scene = next(
            (scene for scene in scenes_data if scene['uuid'] == scene_uuid),
            None
        )

        if not target_scene:
            return error_response("Scene not found", HTTP_NOT_FOUND)

        debug_states = []
        for scene_state in target_scene.get('states', []):
            selector = scene_state.get('selector')
            matching_lights = SceneMatcher.find_matching_lights(lights_data, selector)

            state_debug = {
                "selector": selector,
                "expected": {
                    "power": scene_state.get('power'),
                    "brightness": scene_state.get('brightness'),
                    "color": scene_state.get('color')
                },
                "matching_lights": []
            }

            for light in matching_lights:
                light_debug = {
                    "name": light.get('label'),
                    "id": light.get('id'),
                    "actual": {
                        "power": light.get('power'),
                        "brightness": light.get('brightness'),
                        "color": light.get('color')
                    },
                    "matches": {
                        "power": SceneMatcher.check_power_match(light, scene_state),
                        "brightness": SceneMatcher.check_brightness_match(light, scene_state),
                        "color": SceneMatcher.check_color_match(light, scene_state),
                        "overall": SceneMatcher.light_matches_state(light, scene_state)
                    }
                }
                state_debug["matching_lights"].append(light_debug)

            state_debug["state_matched"] = any(
                l["matches"]["overall"] for l in state_debug["matching_lights"]
            )
            debug_states.append(state_debug)

        matched_count = sum(1 for s in debug_states if s["state_matched"])
        total_states = len(debug_states)

        return jsonify({
            "scene_name": target_scene.get('name'),
            "scene_uuid": scene_uuid,
            "matched_states": matched_count,
            "total_states": total_states,
            "match_percentage": round((matched_count / total_states) * 100, 1) if total_states > 0 else 0,
            "threshold": SCENE_MATCH_THRESHOLD * 100,
            "is_active": (matched_count / total_states) >= SCENE_MATCH_THRESHOLD if total_states > 0 else False,
            "states": debug_states
        })

    except Exception as e:
        return error_response(str(e), HTTP_SERVER_ERROR)


@app.route('/api/group/<group_id>/toggle', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def toggle_group(group_id):
    user = get_current_user()
    if not user:
        return error_response("Unauthorized", HTTP_UNAUTHORIZED)

    if not can_control_light(user, f"group_id:{group_id}"):
        return error_response("You don't have permission to control this group", 403)

    response = make_lifx_request('POST', f"{BASE_URL}/lights/group_id:{group_id}/toggle", headers=get_lifx_headers())
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})


@app.route('/api/lights/<selector>/state', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def set_light_state(selector):
    user = get_current_user()
    if not user:
        return error_response("Unauthorized", HTTP_UNAUTHORIZED)

    if not can_control_light(user, selector):
        return error_response("You don't have permission to control this light", 403)

    data = request.get_json()
    if not data:
        return error_response("No state data provided", HTTP_BAD_REQUEST)

    if 'duration' not in data:
        data['duration'] = CLAUDE_DEFAULT_DURATION

    # Rewrite "all" selector for non-admin users to only their allowed selectors
    effective_selector = selector
    if selector == 'all' and not user.get('is_admin'):
        effective_selector = get_user_allowed_selectors(user)
        if not effective_selector:
            return error_response("No lights available", 403)

    response = make_lifx_request('PUT', f"{BASE_URL}/lights/{effective_selector}/state",
                                headers=get_lifx_headers(), json=data)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code, "results": response.json()})


# ===========================
# SETTINGS MANAGEMENT
# ===========================

@app.route('/api/settings', methods=['GET'])
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
@require_admin
def get_settings():
    """Get current settings (masked for security) - admin only"""
    return jsonify(config.get_masked_config())

@app.route('/api/settings', methods=['POST'])
@limiter.limit(FLASK_SETTINGS_RATE_LIMIT)
@require_admin
def update_settings():
    """Update application settings - admin only"""
    data = request.get_json()

    validation_error = validate_request_data(data)
    if validation_error:
        return validation_error

    updates = {}
    errors = []

    if 'lifx_token' in data:
        token = data['lifx_token'].strip()
        if token:
            if not config.validate_lifx_token(token):
                errors.append("Invalid LIFX token")
            else:
                updates['lifx_token'] = token

    if 'claude_api_key' in data:
        key = data['claude_api_key'].strip()
        if key:
            if not config.validate_claude_key(key):
                errors.append("Invalid Claude API key format")
            else:
                updates['claude_api_key'] = key

    if 'claude_model' in data:
        model = data['claude_model']
        valid_models = [m['id'] for m in CLAUDE_MODELS]
        if model not in valid_models:
            errors.append(f"Invalid model. Must be one of: {', '.join(valid_models)}")
        else:
            updates['claude_model'] = model

    if 'system_prompt' in data:
        updates['system_prompt'] = data['system_prompt'].strip()

    if errors:
        return error_response("; ".join(errors), HTTP_BAD_REQUEST)

    config.update(updates)

    return success_response({
        "message": "Settings updated successfully",
        "settings": config.get_masked_config()
    })

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Get list of available Claude models"""
    return jsonify({
        "models": CLAUDE_MODELS,
        "current": config.get('claude_model')
    })

@app.route('/api/default-prompt', methods=['GET'])
def get_default_prompt():
    """Get the default system prompt"""
    return jsonify({
        "default_prompt": DEFAULT_SYSTEM_PROMPT
    })


# ===========================
# NLP - SCOPED
# ===========================

@app.route('/api/natural-language', methods=['POST'])
@limiter.limit(FLASK_NLP_RATE_LIMIT)
def process_natural_language():
    try:
        user = get_current_user()
        if not user:
            return error_response("Unauthorized", HTTP_UNAUTHORIZED)

        # Check if NLP is enabled for this user
        if not user.get('nlp_enabled') and not user.get('is_admin'):
            return error_response("Natural language control is not enabled for your account", 403)

        data = request.get_json()
        user_request = data.get('request', '')

        if not user_request:
            return error_response("No request provided", HTTP_BAD_REQUEST)

        # Get current lights and scenes for context
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=get_lifx_headers())
        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=get_lifx_headers())

        if isinstance(lights_response, tuple) or isinstance(scenes_response, tuple):
            return error_response("Failed to fetch LIFX data", HTTP_SERVER_ERROR)

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        # CRITICAL: Filter lights and scenes to only what this user can see
        lights_data = filter_lights(lights_data, user)
        scenes_data = filter_scenes(scenes_data, user)

        # Create context for Claude - ONLY includes user's entitled lights/scenes
        context = {
            "lights": lights_data,
            "scenes": scenes_data
        }

        # Get custom system prompt or use default
        base_prompt = config.get('system_prompt') or DEFAULT_SYSTEM_PROMPT

        # Append context to the system prompt
        system_prompt = base_prompt + "\n\nCurrent lights and scenes context: " + json.dumps(context, indent=2)

        # Call Claude API with dynamic model from config
        message = get_claude_client().messages.create(
            model=config.get('claude_model'),
            max_tokens=CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_request}
            ]
        )

        # Parse Claude's response
        claude_response = message.content[0].text.strip()

        # Strip markdown code blocks if present
        if claude_response.startswith('```'):
            claude_response = claude_response.removeprefix('```json').removeprefix('```')
            claude_response = claude_response.removesuffix('```')
            claude_response = claude_response.strip()

        try:
            parsed_response = json.loads(claude_response)
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "Failed to parse AI response",
                "raw_response": claude_response,
                "parse_error": str(e)
            }), HTTP_SERVER_ERROR

        if "error" in parsed_response:
            return jsonify({"summary": parsed_response["error"], "success": False})

        # Execute the actions - with permission checks
        results = []
        api_requests = []
        api_responses = []

        for action in parsed_response.get("actions", []):
            endpoint = action["endpoint"]
            method = action["method"]
            description = action["description"]
            body = action.get("body")

            request_details = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "body": body
            }
            api_requests.append(request_details)

            # Extract selector and verify permission before executing
            selector = None
            if "/api/toggle/" in endpoint:
                light_id = endpoint.split("/api/toggle/")[1]
                selector = f"id:{light_id}" if not light_id.startswith('id:') else light_id
            elif "/api/group/" in endpoint and "/toggle" in endpoint:
                group_id = endpoint.split("/api/group/")[1].split("/toggle")[0]
                selector = f"group_id:{group_id}"
            elif "/api/lights/" in endpoint and "/state" in endpoint:
                selector = endpoint.split("/api/lights/")[1].split("/state")[0]

            # Permission check for non-scene actions
            if selector and not can_control_light(user, selector):
                results.append({"action": description, "success": False, "error": "Permission denied"})
                api_responses.append({
                    "success": False,
                    "description": description,
                    "error": "Permission denied",
                    "statusCode": 403
                })
                continue

            # Scene permission check
            if "/api/scene/" in endpoint and "/api/scene/" in endpoint:
                scene_uuid = endpoint.split("/api/scene/")[1]
                if not user.get('is_admin'):
                    perms = get_user_permissions(user['id'])
                    if scene_uuid not in perms.get('scenes', set()):
                        results.append({"action": description, "success": False, "error": "Permission denied"})
                        api_responses.append({
                            "success": False,
                            "description": description,
                            "error": "Permission denied",
                            "statusCode": 403
                        })
                        continue

            # Execute the action
            if "/api/toggle/" in endpoint:
                light_id = endpoint.split("/api/toggle/")[1]
                lifx_url = f"{BASE_URL}/lights/{light_id}/toggle"
                response = make_lifx_request('POST', lifx_url, headers=get_lifx_headers())
            elif "/api/scene/" in endpoint:
                scene_uuid = endpoint.split("/api/scene/")[1]
                lifx_url = f"{BASE_URL}/scenes/scene_id:{scene_uuid}/activate"
                response = make_lifx_request('PUT', lifx_url, headers=get_lifx_headers(), json={"duration": CLAUDE_DEFAULT_DURATION})
            elif "/api/group/" in endpoint and "/toggle" in endpoint:
                group_id = endpoint.split("/api/group/")[1].split("/toggle")[0]
                lifx_url = f"{BASE_URL}/lights/group_id:{group_id}/toggle"
                response = make_lifx_request('POST', lifx_url, headers=get_lifx_headers())
            elif "/api/lights/" in endpoint and "/state" in endpoint:
                selector = endpoint.split("/api/lights/")[1].split("/state")[0]
                if body:
                    # Rewrite "all" for non-admin users
                    effective_selector = selector
                    if selector == 'all' and not user.get('is_admin'):
                        effective_selector = get_user_allowed_selectors(user)
                        if not effective_selector:
                            results.append({"action": description, "success": False, "error": "No lights available"})
                            api_responses.append({"success": False, "description": description, "error": "No lights available", "statusCode": 403})
                            continue
                    encoded_selector = effective_selector.replace('|', '%7C')
                    lifx_url = f"{BASE_URL}/lights/{encoded_selector}/state"
                    response = make_lifx_request('PUT', lifx_url, headers=get_lifx_headers(), json=body)
                    if '|' in selector:
                        time.sleep(0.3)
                else:
                    results.append({"action": description, "success": False, "error": "No state data provided"})
                    api_responses.append({
                        "success": False,
                        "description": description,
                        "error": "No state data provided",
                        "statusCode": HTTP_BAD_REQUEST
                    })
                    continue
            else:
                results.append({"action": description, "success": False, "error": "Unknown endpoint"})
                api_responses.append({
                    "success": False,
                    "description": description,
                    "error": "Unknown endpoint",
                    "statusCode": HTTP_BAD_REQUEST
                })
                continue

            # Process the response
            if isinstance(response, tuple):
                results.append({"action": description, "success": False, "error": "API request failed"})
                api_responses.append({
                    "success": False,
                    "description": description,
                    "error": "API request failed",
                    "statusCode": HTTP_SERVER_ERROR
                })
            else:
                try:
                    response_data = response.json() if hasattr(response, 'json') else {}
                except (ValueError, AttributeError, TypeError):
                    response_data = {}

                if "/state" in endpoint and response.status_code == HTTP_MULTI_STATUS:
                    success_count = sum(1 for result in response_data.get('results', []) if result.get('status') == 'ok')
                    total_count = len(response_data.get('results', []))
                    results.append({"action": description, "success": True,
                                  "details": f"Updated {success_count}/{total_count} lights"})
                    api_responses.append({
                        "success": True,
                        "description": description,
                        "statusCode": response.status_code,
                        "data": {
                            "summary": f"Updated {success_count}/{total_count} lights",
                            "details": response_data.get('results', [])
                        }
                    })
                else:
                    success = 200 <= response.status_code < 300
                    results.append({"action": description, "success": success})
                    api_responses.append({
                        "success": success,
                        "description": description,
                        "statusCode": response.status_code,
                        "data": response_data
                    })

        return jsonify({
            "summary": parsed_response.get("summary", "Actions completed"),
            "results": results,
            "success": True,
            "apiDetails": {
                "aiAnalysis": {
                    "originalRequest": user_request,
                    "parsedActions": parsed_response.get("actions", []),
                    "summary": parsed_response.get("summary", "Actions completed")
                },
                "requests": api_requests,
                "responses": api_responses
            }
        })

    except Exception as e:
        return error_response(str(e), HTTP_SERVER_ERROR)


# ===========================
# ADMIN USER MANAGEMENT API
# ===========================

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users():
    """List all users with their permissions."""
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY is_admin DESC, is_guest DESC, username").fetchall()
    result = []
    for u in users:
        perms = {}
        perm_rows = conn.execute(
            "SELECT permission_type, permission_value FROM user_permissions WHERE user_id = ?",
            (u['id'],)
        ).fetchall()
        for row in perm_rows:
            perms.setdefault(row['permission_type'], []).append(row['permission_value'])

        result.append({
            'id': u['id'],
            'username': u['username'],
            'is_admin': bool(u['is_admin']),
            'is_guest': bool(u['is_guest']),
            'nlp_enabled': bool(u['nlp_enabled']),
            'permissions': perms
        })
    conn.close()
    return jsonify({'users': result})


@app.route('/api/admin/users', methods=['POST'])
@require_admin
def create_user():
    """Create a new user."""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return error_response("Username and password required", HTTP_BAD_REQUEST)

    if len(password) < 3:
        return error_response("Password must be at least 3 characters", HTTP_BAD_REQUEST)

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return error_response("Username already exists", HTTP_BAD_REQUEST)

    conn.execute(
        "INSERT INTO users (username, password_hash, nlp_enabled) VALUES (?, ?, 1)",
        (username, generate_password_hash(password))
    )
    conn.commit()
    conn.close()
    return success_response({"message": f"User '{username}' created"})


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Delete a user."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return error_response("User not found", HTTP_NOT_FOUND)

    if user['is_admin'] or user['is_guest']:
        conn.close()
        return error_response("Cannot delete admin or guest user", HTTP_BAD_REQUEST)

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return success_response({"message": "User deleted"})


@app.route('/api/admin/users/<int:user_id>/permissions', methods=['GET'])
@require_admin
def get_user_perms(user_id):
    """Get permissions for a user."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return error_response("User not found", HTTP_NOT_FOUND)

    perm_rows = conn.execute(
        "SELECT permission_type, permission_value FROM user_permissions WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()

    perms = {'lights': [], 'groups': [], 'scenes': []}
    for row in perm_rows:
        if row['permission_type'] in perms:
            perms[row['permission_type']].append(row['permission_value'])

    return jsonify({
        'permissions': perms,
        'nlp_enabled': bool(user['nlp_enabled'])
    })


@app.route('/api/admin/users/<int:user_id>/permissions', methods=['POST'])
@require_admin
def set_user_perms(user_id):
    """Set permissions for a user."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return error_response("User not found", HTTP_NOT_FOUND)

    data = request.get_json()

    # Update NLP setting
    nlp_enabled = 1 if data.get('nlp_enabled', False) else 0
    conn.execute("UPDATE users SET nlp_enabled = ? WHERE id = ?", (nlp_enabled, user_id))

    # Replace all permissions
    conn.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))

    for light_id in data.get('lights', []):
        conn.execute(
            "INSERT INTO user_permissions (user_id, permission_type, permission_value) VALUES (?, 'lights', ?)",
            (user_id, str(light_id))
        )
    for group_id in data.get('groups', []):
        conn.execute(
            "INSERT INTO user_permissions (user_id, permission_type, permission_value) VALUES (?, 'groups', ?)",
            (user_id, str(group_id))
        )
    for scene_uuid in data.get('scenes', []):
        conn.execute(
            "INSERT INTO user_permissions (user_id, permission_type, permission_value) VALUES (?, 'scenes', ?)",
            (user_id, scene_uuid)
        )

    conn.commit()
    conn.close()
    return success_response({"message": "Permissions updated"})


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
