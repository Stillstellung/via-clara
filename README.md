# Via Clara

A modern web-based dashboard for controlling LIFX smart lights with LLM-driven natural language control. Built with trial, error, and Claude Code.

If you want to use the written commands to lighting feature(s), currently you must have an anthropic claude api key. Local LLMs behaved oddly, but I'll probably bring that option back one of these days. 

Star it if ya like it. 

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.0-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

![Dashboard](/dash.png)

## Features

### Light Control
- **Individual Light Control via natural language requests** - Toggle, adjust brightness, change colors, etc (details below)
- **Room/Group Management** - Control multiple lights at once
- **Scene Activation** - One-click scene switching with visual feedback
- **Real-time Status** - Auto-refresh every 5 seconds
- **Multi-Zone Support** - Create gradients by describing them on LIFX Beam and Strip devices

Request example

![Request](/nlp1.png)

And the result

![Result](/nlp2.png)

### Configuration UI
- **Model selection** - Choose between Claude Haiku, Sonnet, or Opus
- **Custom system prompt** - Customize how the LLM interprets your speech
- **Live validation** - Credentials validated before saving

### Pinning Objects
- **Quick access** - Pin your favorite scenes, rooms, or lights
- **Double-right-click** to pin/unpin any item

### A Note on Scene Detection

The LIFX API doesn't provide a "is this scene active?" endpoint, so Via Clara uses a **hybrid approach**:

1. **Click a scene** → Purple "activating" badge appears immediately
2. **During transition** → Activating state persists (scenes can have 10+ second transitions)
3. **Backend polling** → Server compares light states every 5 seconds (70% match threshold)
4. **Transition complete** → Flips to green "active" badge when detected

**What this means for you:**
- Activating via dashboard = immediate "activating" feedback, then "active" when lights finish transitioning
- Activating via LIFX app/Alexa = detected within 5 seconds
- Multiple similar scenes may show as "active" simultaneously (they share light settings)
- Tune thresholds in `constants.py` if needed (`SCENE_MATCH_THRESHOLD`, tolerances for brightness/hue/kelvin)

##  Quick Start with Flask

### Prerequisites
- Python 3.8 or higher
- LIFX smart lights connected to your network
- LIFX API token ([Get one here](https://cloud.lifx.com/settings))
- Claude API key ([Get one here](https://console.anthropic.com/settings/keys))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Stillstellung/via-clara.git
   cd via-clara
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application**
   ```bash
   python app.py
   ```

4. **Open in your browser**
   ```
   http://localhost:5000
   ```

5. **Configure via Settings UI**
   - Click the gear icon (⚙️) in the top-right corner
   - Enter your LIFX token
   - Enter your Claude API key
   - Select your preferred Claude model
   - Click "Save Settings"

### Natural Language Commands

**Simple Commands:**
```
turn on bedroom lights
set kitchen to 75% brightness
make living room lights red
turn off all lights
```

**Color Commands:**
```
set bedroom to blue
make kitchen lights warm white
change living room to #ff6b35
```

**Multi-Zone Gradients (LIFX Beam):**
```
make beam purple and red
set beam to rainbow gradient
create blue to green gradient on beam
make beam half orange half purple
```

**Combined Commands:**
```
turn bedroom lights blue at 50% brightness
set living room to warm white at 25%
```

###  Multi-Zone Device Support

The dashboard supports LIFX Beam and Strip devices with individually addressable zones.

**Gradient Commands:**
- Two colors: "make beam purple and red"
- Three colors: "make beam red white and blue gradient"
- Rainbow: "set beam to rainbow"
- Specific zones: "make beam half green half yellow"

**How it Works:**
- Uses zone selector syntax: `id:d073d5|0-30`
- Automatically includes brightness for visibility
- 300ms delay between zone commands prevents interference
- Works with both named colors and hex codes

### Processing Pipeline Viz

Enable pipeline tracking with the eye icon (👁️) to see:
1. **Prompt Ingestion** - Your request being analyzed
2. **AI Processing** - Claude converting to API commands
3. **API Execution** - Commands being sent to LIFX
4. **Completion** - Results and success indicators

Expand the API details panel to see:
- Original request and AI interpretation
- HTTP requests with full endpoints and payloads
- API responses with status codes and data
- Individual zone commands for multi-zone devices

## Arch

### Structure
```
via-clara/
├── app.py                 # Flask backend & API routes
├── config.py              # Configuration management
├── constants.py           # Centralized constants
├── scene_matcher.py       # Scene status detection
├── api_utils.py           # API response handlers
├── requirements.txt       # Python dependencies
├── config.example.json    # Configuration template
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── css/
    │   └── style.css     # Material Design styling
    └── js/
        └── app.js        # Frontend JavaScript
```

### Stack
- **Backend:** Flask 
- **Frontend:** Material JS
- **LLM:** Anthropic Claude API (Haiku/Sonnet/Opus models)
- **Smart Home:** LIFX HTTP API
- **Rate Limiting:** Flask-Limiter
- **Configuration:** JSON-based with hot-reload

## Configuration

### Claude Models

Choose the model that fits your needs:

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **Haiku 4.5** | Fastest | $1/$5 per million tokens | Most users, quick responses |
| **Sonnet 4.5** | Balanced | $3/$15 per million tokens | Complex commands, better accuracy |
| **Opus 4.5** | Powerful | $15/$75 per million tokens | Maximum capability, research |

**Recommendation:** Just use Haiku.

### Configuration File

If you prefer manual configuration, edit `config.json`:

```json
{
  "lifx_token": "your_lifx_token_here",
  "claude_api_key": "your_claude_api_key_here",
  "claude_model": "claude-haiku-4-5-20251001"
}
```

## System Prompt & LLM Behavior

The natural language control is powered by a system prompt that instructs Claude how to interpret your commands and translate them into LIFX API calls.

### Default Behavior

The default system prompt tells Claude to:

1. **Understand your intent** - Parse natural language like "turn on bedroom lights" or "make beam purple and red"
2. **Match to actual devices** - Use the exact light IDs, group IDs, and scene UUIDs from your LIFX setup
3. **Generate API actions** - Output structured JSON with the appropriate HTTP methods and endpoints
4. **Handle multi-zone devices** - Automatically split gradient commands across Beam/Strip zones

### Expected Response Format

Claude returns JSON with this structure:

```json
{
  "actions": [
    {
      "method": "PUT",
      "endpoint": "/api/lights/group_id:abc123/state",
      "body": {"power": "on", "color": "red", "brightness": 1.0, "duration": 1.0},
      "description": "Set bedroom lights to red"
    }
  ],
  "summary": "Setting bedroom lights to red"
}
```

### Supported Actions

| Action Type | Endpoint Pattern | Description |
|-------------|------------------|-------------|
| Toggle light | `PUT /api/toggle/{light_id}` | Turn individual light on/off |
| Activate scene | `PUT /api/scene/{scene_uuid}` | Activate a saved scene |
| Toggle room | `PUT /api/group/{group_id}/toggle` | Toggle all lights in a room |
| Set state | `PUT /api/lights/{selector}/state` | Set color, brightness, power |

### Color Formats

The AI understands multiple color formats:
- **Named colors**: `red`, `blue`, `green`, `purple`, `orange`, `white`, `warm white`
- **Hex codes**: `#ff0000`, `#6b5b95`
- **Kelvin temperatures**: `kelvin:2700` (warm), `kelvin:6500` (cool)
- **HSB values**: `hue:240 saturation:1.0`

### Important Behaviors

- **Brightness defaults to 100%** when setting colors (ensures lights are visible)
- **Power is always set to "on"** with color commands
- **Duration defaults to 1 second** for smooth transitions
- **Group IDs must match exactly** - the AI uses the actual IDs from your LIFX context

### Customizing the System Prompt

You can edit the system prompt in Settings to:
- Add custom command shortcuts (e.g., "movie mode" → specific scene)
- Change default brightness or duration
- Add device-specific instructions
- Restrict certain actions
- Change the response verbosity

**To customize:**
1. Click the Settings gear icon
2. Scroll to "System Prompt" textarea
3. Edit the prompt (or click "Restore Default" to reset)
4. Click "Save Settings"

**Tips for custom prompts:**
- Keep the JSON response format instructions
- Include the `{context}` marker where device data should be injected
- Test changes with simple commands first
- The original default is always available via "Restore Default"

## API Endpoints

### Settings Management
- `GET /api/settings` - Get current configuration (masked)
- `POST /api/settings` - Update configuration
- `GET /api/models` - Get available Claude models
- `GET /api/default-prompt` - Get the default system prompt

### Light Control
- `GET /api/lights` - Get all lights
- `GET /api/scenes` - Get all scenes
- `GET /api/scenes/status/batch` - Get scene statuses (optimized)
- `GET /api/scene/<uuid>/debug` - Debug scene matching (see expected vs actual)
- `PUT /api/toggle/<selector>` - Toggle light/group
- `PUT /api/scene/<uuid>` - Activate scene
- `PUT /api/group/<id>/toggle` - Toggle room
- `PUT /api/lights/<selector>/state` - Set light state

### Natural Language
- `POST /api/natural-language` - Process natural language command

### Debug Mode

Enable detailed logging:
```bash
export FLASK_DEBUG=1
python app.py
```

Check API details panel (eye icon) for:
- Exact API requests sent
- Response status codes
- Error messages from LIFX API

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Additional Resources

- [LIFX API Documentation](https://api.developer.lifx.com/)
- [Claude API Documentation](https://docs.anthropic.com/)

---
