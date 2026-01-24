"""
Constants and configuration values for LIFX Controller.
Centralizes magic numbers and configuration to improve maintainability.
"""

# LIFX API Configuration
LIFX_API_BASE_URL = "https://api.lifx.com/v1"

# Rate Limiting
LIFX_RATE_LIMIT_MAX = 120  # requests per minute
FLASK_DEFAULT_RATE_LIMIT = "100 per minute"
FLASK_LIGHTS_RATE_LIMIT = "30 per minute"
FLASK_TOGGLE_RATE_LIMIT = "60 per minute"
FLASK_NLP_RATE_LIMIT = "10 per minute"
FLASK_SETTINGS_RATE_LIMIT = "5 per minute"  # Stricter for sensitive endpoint

# Scene Status Detection Thresholds
BRIGHTNESS_TOLERANCE = 0.05  # 5% tolerance for brightness matching
SATURATION_TOLERANCE = 0.1   # 10% tolerance for saturation matching
HUE_TOLERANCE_DEGREES = 10   # degrees tolerance for hue matching
HUE_WRAPAROUND_THRESHOLD = 350  # degrees - handle 360 degree wraparound
KELVIN_TOLERANCE = 200  # kelvin tolerance for color temperature matching
SCENE_MATCH_THRESHOLD = 0.7  # 70% of lights must match for scene to be active

# Claude AI Configuration
CLAUDE_MAX_TOKENS = 1000
CLAUDE_DEFAULT_DURATION = 1.0  # seconds for light transitions

# Available Claude Models (as of 2026-01)
CLAUDE_MODELS = [
    {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "description": "Fast and cost-effective",
        "pricing": "$1/$5 per million tokens"
    },
    {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Balanced performance",
        "pricing": "$3/$15 per million tokens"
    },
    {
        "id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "description": "Most capable",
        "pricing": "$15/$75 per million tokens"
    }
]

# Default Claude model (fastest and cheapest)
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# HTTP Status Codes
HTTP_OK = 200
HTTP_MULTI_STATUS = 207
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500
