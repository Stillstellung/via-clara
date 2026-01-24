# Via Clara - LIFX Controller Dashboard

## Overview
Python Flask web dashboard for controlling LIFX smart lights with Material Design and Claude AI-powered natural language control. **Now with light/dark mode toggle, enhanced responsive design, and full accessibility support!**

*Via Clara* - Latin for "The Bright Way"

## Key Features
- **Light/Dark Mode Toggle** - Seamlessly switch between themes with persistent preference (localStorage)
- **Modern Responsive Design** - Optimized for mobile, tablet, and desktop with adaptive layouts
- **Enhanced Accessibility** - Full keyboard navigation, ARIA labels, and screen reader support
- **Settings UI** - Configure API keys, Claude model, and custom system prompt
- **Pinned Items** - Double-right-click to pin favorite scenes, rooms, or lights (persists via localStorage)
- **Custom System Prompt** - Customize Claude AI's behavior through the settings UI
- View and control all LIFX lights
- Activate scenes with visual feedback
- Toggle rooms (groups) on/off
- Individual light control
- **Natural language control** - Use plain English to control lights
- Auto-refresh every 10 seconds
- Smooth animations and modern Material Design styling

## Project Structure

### Backend Files
- `app.py` (495 lines) - Flask backend with LIFX API integration and Claude AI processing
- `config.py` - Configuration management singleton (handles config.json persistence)
- `constants.py` - Centralized constants (rate limits, tolerances, model options)
- `scene_matcher.py` - Scene status detection logic (eliminates code duplication)
- `api_utils.py` - API response handlers and validation utilities
- `requirements.txt` - Python dependencies

### Frontend Files
- `templates/index.html` - Main HTML template with natural language input, settings modal, and theme toggle
- `static/css/style.css` - Material Design styling with CSS variables for light/dark themes
- `static/js/app.js` - Frontend JavaScript for API calls, UI updates, and theme management

### Configuration Files
- `config.json` (gitignored) - Runtime configuration with API credentials
- `config.example.json` - Template for initial setup
- `.gitignore` - Includes config.json to prevent credential exposure

## Initial Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials

**Option A: Use the Settings UI (Recommended)**
1. Start the app: `python app.py`
2. Open http://localhost:5000
3. Click the settings gear icon (top-right)
4. Enter your API credentials:
   - LIFX Token from [cloud.lifx.com/settings](https://cloud.lifx.com/settings)
   - Claude API Key from [console.anthropic.com](https://console.anthropic.com/settings/keys)
5. Select Claude model (Haiku 4.5, Sonnet 4.5, or Opus 4.5)
6. Click "Save Settings"

**Option B: Manual Configuration**
1. Copy `config.example.json` to `config.json`
2. Edit `config.json` with your credentials:
```json
{
  "lifx_token": "your_lifx_token_here",
  "claude_api_key": "your_claude_key_here",
  "claude_model": "claude-haiku-4-5-20251001"
}
```

### 3. Run the App
```bash
python app.py
```
Access at http://localhost:5000

## Available Claude Models
- **claude-haiku-4-5-20251001** - Fast and cost-effective ($1/$5 per million tokens)
- **claude-sonnet-4-5-20250929** - Balanced performance ($3/$15 per million tokens)
- **claude-opus-4-5-20251101** - Most capable ($15/$75 per million tokens)

## API Endpoints

### Settings Management
- `GET /api/settings` - Get current configuration (masked for security, includes system_prompt)
- `POST /api/settings` - Update configuration (validates credentials, accepts system_prompt)
- `GET /api/models` - Get available Claude models with descriptions
- `GET /api/default-prompt` - Get the default system prompt for restoration

### Light Control
- `GET /api/lights` - Get all lights
- `GET /api/scenes` - Get all scenes
- `GET /api/scenes/status/batch` - Get all scene statuses in one call (optimized)
- `GET /api/scene/<scene_uuid>/status` - Get individual scene status
- `GET /api/scene/<scene_uuid>/debug` - Debug scene matching (shows expected vs actual values)
- `PUT /api/toggle/<selector>` - Toggle light
- `PUT /api/scene/<scene_uuid>` - Activate scene (uses natural timing, no duration override)
- `PUT /api/group/<group_id>/toggle` - Toggle room
- `PUT /api/lights/<selector>/state` - Set light color/brightness/power
- `POST /api/natural-language` - Process natural language commands

## Natural Language Control
The dashboard includes a text input at the top for natural language commands powered by Claude AI with **enhanced visual feedback** showing the entire processing pipeline.

### Enhanced Visual Feedback
When processing natural language commands, the dashboard shows:

1. **Processing Pipeline Visualization**: 4-stage visual pipeline showing:
   - **Prompt Ingestion**: Real-time display of the user's request being parsed
   - **AI Processing**: Claude AI analyzing and converting to API commands
   - **API Execution**: Commands being sent to LIFX API with progress tracking
   - **Completion**: Final results with success/error indicators

2. **Detailed API Information Panel**: Expandable section showing:
   - **AI Analysis**: Original request, parsed actions, and command summary
   - **API Requests**: HTTP method, endpoint, and request body for each command
   - **API Responses**: Status codes, response data, and detailed success/error info

3. **Real-time Status Updates**: Each pipeline stage shows:
   - Animated progress indicators with spinning icons
   - Color-coded status (purple=active, green=success, red=error)
   - Descriptive details about current processing step
   - Live command counts and execution results

### Example Commands
- "turn on bedroom lights"
- "make living room lights red"
- "set kitchen to 50% brightness"
- "turn bedroom lights blue at 75% brightness"
- "turn off all lights"
- "activate movie scene"

### Multi-Zone Gradients (LIFX Beam)
For multi-zone devices like LIFX Beam and Z Strip, you can create gradient effects across zones:

**Gradient Commands:**
- "make beam purple and red" - Creates a two-color gradient
- "set beam to rainbow gradient" - Creates a multi-color rainbow effect
- "make beam half green half yellow" - Splits device into two color zones
- "create purple to blue gradient on beam" - Smooth color transition

**How it Works:**
- The AI automatically identifies multi-zone devices (Beam, Strip, Lightstrip)
- Splits zones evenly between requested colors (varies by device: 10 zones per Beam segment, up to 82 total)
- Sends multiple zone-specific commands to create the gradient
- Automatically sets brightness to 100% unless you specify otherwise
- Example: "purple and red" on 61-zone Beam → zones 0-30 purple, zones 31-60 red

**Single Color on Beam:**
- "make beam blue" - Sets all zones to the same color (no gradient)
- "turn beam on" - Toggles the entire device

**Technical Details:**
- Zone syntax: `id:d073d5|0-4` targets zones 0-4 of device d073d5 (pipe character URL-encoded to %7C)
- Gradients require multiple API calls (one per color segment) with 300ms delay between commands
- Each zone command includes power, color, brightness, and duration
- Brightness defaults to 1.0 (100%) for visibility unless user specifies percentage
- Action log shows individual zone commands for transparency

### Supported Actions
- **Toggle lights/rooms**: on/off control
- **Set colors**: named colors (red, blue), hex codes (#ff0000), or hue/saturation
- **Set brightness**: percentages (0-100%)
- **Activate scenes**: by name
- **Combined commands**: color + brightness in one command

## Pinned Items

Pin your favorite scenes, rooms, or lights for quick access at the top of the dashboard.

### How to Pin
- **Double-right-click** on any scene, room, or light card to pin/unpin it
- Pinned items appear in a dedicated "Pinned" section at the top
- Pins persist across browser sessions via localStorage

### Features
- **Live state**: Pinned items show real-time status (on/off, brightness, active scene)
- **Full functionality**: Click pinned items to toggle/activate just like regular items
- **Automatic cleanup**: Items removed from LIFX are automatically unpinned
- **Section visibility**: Pinned section only appears when items are pinned

## Settings UI Features

### Configuration Management
- **Secure storage**: Credentials stored server-side in config.json (600 permissions)
- **Masked display**: API keys shown as `c5002ca2...6494` for security
- **Live validation**: Credentials validated before saving
- **Hot reload**: Changes apply immediately without restart
- **Model selection**: Dropdown with all available Claude models
- **Custom system prompt**: Edit the AI system prompt to customize behavior

### UI Components
- **Settings Button**: Gear icon in header (top-right)
- **Modal Panel**: Slide-in animation with Material Design styling
- **Password Toggles**: Show/hide buttons for API credentials
- **System Prompt Textarea**: Monospace editor with restore default button
- **Status Indicator**: Shows configuration completeness
- **Help Links**: Direct links to credential sources
- **Responsive Design**: Mobile-optimized layout

## Theme System (Light/Dark Mode)

### Features
- **Seamless Toggle**: Click the sun/moon icon in the header to switch themes
- **Persistent Preference**: Theme choice saved to localStorage (survives page refresh)
- **Smooth Transitions**: All UI elements transition smoothly between themes
- **Complete Coverage**: All components styled for both light and dark modes

### Theme Implementation
- **CSS Variables**: Dual theme system using CSS custom properties
- **Light Theme**: Clean white backgrounds, subtle shadows, high contrast text
- **Dark Theme**: Deep navy backgrounds, vibrant accents, reduced eye strain
- **Gradients**: Modern gradient overlays on both themes for visual depth
- **Accessibility**: Both themes meet WCAG contrast requirements

### Usage
The theme toggle button is located in the header (top-right area) with intuitive icons:
- 🌙 Moon icon = Currently in light mode (click to switch to dark)
- ☀️ Sun icon = Currently in dark mode (click to switch to light)

## Responsive Design

### Breakpoints
- **Desktop** (≥1024px): Full grid layouts with optimal spacing, multi-column scenes/rooms/lights
- **Tablet** (768px-1023px): Adjusted grid columns, optimized spacing
- **Mobile** (≤767px): Single column layout, touch-friendly 44x44px minimum targets
- **Small Mobile** (≤374px): Further spacing optimizations for compact screens

### Adaptive Features
- **Header Actions**: Settings and theme toggle buttons stack properly on mobile
- **Natural Language Input**: Full-width on mobile with adjusted padding
- **Cards**: Scene, room, and light cards automatically reflow
- **Settings Modal**: Full-screen on mobile, centered panel on desktop
- **Touch Targets**: All interactive elements meet minimum 44x44px for touch accessibility

## Accessibility Features

### Keyboard Navigation
- **Tab Navigation**: All interactive elements accessible via Tab key
- **Enter/Space Activation**: Cards and buttons respond to keyboard activation
- **Focus Indicators**: Clear visual focus rings on all interactive elements
- **Skip Links**: Efficient navigation for keyboard-only users

### Screen Reader Support
- **ARIA Labels**: Descriptive labels on all interactive elements
- **ARIA Live Regions**: Dynamic content updates announced to screen readers
- **Semantic HTML**: Proper heading hierarchy and landmark roles
- **Button Roles**: Explicit roles for clickable elements

### Visual Accessibility
- **High Contrast**: Both themes meet WCAG contrast requirements
- **Color Independence**: Status not conveyed by color alone
- **Scalable Text**: Responsive font sizing with viewport units
- **Focus Visibility**: Clear focus indicators for keyboard navigation

## UI Components
- **Theme Toggle**: Sun/moon button in header to switch between light/dark mode
- **Refreshing Indicator**: Appears below title when data is loading
- **Pinned Section**: Shows pinned items at top (double-right-click to pin/unpin)
- **Settings Modal**: Configure API keys, model selection, and system prompt
- **Natural Language Input**: Top section with text input and submit button
- **Processing Pipeline**: 4-stage visual pipeline showing prompt → AI → API → completion with real-time status
- **API Details Panel**: Collapsible technical view showing AI analysis, HTTP requests, and responses
- **Action Log**: Persistent log showing last 3 natural language commands with timestamps and results (auto-expires after 3 minutes)
- **Scenes**: Scene tiles with clickable activation and hover effects
- **Rooms**: Room controls with toggle buttons and status indicators
- **Lights**: Individual light tiles showing power state, brightness, and color

## API Optimization & Refresh Behavior

### Batch Scene Status Checking
- **Optimized from 2+2N to 3 API calls** per refresh using `/api/scenes/status/batch`
- Single endpoint checks all scene statuses server-side with sophisticated state comparison
- Reduces API load while maintaining accurate scene detection

### Automatic Refresh
- **Every 5 seconds** - Full data refresh from LIFX API
- Safe at 36 calls/minute vs 120/minute LIFX rate limit

### Scene Detection (Hybrid Approach)

**Why hybrid?** The LIFX API has no "is this scene active?" endpoint. We must compare current light states against saved scene states. Additionally, scenes can have transition times (e.g., 10 seconds) during which lights gradually change to target values.

**How it works:**

1. **Click scene** → Purple "activating" badge appears immediately
2. **During transition** → Activating state persists while lights transition (can be 10+ seconds depending on scene settings)
3. **Backend polling** → Every 5 seconds, server compares light states to scene states
4. **Transition complete** → When backend detects scene at 70% match, flips to green "active" badge
5. **External activations** → If you activate via LIFX app/Alexa, backend detects it and syncs UI

**Backend matching (70% threshold)** with tolerances:
- Brightness: ±5%
- Hue: ±10° (with 360° wraparound handling)
- Saturation: ±10%
- Kelvin (color temperature): ±200K

**Important notes:**
- Multiple scenes can be detected as "active" simultaneously if they have similar/overlapping settings
- The system tracks which specific scene you activated and waits for that one to be detected
- Small scenes (2-3 lights) require all lights to match since 1 mismatch drops below 70%
- External changes take up to 5 seconds to reflect in the UI

### Manual Refresh Triggers
- **After toggling individual lights** - 500ms delay
- **After toggling rooms** - 500ms delay
- **After natural language commands** - 1 second delay

### Action Log Behavior
- Shows last 3 natural language commands with timestamps
- Each entry auto-expires after 3 minutes
- Displays detailed results for each action taken
- Includes success/failure status for individual lights affected
- Log appears/disappears automatically based on activity

## Code Architecture

### Backend Modules
**config.py** - Configuration Management
- Singleton pattern for global config access
- Validates LIFX tokens and Claude API keys
- Persists changes to config.json with secure permissions
- Provides masked output for UI display

**constants.py** - Centralized Constants
- Rate limits (LIFX: 120/min, Flask endpoints: various)
- Scene detection thresholds (brightness: 5%, hue: 10°, saturation: 10%, kelvin: 200K, scene: 70%)
- Claude model options with descriptions and pricing
- HTTP status codes

**scene_matcher.py** - Scene Status Detection
- `matches_selector()` - Check if light matches selector
- `find_matching_lights()` - Get all lights matching selector
- `check_power_match()` - Validate power state
- `check_brightness_match()` - Validate brightness (with tolerance)
- `check_hue_match()` - Validate hue (handles 360° wraparound)
- `check_saturation_match()` - Validate saturation (with tolerance)
- `light_matches_state()` - Full state comparison
- `check_scene_status()` - Main scene detection logic

**api_utils.py** - API Utilities
- `handle_lifx_response()` - Standardized LIFX response handling
- `success_response()` - Consistent success formatting
- `error_response()` - Consistent error formatting
- `validate_request_data()` - Request validation

### Frontend Architecture
**CSS Variables** - Dual Theme System
- Complete light/dark theme definitions with CSS custom properties
- Brand colors, backgrounds, borders, text, states for both themes
- Shadows, transitions, spacing, border radius
- Gradient overlays and modern visual effects
- Enables consistent styling and instant theme switching across all components

**JavaScript Organization**
- Global state variables (lights, scenes, rooms, etc.)
- Theme management (localStorage persistence, toggle functionality)
- Data fetching and rendering functions
- Natural language processing with pipeline visualization
- Settings modal management
- Keyboard event handlers for accessibility
- Event listeners in DOMContentLoaded

## Security Features
- API credentials never sent to client browser
- Credentials masked in UI (`c5002ca2...6494`)
- config.json has 600 permissions (owner read/write only)
- config.json gitignored to prevent accidental commits
- LIFX token validation before saving
- Claude API key format validation

## Development Guidelines
- **ALWAYS update CLAUDE.md** after making any changes to code, features, or project structure
- Document new endpoints, features, API keys, and usage examples immediately
- Keep project structure and dependencies current in documentation
- Never commit config.json to version control
- Use settings UI for credential management in production

## Troubleshooting

### Configuration Issues
**Problem**: App starts but shows "Configuration required"
**Solution**: Use settings UI or create config.json with valid credentials

**Problem**: Settings save fails with "Invalid LIFX token"
**Solution**: Verify token from [cloud.lifx.com/settings](https://cloud.lifx.com/settings)

**Problem**: Natural language commands fail
**Solution**: Check Claude API key in settings, verify model is selected

### API Rate Limiting
**Problem**: "Rate limit exceeded" errors
**Solution**: App tracks rate limits automatically. Wait for limit reset (shown in error message)

### Scene Detection
**Problem**: Scene shows as active but shouldn't (or vice versa)
**Context**: Scene detection is inherently fuzzy - see "Scene Detection (Hybrid Approach)" section above.
**Solutions**:
- Adjust `SCENE_MATCH_THRESHOLD` in constants.py (default 0.7 = 70%)
- Adjust individual tolerances: `BRIGHTNESS_TOLERANCE`, `HUE_TOLERANCE_DEGREES`, `SATURATION_TOLERANCE`, `KELVIN_TOLERANCE`
- Use debug endpoint: `GET /api/scene/<uuid>/debug` to see exactly what's matching/not matching

## Code Quality Improvements

### Backend Refactor
- ✅ **65 lines removed** from app.py (560 → 495 lines)
- ✅ **~150 lines of duplicate code eliminated** (scene status logic)
- ✅ **No hardcoded credentials** in source code
- ✅ **Centralized constants** (no magic numbers)
- ✅ **Modular architecture** (config, constants, scene_matcher, api_utils)
- ✅ **Settings UI** for easy configuration
- ✅ **Latest Claude models** (Haiku 4.5, Sonnet 4.5, Opus 4.5)

### Frontend Refactor (January 2026)
- ✅ **Light/Dark Mode Toggle** - Complete dual theme system with localStorage persistence
- ✅ **Enhanced Responsive Design** - Comprehensive breakpoints for mobile, tablet, and desktop
- ✅ **Full Accessibility Support** - ARIA labels, keyboard navigation, screen reader optimization
- ✅ **Modern Material Design** - Gradients, animations, and enhanced visual polish
- ✅ **CSS Variables** - Maintainable theming system with 80+ custom properties
- ✅ **Touch Optimization** - 44x44px minimum touch targets, mobile-friendly interactions
- ✅ **Improved UX** - Smooth transitions, clear focus indicators, intuitive controls
- ✅ **File Changes**: 880 insertions, 437 deletions across 3 frontend files

