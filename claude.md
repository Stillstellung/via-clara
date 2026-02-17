# claude.md — Via Clara Project Context

## What Is This?

Via Clara is a Flask web dashboard for controlling LIFX smart lights via natural language (powered by Claude API). It supports direct light/group/scene control, multi-zone gradients (Beam/Strip), and a processing pipeline visualization.

## Architecture

- **`app.py`** — Main Flask app. All API routes, NLP processing pipeline, LIFX API integration, admin endpoints.
- **`auth.py`** — Authentication and authorization. SQLite-backed user/permission management, session handling, permission filtering, selector rewriting.
- **`config.py`** — JSON config management (LIFX token, Claude API key, model selection, system prompt).
- **`constants.py`** — Centralized constants (thresholds, timeouts, defaults).
- **`scene_matcher.py`** — Hybrid scene detection (compares live light states against scene definitions).
- **`api_utils.py`** — HTTP response helpers for LIFX API calls.
- **`templates/index.html`** — Main dashboard UI.
- **`templates/login.html`** — Login page.
- **`templates/admin.html`** — Admin panel for user/permission management.
- **`static/js/app.js`** — Frontend JS (Material Design, light controls, NLP UI, auth-aware visibility).
- **`static/css/style.css`** — Styling (light/dark theme, responsive).
- **`via_clara.db`** — SQLite database (auto-created on first run). Stores users and permissions.

## User Auth System (feature/user-auth)

### Roles
- **Admin** — Full access. Can manage users, configure settings, use NLP, see all lights/scenes/groups. Default: `admin`/`admin`.
- **Named users** — Password-authenticated. Scoped to specific lights, groups, and scenes assigned by admin. NLP access toggleable.
- **Guest** — No login required. Scoped view based on guest permissions. NLP disabled by default.

### Permission Model
- Permissions stored in `user_permissions` table: `(user_id, permission_type, permission_value)`.
- `permission_type` is one of: `lights`, `groups`, `scenes`.
- `permission_value` stores the **label/name** (not UUID/hardware ID) for portability.
- **Cascading**: assigning a group auto-includes all its lights. Assigning a scene auto-includes all lights and groups the scene references. Cascading is resolved at save time by fetching live LIFX data.

### How Scoping Works
- `filter_lights()` / `filter_scenes()` in `auth.py` prune API responses before sending to the frontend.
- NLP context only includes lights the user is entitled to (via `get_user_allowed_selectors()`).
- `can_control_light()` enforces permissions on every API action, resolving hardware IDs to labels via a lights cache when needed.
- `all` selector is allowed for non-admins only if they have some permissions — the NLP context itself limits what Claude can target.

### Key Design Decisions
- **Labels over IDs**: Permissions use human-readable names (`label:`, `group:`) rather than LIFX hardware IDs or UUIDs. This survives device replacements and is easier to manage in the admin UI.
- **Cascading at save time**: When an admin assigns a scene, the server resolves its constituent lights/groups immediately and stores them as explicit permissions. This avoids runtime dependency on scene definitions.
- **NLP scoping via context**: Rather than post-filtering NLP commands, the LLM only sees lights the user is allowed to control. The `all` selector works naturally because "all" in the LLM's context means "all lights I was told about."
- **Server-side enforcement**: Even if a user crafts manual API calls, `can_control_light()` checks every action. Belt and suspenders.

## Development Notes

- The database auto-initializes on import of `auth.py` (`init_db()` runs at module level).
- `.gitignore` excludes `via_clara.db` — each deployment starts fresh or migrates its own.
- `config.json` holds LIFX/Claude credentials (also gitignored).
- The app binds to `0.0.0.0:5000` by default.

## Testing the Auth System

1. Start the app, log in as `admin`/`admin`.
2. Go to `/admin`, create a test user with a subset of lights/groups/scenes.
3. Log out, log in as the test user.
4. Verify: only assigned lights/groups/scenes are visible. NLP commands are scoped. Direct API calls to unauthorized lights return 403.
5. Test guest by visiting in an incognito window (no login).
