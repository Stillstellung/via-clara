from flask import Flask, render_template, jsonify, request
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

claude_client = get_claude_client()

headers = {
    "Authorization": f"Bearer {LIFX_TOKEN}",
}

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lights')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_lights():
    response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=headers)
    if isinstance(response, tuple):
        return response
    return jsonify(response.json())

@app.route('/api/scenes')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_scenes():
    response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=headers)
    if isinstance(response, tuple):
        return response
    return jsonify(response.json())

@app.route('/api/toggle/<selector>', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def toggle_light(selector):
    response = make_lifx_request('POST', f"{BASE_URL}/lights/{selector}/toggle", headers=headers)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})

@app.route('/api/scene/<scene_uuid>', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def activate_scene(scene_uuid):
    # Let scenes use their natural timing - no duration override
    response = make_lifx_request('PUT', f"{BASE_URL}/scenes/scene_id:{scene_uuid}/activate",
                          headers=headers)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})

@app.route('/api/scenes/status/batch')
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_all_scene_statuses():
    """Get status for all scenes using SceneMatcher"""
    try:
        # Get current lights state
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=headers)
        if isinstance(lights_response, tuple):
            return lights_response

        # Get scene details
        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=headers)
        if isinstance(scenes_response, tuple):
            return scenes_response

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        # Check status for all scenes using SceneMatcher
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
        # Get current lights state
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=headers)
        if isinstance(lights_response, tuple):
            return lights_response

        # Get scene details
        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=headers)
        if isinstance(scenes_response, tuple):
            return scenes_response

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        # Find the specific scene
        target_scene = next(
            (scene for scene in scenes_data if scene['uuid'] == scene_uuid),
            None
        )

        if not target_scene:
            return error_response("Scene not found", HTTP_NOT_FOUND)

        # Check status using SceneMatcher
        status = SceneMatcher.check_scene_status(target_scene, lights_data)
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e), "active": False}), HTTP_SERVER_ERROR

@app.route('/api/group/<group_id>/toggle', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def toggle_group(group_id):
    response = make_lifx_request('POST', f"{BASE_URL}/lights/group_id:{group_id}/toggle", headers=headers)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code})

@app.route('/api/lights/<selector>/state', methods=['PUT'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def set_light_state(selector):
    data = request.get_json()
    if not data:
        return error_response("No state data provided", HTTP_BAD_REQUEST)

    # Add default duration if not specified
    if 'duration' not in data:
        data['duration'] = CLAUDE_DEFAULT_DURATION

    response = make_lifx_request('PUT', f"{BASE_URL}/lights/{selector}/state",
                                headers=headers, json=data)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code, "results": response.json()})

# NEW ENDPOINTS: Settings Management

@app.route('/api/settings', methods=['GET'])
@limiter.limit(FLASK_LIGHTS_RATE_LIMIT)
def get_settings():
    """Get current settings (masked for security)"""
    return jsonify(config.get_masked_config())

@app.route('/api/settings', methods=['POST'])
@limiter.limit(FLASK_SETTINGS_RATE_LIMIT)
def update_settings():
    """Update application settings"""
    data = request.get_json()

    # Validate request
    validation_error = validate_request_data(data)
    if validation_error:
        return validation_error

    updates = {}
    errors = []

    # Validate and prepare LIFX token
    if 'lifx_token' in data:
        token = data['lifx_token'].strip()
        if token:
            if not config.validate_lifx_token(token):
                errors.append("Invalid LIFX token")
            else:
                updates['lifx_token'] = token

    # Validate and prepare Claude API key
    if 'claude_api_key' in data:
        key = data['claude_api_key'].strip()
        if key:
            if not config.validate_claude_key(key):
                errors.append("Invalid Claude API key format")
            else:
                updates['claude_api_key'] = key

    # Validate Claude model selection
    if 'claude_model' in data:
        model = data['claude_model']
        valid_models = [m['id'] for m in CLAUDE_MODELS]
        if model not in valid_models:
            errors.append(f"Invalid model. Must be one of: {', '.join(valid_models)}")
        else:
            updates['claude_model'] = model

    # Handle system prompt (empty string means use default)
    if 'system_prompt' in data:
        updates['system_prompt'] = data['system_prompt'].strip()

    if errors:
        return error_response("; ".join(errors), HTTP_BAD_REQUEST)

    # Apply updates
    config.update(updates)

    # Reinitialize clients with new credentials
    global claude_client, headers
    claude_client = get_claude_client()
    headers = {"Authorization": f"Bearer {config.get('lifx_token')}"}

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

@app.route('/api/natural-language', methods=['POST'])
@limiter.limit(FLASK_NLP_RATE_LIMIT)
def process_natural_language():
    try:
        data = request.get_json()
        user_request = data.get('request', '')

        if not user_request:
            return error_response("No request provided", HTTP_BAD_REQUEST)

        # Get current lights and scenes for context
        lights_response = make_lifx_request('GET', f"{BASE_URL}/lights/all", headers=headers)
        scenes_response = make_lifx_request('GET', f"{BASE_URL}/scenes", headers=headers)

        if isinstance(lights_response, tuple) or isinstance(scenes_response, tuple):
            return error_response("Failed to fetch LIFX data", HTTP_SERVER_ERROR)

        lights_data = lights_response.json()
        scenes_data = scenes_response.json()

        # Create context for Claude
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

        # Strip markdown code blocks if present (newer models wrap JSON in ```json)
        if claude_response.startswith('```'):
            # Remove opening ```json or ``` and closing ```
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

        # Execute the actions
        results = []
        api_requests = []
        api_responses = []

        for action in parsed_response.get("actions", []):
            endpoint = action["endpoint"]
            method = action["method"]
            description = action["description"]
            body = action.get("body")

            # Track the API request details
            request_details = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "body": body
            }
            api_requests.append(request_details)

            # Execute the action based on endpoint
            if "/api/toggle/" in endpoint:
                light_id = endpoint.split("/api/toggle/")[1]
                lifx_url = f"{BASE_URL}/lights/{light_id}/toggle"
                response = make_lifx_request('POST', lifx_url, headers=headers)
            elif "/api/scene/" in endpoint:
                scene_uuid = endpoint.split("/api/scene/")[1]
                lifx_url = f"{BASE_URL}/scenes/scene_id:{scene_uuid}/activate"
                response = make_lifx_request('PUT', lifx_url, headers=headers, json={"duration": CLAUDE_DEFAULT_DURATION})
            elif "/api/group/" in endpoint and "/toggle" in endpoint:
                group_id = endpoint.split("/api/group/")[1].split("/toggle")[0]
                lifx_url = f"{BASE_URL}/lights/group_id:{group_id}/toggle"
                response = make_lifx_request('POST', lifx_url, headers=headers)
            elif "/api/lights/" in endpoint and "/state" in endpoint:
                # Extract selector from endpoint like "/api/lights/group:bedroom/state"
                selector = endpoint.split("/api/lights/")[1].split("/state")[0]
                if body:
                    # URL-encode pipe character for zone selectors
                    encoded_selector = selector.replace('|', '%7C')
                    lifx_url = f"{BASE_URL}/lights/{encoded_selector}/state"
                    response = make_lifx_request('PUT', lifx_url, headers=headers, json=body)

                    # Add delay between zone commands to prevent interference
                    if '|' in selector:
                        time.sleep(0.3)  # 300ms delay for multi-zone commands
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
                except:
                    response_data = {}

                # Get more detailed response info for state changes
                if "/state" in endpoint and response.status_code == HTTP_MULTI_STATUS:
                    # Multi-status response, extract results
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
