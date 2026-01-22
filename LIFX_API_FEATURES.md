# LIFX API Features - Gap Analysis for Via Clara

**Research Date:** January 22, 2026
**API Documentation:** [api.developer.lifx.com](https://api.developer.lifx.com)
**Current Via Clara Version:** v1.0 (495 lines in app.py)

## Executive Summary

Via Clara currently uses **6 out of 18+ available LIFX HTTP API endpoints** (33% coverage). The application focuses on basic light control, scene activation, and natural language processing but misses significant features including:

- **10 visual effect endpoints** (breathe, pulse, move, morph, flame, etc.)
- **4 advanced control endpoints** (state delta, set states, cycle, effects off)
- **3 utility endpoints** (validate color, clean mode, enhanced device info)
- **Multiple state parameters** (infrared, fast mode, persist)
- **Advanced selector features** (location-based, scene-based)

This represents significant opportunities to enhance user experience with minimal development effort, particularly in areas like visual effects, batch operations, and incremental adjustments.

---

## Table of Contents

1. [Current API Usage](#current-api-usage)
2. [Visual Effects (Missing)](#visual-effects-missing)
3. [Advanced State Management (Missing)](#advanced-state-management-missing)
4. [Batch & Optimization Features (Missing)](#batch--optimization-features-missing)
5. [Utility & Validation (Missing)](#utility--validation-missing)
6. [Advanced Parameters (Missing)](#advanced-parameters-missing)
7. [Selector Enhancements (Partial)](#selector-enhancements-partial)
8. [Device Capabilities (Underutilized)](#device-capabilities-underutilized)
9. [Rate Limit Management (Basic)](#rate-limit-management-basic)
10. [Priority Recommendations](#priority-recommendations)

---

## Current API Usage

### Endpoints Currently Used ✅

| Endpoint | Method | Purpose | File Reference |
|----------|--------|---------|----------------|
| `/lights/all` | GET | List all lights | app.py:171, 208, 237, 385 |
| `/scenes` | GET | List all scenes | app.py:179, 213, 242, 386 |
| `/lights/{selector}/toggle` | POST | Toggle lights on/off | app.py:187, 461, 469 |
| `/scenes/scene_id:{uuid}/activate` | PUT | Activate scene | app.py:196, 465 |
| `/lights/group_id:{id}/toggle` | POST | Toggle room/group | app.py:268, 469 |
| `/lights/{selector}/state` | PUT | Set color/brightness/power | app.py:284, 478 |

### Features Currently Implemented ✅

- ✅ Basic light control (on/off, color, brightness)
- ✅ Scene activation
- ✅ Room/group toggling
- ✅ Multi-zone support for LIFX Beam (zone selectors like `id:xxx|0-4`)
- ✅ Natural language processing via Claude AI
- ✅ Basic rate limit tracking (120 req/min)
- ✅ State parameters: power, color, brightness, duration
- ✅ Selector types: `all`, `id:xxx`, `group_id:xxx`, zone ranges

---

## Visual Effects (Missing)

**Priority: HIGH** - These features add significant visual appeal with minimal backend complexity. All effects work via POST requests with simple JSON payloads.

### 1. Breathe Effect ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/breathe`

**What it does:** Creates a smooth pulsing animation that fades between two colors, like breathing.

**Parameters:**
```json
{
  "color": "blue",           // Required: target color
  "from_color": "red",       // Optional: starting color (defaults to current)
  "period": 1.0,             // Optional: seconds per cycle (default: 1)
  "cycles": 5.0,             // Optional: number of repeats (default: 1)
  "persist": false,          // Optional: keep final color after effect (default: false)
  "power_on": true,          // Optional: turn on if off (default: true)
  "peak": 0.5                // Optional: 0.0-1.0, when max intensity occurs (default: 0.5)
}
```

**Use Cases for Via Clara:**
- "make bedroom lights breathe blue"
- "create a relaxing breathing effect in living room"
- "breathe between red and purple in the office"
- Party mode scenes
- Meditation/relaxation modes
- Notification effects (e.g., breathe when doorbell rings)

**Implementation Effort:** Low (single POST endpoint)

**Documentation:** [LIFX Breathe Effect](https://api.developer.lifx.com/docs/breathe-effect)

---

### 2. Pulse Effect ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/pulse`

**What it does:** Similar to breathe but without the `peak` parameter - creates a simpler alternating effect between colors.

**Parameters:**
```json
{
  "color": "purple",         // Required: target color
  "from_color": "white",     // Optional: starting color
  "period": 0.5,             // Optional: seconds per cycle
  "cycles": 10.0,            // Optional: number of repeats
  "persist": false,          // Optional: keep final color
  "power_on": true           // Optional: turn on if off
}
```

**Use Cases for Via Clara:**
- "pulse the kitchen lights red"
- "create a quick pulsing alert in bedroom"
- Faster, more dramatic effects than breathe
- Alert/notification animations
- Party/entertainment scenes

**Implementation Effort:** Low (single POST endpoint)

**Documentation:** [LIFX Pulse Effect](https://api.developer.lifx.com/docs/pulse-effect)

---

### 3. Move Effect (Multi-Zone) ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/move`

**What it does:** For multi-zone devices (Beam, Z Strip), moves the current color pattern across zones in a direction, creating a flowing animation.

**Parameters:**
```json
{
  "direction": "forward",    // "forward" or "backward"
  "period": 1.0,             // Seconds for one complete cycle
  "cycles": null,            // Number of cycles (null = infinite, 0 = stop)
  "power_on": true,          // Turn on if off
  "fast": false              // Skip state checks
}
```

**Use Cases for Via Clara:**
- "make the beam colors flow forward"
- "create a moving rainbow on the strip"
- "animate the beam backward"
- Dynamic accent lighting
- Entertainment mode for TV/gaming setups
- Visual interest for parties

**Device Support:** LIFX Beam, LIFX Z Strip, LIFX Lightstrip

**Implementation Effort:** Low (Via Clara already supports multi-zone via zone selectors)

**Documentation:** [LIFX Move Effect](https://api.developer.lifx.com/docs/move-effect)

---

### 4. Morph Effect (Tile Devices) ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/morph`

**What it does:** Creates dynamic, flowing color animations across LIFX Tile devices. Brightness is controlled independently via SetState, allowing palette animation without brightness changes.

**Parameters:**
```json
{
  "period": 5.0,             // Animation speed in seconds (default: 5)
  "duration": null,          // Total duration (null = continuous, 0 = stop)
  "palette": [               // Array of colors (default: 7 spectrum colors)
    "red", "orange", "yellow", "green", "cyan", "blue", "purple"
  ],
  "power_on": true,          // Turn on if off
  "fast": false              // Skip state checks
}
```

**Use Cases for Via Clara:**
- "morph the tiles with rainbow colors"
- "create a flowing animation on tiles"
- "animate tiles with warm colors"
- Ambient lighting for entertainment areas
- Visual art installations
- Dynamic accent walls

**Device Support:** LIFX Tile (only)

**Implementation Effort:** Low (single POST endpoint)

**Note:** Via Clara would need to detect if user has LIFX Tiles via the `product.name` field from `/lights/all`

**Documentation:** [LIFX Morph Effect](https://api.developer.lifx.com/docs/morph-effect)

---

### 5. Flame Effect (Tile Devices) ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/flame`

**What it does:** Creates a realistic flickering flame effect on LIFX Tile devices. Brightness is determined by tile brightness, not the effect itself.

**Parameters:**
```json
{
  "period": 5.0,             // Animation speed (lower = faster flicker)
  "duration": null,          // Total duration (null = continuous, 0 = stop)
  "power_on": true,          // Turn on if off
  "fast": false              // Skip state checks
}
```

**Use Cases for Via Clara:**
- "create a fireplace effect on tiles"
- "make tiles look like flickering flames"
- Cozy ambiance for winter evenings
- Romantic dinner lighting
- Halloween/themed party effects

**Device Support:** LIFX Tile (only)

**Implementation Effort:** Low (single POST endpoint)

**Documentation:** [LIFX Flame Effect](https://api.developer.lifx.com/docs/flame-effect)

---

### 6. Effects Off ❌

**Endpoint:** `POST /v1/lights/{selector}/effects/off`

**What it does:** Turns off any running effects (breathe, pulse, move, morph, flame) and optionally powers off the lights.

**Parameters:**
```json
{
  "power_off": false         // Optional: also turn off lights (default: false)
}
```

**Use Cases for Via Clara:**
- "stop all effects"
- "turn off the breathing animation"
- "cancel effects and turn off lights"
- Critical for stopping infinite/long-duration effects
- Clean state management

**Implementation Effort:** Very Low (single POST endpoint)

**Note:** This is essential if implementing any effects, otherwise users have no way to stop them via the dashboard.

**Documentation:** [LIFX Effects Off](https://api.developer.lifx.com/docs/effects-off)

---

### Effect Implementation Strategy

**Recommended Approach:**

1. **Phase 1 (High Value):** Implement Breathe and Pulse
   - Most versatile, work on all lights
   - Natural language examples: "breathe blue", "pulse red 5 times"

2. **Phase 2 (Multi-Zone Support):** Implement Move
   - Leverages existing multi-zone infrastructure
   - Natural language: "flow colors forward on beam"

3. **Phase 3 (Tile Support):** Implement Morph and Flame
   - Only for users with Tiles
   - Detect via `product.name` containing "Tile"

4. **Always Include:** Effects Off
   - Critical for user control
   - Natural language: "stop effects", "cancel animation"

**UI Considerations:**
- Add "Effects" section to dashboard
- Show currently running effect status (from `/lights/all` → `effect` field)
- One-click "Stop All Effects" button
- Preset effect configurations ("Relax", "Party", "Alert")

---

## Advanced State Management (Missing)

**Priority: MEDIUM-HIGH** - These features enable more sophisticated control patterns and batch operations.

### 7. State Delta (Incremental Changes) ❌

**Endpoint:** `POST /v1/lights/{selector}/state/delta`

**What it does:** Applies **relative/incremental** changes to light state instead of absolute values. Changes the state by the amount specified, not to a specific value.

**Parameters:**
```json
{
  "power": "on",             // Absolute: on or off
  "duration": 1.0,           // Absolute: transition time
  "infrared": 0.1,           // Delta: increase IR by 0.1
  "hue": 45.0,               // Delta: rotate hue by +45 degrees (-360 to 360)
  "saturation": 0.2,         // Delta: increase saturation by 0.2 (clipped to 0-1)
  "brightness": -0.1,        // Delta: decrease brightness by 0.1 (clipped to 0-1)
  "kelvin": 500,             // Delta: increase kelvin by 500 (clipped to 2500-9000)
  "fast": false              // Skip state checks
}
```

**Key Difference from Set State:**
- **Set State:** "Set brightness to 0.5"
- **State Delta:** "Increase brightness by 0.1"

**Use Cases for Via Clara:**
- "brighten all lights by 20%"
- "make bedroom warmer" (increase kelvin)
- "dim living room a bit" (negative brightness delta)
- "rotate hue 30 degrees"
- Relative slider controls in UI
- "Brighter" / "Dimmer" quick action buttons
- Proportional adjustments across mixed brightness levels

**Example Natural Language:**
- User: "brighten bedroom by 25%"
- API: `POST /lights/group:bedroom/state/delta` with `{"brightness": 0.25}`
- Result: Light at 50% → 75%, light at 30% → 55% (proportional)

**Implementation Effort:** Low (single POST endpoint, similar to existing state endpoint)

**Documentation:** [LIFX State Delta](https://api.developer.lifx.com/docs/state-delta)

---

### 8. Set States (Plural - Batch Operations) ❌

**Endpoint:** `PUT /v1/lights/states`

**What it does:** Apply **different states to multiple selectors in a single API call** (max 50 operations). Dramatically reduces API calls for complex scenes.

**Parameters:**
```json
{
  "states": [                // Required: array of state objects (max 50)
    {
      "selector": "group:bedroom",
      "power": "on",
      "brightness": 0.5,
      "color": "warm white"
    },
    {
      "selector": "group:kitchen",
      "power": "on",
      "brightness": 1.0,
      "color": "bright white"
    },
    {
      "selector": "id:d073d5123456",
      "power": "on",
      "color": "purple"
    }
  ],
  "defaults": {              // Optional: applied to all states if not specified
    "duration": 2.0,
    "power": "on"
  },
  "fast": false              // Optional: skip state checks
}
```

**Use Cases for Via Clara:**
- **Custom scene creation:** "Set bedroom to 50%, kitchen to full, and living room off"
- **Complex natural language:** "dim bedroom, brighten kitchen, and make living room purple"
- **Morning routine:** Different brightness/color per room in one command
- **Night mode:** Dim all lights to different levels simultaneously
- **API efficiency:** Reduce from N API calls to 1 API call

**Current Limitation:**
Via Clara executes actions sequentially with delays between multi-zone commands (300ms). Set States could execute them in parallel via the API.

**Example:**
```python
# Current Via Clara: 3 separate API calls + delays
PUT /lights/group:bedroom/state  → {"brightness": 0.5}
time.sleep(0.3)
PUT /lights/group:kitchen/state  → {"brightness": 1.0}
time.sleep(0.3)
PUT /lights/group:living/state   → {"power": "off"}

# With Set States: 1 API call
PUT /lights/states → {"states": [{bedroom}, {kitchen}, {living}]}
```

**Implementation Effort:** Medium (requires restructuring Claude's action planning to group state changes)

**Benefits:**
- **Faster execution** (parallel vs sequential)
- **Fewer rate limit issues** (1 call vs N calls)
- **Better UX** (simultaneous state changes across house)

**Documentation:** [LIFX Set States](https://api.developer.lifx.com/docs/set-states)

---

### 9. Cycle ❌

**Endpoint:** `POST /v1/lights/{selector}/cycle`

**What it does:** Automatically cycles lights through a predefined sequence of states based on current state. The API determines which state to apply next, enabling simple "toggle through options" behavior.

**Parameters:**
```json
{
  "states": [                // Required: 2-10 state objects
    {
      "power": "on",
      "brightness": 0.2,
      "color": "warm white"
    },
    {
      "power": "on",
      "brightness": 0.5,
      "color": "warm white"
    },
    {
      "power": "on",
      "brightness": 1.0,
      "color": "bright white"
    }
  ],
  "defaults": {              // Optional: applied to all states
    "duration": 1.0
  },
  "direction": "forward"     // "forward" or "backward"
}
```

**How it works:**
1. API scores current light state against each state in the array
2. If current state matches one (high score), API applies the **next** state in sequence
3. Loops back to first state after reaching the end
4. If no match, applies first state

**Use Cases for Via Clara:**
- **Brightness cycling:** "cycle bedroom brightness" → 20% → 50% → 100% → 20% → ...
- **Color temperature cycling:** warm → neutral → cool → warm
- **Scene cycling:** Click same button to cycle through scene variants
- **Physical button integration:** Same API call cycles through states
- **Quick toggles:** One natural language command cycles through options

**Example Natural Language:**
- User: "cycle living room brightness" (first call)
  - API checks current state, applies next in sequence
- User: "cycle living room brightness" (second call)
  - API checks new state, applies next in sequence

**Implementation Effort:** Medium (requires defining state sequences, possibly in config)

**UI Potential:**
- "Cycle" button next to room controls
- Predefined cycling presets ("Brightness Levels", "Color Temps", "Scene Variants")

**Documentation:** [LIFX Cycle](https://api.developer.lifx.com/docs/cycle)

---

## Batch & Optimization Features (Missing)

Via Clara partially uses optimization (batch scene status checking via `/api/scenes/status/batch`), but misses key features for efficiency and advanced UX.

### 10. Fast Mode Parameter ❌

**What it is:** A boolean parameter (`"fast": true`) available on most state-changing endpoints.

**What it does:**
- Skips initial device state checks
- Doesn't wait for device responses
- Returns `202 Accepted` immediately instead of waiting for completion
- Significantly faster for rapid-fire commands

**Available on:**
- `PUT /lights/{selector}/state`
- `POST /lights/{selector}/state/delta`
- `PUT /lights/states`
- All effect endpoints (breathe, pulse, move, morph, flame)

**Use Cases for Via Clara:**
- **Rapid natural language commands:** User sends multiple commands quickly
- **UI responsiveness:** Button clicks return instantly
- **Non-critical operations:** User doesn't need confirmation
- **High-frequency updates:** Slider adjustments, animations

**Current Limitation:**
Via Clara waits for responses from every API call, causing delays for multi-step operations.

**Example:**
```python
# Current (slow): waits for response
response = requests.put(f"{BASE_URL}/lights/all/state",
                       json={"brightness": 0.5})
# Blocks until lights respond

# With fast=true (instant):
response = requests.put(f"{BASE_URL}/lights/all/state",
                       json={"brightness": 0.5, "fast": true})
# Returns 202 immediately
```

**Implementation Effort:** Very Low (add `"fast": true` to request bodies)

**Recommendation:** Use `fast: true` for:
- Natural language commands (user expects instant feedback)
- Effect triggers (breathe, pulse, etc.)
- State delta operations (incremental changes)

**Avoid `fast: true` for:**
- Critical operations requiring confirmation
- Error-sensitive operations
- When you need detailed response data

---

## Utility & Validation (Missing)

**Priority: MEDIUM** - Quality-of-life features that improve reliability and UX.

### 11. Validate Color ❌

**Endpoint:** `GET /v1/color?string={color_string}`

**What it does:** Validates a color string and returns the HSBK values the API will interpret, or returns error if invalid.

**Response:**
```json
{
  "hue": 120.0,              // 0-360
  "saturation": 1.0,         // 0-1
  "brightness": 0.5,         // 0-1 (optional)
  "kelvin": 3500             // 1500-9000 (optional)
}
```

**Use Cases for Via Clara:**
- **Pre-validation:** Check user color input before sending to lights
- **Error prevention:** Show validation errors in UI before API call
- **Color preview:** Show user what color will be applied
- **Natural language feedback:** "I interpreted that as blue (hue: 250°)"
- **Learning tool:** Help users understand HSBK values

**Example Flow:**
1. User types: "make lights #ff5733"
2. Via Clara calls: `GET /v1/color?string=%23ff5733`
3. API returns: `{"hue": 13.5, "saturation": 0.8, "brightness": 1.0}`
4. Via Clara shows preview or applies to lights

**Implementation Effort:** Very Low (single GET endpoint)

**Documentation:** [LIFX Validate Color](https://api.developer.lifx.com/docs/validate-color)

---

### 12. Clean Mode (HEV) ❌

**Endpoint:** `POST /v1/lights/{selector}/clean`

**What it does:** Activates HEV (High Energy Visible light) mode on compatible devices for UV sterilization/cleaning cycles.

**Parameters:**
```json
{
  "stop": false,             // Stop clean mode (default: false)
  "duration": 3600           // Duration in seconds (0 or blank = device default)
}
```

**Device Support:** LIFX Clean (HEV-capable devices only)

**Use Cases for Via Clara:**
- "start cleaning mode in bedroom"
- "run HEV cycle for 30 minutes"
- "stop clean mode"
- Scheduled cleaning routines
- Voice control via natural language
- Integration with home automation

**Detection:**
Check `product.capabilities.has_hev` from `/lights/all` response (if available).

**Implementation Effort:** Low (single POST endpoint)

**Market Note:** LIFX Clean is a specialized product. This feature is low priority unless Via Clara aims to support all LIFX devices comprehensively.

**Documentation:** [LIFX Clean](https://api.developer.lifx.com/docs/clean)

---

## Advanced Parameters (Missing)

These parameters are available on existing endpoints but not currently used by Via Clara.

### 13. Infrared Parameter ❌

**What it is:** A state parameter (`"infrared": 0.0-1.0`) for devices with infrared LEDs.

**Available on:**
- `PUT /lights/{selector}/state`
- `POST /lights/{selector}/state/delta`
- `PUT /lights/states`

**What it does:**
Sets the maximum brightness of the infrared channel (0.0 = off, 1.0 = full IR).

**Device Support:**
- Devices with `"has_ir": true` in capabilities (check via `/lights/all`)
- LIFX+ bulbs (discontinued but still in use)
- LIFX Nightvision (if exists)

**Use Cases for Via Clara:**
- **Security cameras:** "set office lights to IR mode" (for night vision cameras)
- **Night vision:** Lights that provide illumination without visible light
- **Photography/videography:** Controlled IR lighting setups
- "enable infrared at 50% in garage"

**Detection:**
```json
// From /lights/all response
{
  "capabilities": {
    "has_ir": true,
    "min_kelvin": 2500,
    "max_kelvin": 9000
  }
}
```

**Implementation Effort:** Very Low (add to state request bodies when detected)

**Current Limitation:**
Via Clara doesn't expose or use infrared control, even for IR-capable devices.

---

### 14. Persist Parameter (Effects) ❌

**What it is:** A boolean parameter (`"persist": true/false`) available on effect endpoints.

**Available on:**
- Breathe effect
- Pulse effect

**What it does:**
- `"persist": false` (default) → Light returns to original state after effect completes
- `"persist": true` → Light remains at final effect color after completion

**Use Cases for Via Clara:**
- **Temporary alerts:** `persist: false` → Flash red then return to original
- **Permanent transitions:** `persist: true` → Breathe to new color and stay there
- **Notification effects:** Show effect then revert automatically
- "breathe to blue and stay there" vs "breathe blue temporarily"

**Implementation Effort:** Very Low (add to effect request bodies)

---

### 15. Peak Parameter (Breathe Effect) ❌

**What it is:** A float parameter (`"peak": 0.0-1.0`) for the breathe effect.

**What it does:**
Defines where in the cycle the target color reaches maximum intensity:
- `0.0` → Peak at start of cycle
- `0.5` (default) → Peak at middle (symmetric)
- `1.0` → Peak at end of cycle

**Use Cases for Via Clara:**
- Asymmetric breathing patterns
- Customized animation feel
- Advanced effect control for power users

**Implementation Effort:** Very Low (add to breathe effect requests)

---

## Selector Enhancements (Partial)

Via Clara uses `all`, `id:xxx`, `group_id:xxx`, and zone selectors (`id:xxx|0-4`). Several selector types are unused.

### 16. Location-Based Selectors ⚠️ (Unused)

**Syntax:**
- `location_id:{id}` → Target lights in a specific location by ID
- `location:{label}` → Target lights in locations matching label

**What it is:**
LIFX allows organizing lights into "locations" (different from groups/rooms). Locations are typically physical locations like "Home", "Office", "Vacation House".

**Current Via Clara Usage:** ❌ Not using location selectors

**Use Cases:**
- Multi-home setups: "turn off all lights at vacation house"
- Large deployments: Corporate offices, hotels, multi-building campuses
- Whole-location control: "turn off all lights at home"

**Implementation Effort:** Low (just expose in natural language, works automatically)

**Note:** Most home users don't use locations, so low priority for Via Clara's target audience.

---

### 17. Scene-Based Selectors ⚠️ (Unused)

**Syntax:**
- `scene_id:{uuid}` → Target all lights referenced in a specific scene

**What it is:**
Select all lights that are part of a particular scene, useful for bulk operations on scene-specific lights.

**Current Via Clara Usage:** ❌ Not using scene selectors

**Use Cases:**
- "turn off all lights in movie scene" (without activating scene)
- "set all lights from party scene to 50% brightness"
- Modify scene lights without applying scene state

**Implementation Effort:** Low

**Documentation:** [LIFX Selectors](https://api.developer.lifx.com/docs/selectors)

---

### 18. Label-Based Selectors ⚠️ (Caution)

**Syntax:**
- `label:{name}` → Target lights by custom name

**Current Via Clara Usage:** ❌ Not exposed (using `id:` instead)

**Why Unused:**
The LIFX API documentation warns: *"Generally, you should avoid using label-based selectors... when developing an application as they will break if users rename"* the labels.

**Recommendation:** Continue avoiding label-based selectors in favor of ID-based selectors for stability.

---

## Device Capabilities (Underutilized)

Via Clara fetches device information from `/lights/all` but doesn't utilize many available fields.

### 19. Capabilities Object ⚠️ (Underutilized)

**What it is:**
Every light in the `/lights/all` response includes a `capabilities` object with feature flags.

**Available Capabilities:**
```json
{
  "has_color": true,           // Supports color (vs white-only)
  "has_variable_color_temp": true,  // Supports kelvin adjustment
  "has_ir": false,             // Has infrared LEDs
  "has_chain": false,          // Is part of a chain (Tiles)
  "has_multizone": true,       // Has individually addressable zones
  "has_hev": false,            // Has HEV cleaning mode (if exposed)
  "min_kelvin": 2500,          // Minimum color temperature
  "max_kelvin": 9000           // Maximum color temperature
}
```

**Current Via Clara Usage:**
- ✅ Uses `product.name` to detect multi-zone devices (LIFX Beam)
- ❌ Doesn't use `capabilities` object for feature detection

**Missed Opportunities:**

1. **Feature Availability:**
   - Only show color controls for `has_color: true` devices
   - Only show kelvin controls for `has_variable_color_temp: true`
   - Only show IR controls for `has_ir: true`

2. **Validation:**
   - Validate kelvin input against `min_kelvin` and `max_kelvin`
   - Prevent color commands on white-only bulbs

3. **Natural Language Intelligence:**
   - "make lights infrared" → Only apply to lights with `has_ir: true`
   - "set color to red" → Skip devices with `has_color: false`

4. **UI Enhancement:**
   - Show capability badges on light cards ("Color", "IR", "Multi-Zone")
   - Disable unsupported controls in UI

**Implementation Effort:** Low (parse existing response data)

---

### 20. Product Information ⚠️ (Underutilized)

**What it is:**
Each light includes detailed product metadata:

```json
{
  "product": {
    "name": "LIFX Beam",       // User-friendly product name
    "identifier": "lifx_beam", // Product identifier
    "company": "LIFX",         // Manufacturer
    "vendor_id": 1,            // Vendor ID
    "product_id": 38,          // Product ID
    "capabilities": {...}      // Capabilities object
  }
}
```

**Current Via Clara Usage:**
- ✅ Uses `product.name` to detect Beam/Strip/Lightstrip
- ❌ Doesn't display product info in UI

**Missed Opportunities:**
- Show product name in light cards ("LIFX Beam" vs "LIFX Bulb")
- Product-specific help text or tips
- Filter/group by product type
- Better multi-zone detection (check `capabilities.has_multizone` instead of string matching)

**Implementation Effort:** Very Low (display existing data)

---

### 21. Current Effect Status ⚠️ (Underutilized)

**What it is:**
The `/lights/all` response includes an `effect` field showing the currently running effect:

```json
{
  "effect": "OFF"           // Or "MORPH", "MOVE", "FLAME", etc.
}
```

**Current Via Clara Usage:** ❌ Not displayed or used

**Missed Opportunities:**
- Show "Effect: BREATHE" badge on light cards
- "Stop Effect" button for lights with active effects
- Prevent conflicting state changes while effect is running
- Natural language awareness: "the bedroom lights are already breathing"

**Implementation Effort:** Very Low (display existing data)

**Recommendation:** If implementing effects, this field is critical for status display.

---

### 22. Zone Information ⚠️ (Partial)

**What it is:**
Multi-zone lights include detailed zone information:

```json
{
  "zones": {
    "count": 61,             // Total number of zones
    "zones": [               // Array of zone states
      {
        "hue": 120.0,
        "saturation": 1.0,
        "brightness": 0.8,
        "kelvin": 3500
      },
      // ... more zones
    ]
  }
}
```

**Current Via Clara Usage:**
- ✅ Supports zone selectors (`id:xxx|0-4`)
- ✅ Creates gradients by splitting zones
- ❌ Doesn't visualize zone states in UI

**Missed Opportunities:**
- Visual zone display (color bar showing current gradient)
- Per-zone color editing
- Zone count validation (ensure zone ranges are valid)
- More intelligent gradient distribution based on actual zone count

**Implementation Effort:** Medium (requires UI component for visualization)

---

### 23. Tile/Chain Information ⚠️ (Unused)

**What it is:**
LIFX Tile devices include chain configuration showing tile layout:

```json
{
  "chain": [                 // Array of tiles in chain
    {
      "index": 0,            // Tile position in chain
      "x": 0,                // Grid X position
      "y": 0,                // Grid Y position
      "width": 8,            // Tile width in zones
      "height": 8,           // Tile height in zones
      "device_id": "d073d5...",
      "colors": [...]        // 64-element array (8x8 zones)
    },
    // ... more tiles
  ]
}
```

**Current Via Clara Usage:** ❌ Not used (Via Clara doesn't support Tile-specific features)

**Use Cases:**
- Visualize tile layout in UI
- Per-tile control
- Tile-specific effects (morph, flame)
- Artistic tile configurations

**Implementation Effort:** High (requires understanding tile geometry and zone addressing)

**Priority:** Low (Tiles are specialized devices, small market share)

---

## Rate Limit Management (Basic)

Via Clara has **basic** rate limit tracking but misses several optimizations.

### 24. Rate Limit Headers ⚠️ (Partial)

**Available Headers:**
```http
X-RateLimit-Limit: 120          # Max requests per window
X-RateLimit-Remaining: 87       # Requests left in current window
X-RateLimit-Reset: 1737549120   # Unix timestamp when window resets
```

**Current Via Clara Usage:**
- ✅ Tracks `X-RateLimit-Remaining` (app.py:131)
- ✅ Tracks `X-RateLimit-Reset` (app.py:132)
- ✅ Checks before making requests (app.py:134)
- ❌ Doesn't expose to frontend
- ❌ Doesn't show in UI

**Missed Opportunities:**
- Show rate limit status in UI ("87/120 API calls remaining")
- Warn user when approaching limit
- Throttle natural language commands if rate limit is low
- Better error messages ("Rate limit exceeded, resets in 23 seconds")

**Implementation Effort:** Low (expose existing backend data to frontend)

**Documentation:** [LIFX Rate Limits](https://api.developer.lifx.com/docs/rate-limits)

---

### 25. Batch Operations for Rate Limit Efficiency ⚠️ (Partial)

**Current Via Clara Optimization:**
- ✅ Uses `/api/scenes/status/batch` to check all scenes in one call
- ✅ Reduced from 2+2N to 3 API calls per refresh

**Missed Opportunities:**
- Use `PUT /lights/states` for batch operations (discussed in #8)
- Use `fast: true` to reduce wait times (discussed in #10)
- Combine multiple natural language actions into single Set States call

**Recommendation:**
Via Clara already does good optimization for scene status. Extend this pattern to state changes.

---

## Priority Recommendations

Based on value, implementation effort, and user impact, here are prioritized recommendations:

### 🔥 High Priority (High Value, Low Effort)

1. **Breathe & Pulse Effects**
   - **Value:** Dramatically enhances visual appeal and user engagement
   - **Effort:** Low (2 simple POST endpoints)
   - **Implementation:** Add to natural language system, minimal UI changes
   - **User Impact:** High - "breathing" lights are visually impressive

2. **Effects Off**
   - **Value:** Essential for user control if effects are implemented
   - **Effort:** Very Low (single POST endpoint)
   - **Implementation:** One-line natural language support
   - **User Impact:** Critical for stopping effects

3. **State Delta (Incremental Changes)**
   - **Value:** Enables "brighten", "dim", "warmer", "cooler" natural language
   - **Effort:** Low (single POST endpoint, similar to existing state)
   - **Implementation:** Add to Claude's natural language understanding
   - **User Impact:** High - more intuitive control

4. **Fast Mode Parameter**
   - **Value:** Instant UI response, better UX
   - **Effort:** Very Low (add `"fast": true` to existing requests)
   - **Implementation:** One-line change to request bodies
   - **User Impact:** Medium - noticeable responsiveness improvement

5. **Validate Color**
   - **Value:** Better error handling, user feedback
   - **Effort:** Very Low (single GET endpoint)
   - **Implementation:** Call before applying colors in natural language
   - **User Impact:** Medium - prevents errors, educates users

### ⚡ Medium Priority (Good Value, Medium Effort)

6. **Set States (Batch Operations)**
   - **Value:** API efficiency, simultaneous state changes
   - **Effort:** Medium (requires restructuring action execution)
   - **Implementation:** Modify Claude's response to group state changes
   - **User Impact:** Medium-High - faster, more synchronized

7. **Move Effect (Multi-Zone)**
   - **Value:** Leverages existing multi-zone support, visual appeal
   - **Effort:** Low (Via Clara already handles zones)
   - **Implementation:** Natural language + POST endpoint
   - **User Impact:** Medium - cool effect for Beam/Strip owners

8. **Infrared Support**
   - **Value:** Unlocks use case for IR-capable devices
   - **Effort:** Low (add parameter when detected)
   - **Implementation:** Check capabilities, expose in natural language
   - **User Impact:** Low-Medium - only for IR device owners

9. **Cycle**
   - **Value:** Enables cycling through brightness/color presets
   - **Effort:** Medium (requires defining state sequences)
   - **Implementation:** Natural language + cycling config
   - **User Impact:** Medium - convenient for repetitive tasks

10. **Display Current Effect Status**
    - **Value:** Shows what effects are running
    - **Effort:** Very Low (display existing data from `/lights/all`)
    - **Implementation:** Add badge to UI when `effect != "OFF"`
    - **User Impact:** Medium - important context for users

### 🎯 Lower Priority (Specialized or High Effort)

11. **Morph & Flame Effects (Tiles)**
    - **Value:** Great for Tile owners, niche market
    - **Effort:** Low (single POST each)
    - **Implementation:** Detect Tile devices, add natural language
    - **User Impact:** Low (small user base), High (for Tile owners)

12. **Clean Mode (HEV)**
    - **Value:** Specialized use case, small market
    - **Effort:** Low (single POST endpoint)
    - **Implementation:** Detect HEV devices, add natural language
    - **User Impact:** Low (very specialized product)

13. **Tile Visualization & Control**
    - **Value:** Advanced feature for Tile owners
    - **Effort:** High (complex UI, chain geometry)
    - **Implementation:** Requires tile layout visualization
    - **User Impact:** Medium (for Tile owners only)

14. **Zone Visualization**
    - **Value:** Shows current gradient on multi-zone devices
    - **Effort:** Medium (UI component for color bar)
    - **Implementation:** Parse zone data, render visualization
    - **User Impact:** Medium - nice-to-have for Beam/Strip

15. **Location & Scene-Based Selectors**
    - **Value:** Advanced control for power users
    - **Effort:** Low (expose in natural language)
    - **Implementation:** Add to Claude's selector vocabulary
    - **User Impact:** Low (most users don't need this)

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
- ✅ Add `fast: true` parameter to state changes
- ✅ Implement Breathe effect
- ✅ Implement Pulse effect
- ✅ Implement Effects Off
- ✅ Validate Color endpoint integration
- ✅ Display current effect status in UI

**Impact:** Major visual upgrade, instant responsiveness

### Phase 2: Advanced Control (3-5 days)
- ✅ State Delta for incremental changes
- ✅ Set States for batch operations
- ✅ Infrared support (if IR devices detected)
- ✅ Move effect for multi-zone devices
- ✅ Rate limit status in UI

**Impact:** More sophisticated control, better efficiency

### Phase 3: Specialized Features (5-7 days)
- ✅ Cycle endpoint for state cycling
- ✅ Morph & Flame effects for Tiles
- ✅ Clean mode for HEV devices
- ✅ Zone visualization for multi-zone
- ✅ Enhanced capability detection

**Impact:** Comprehensive LIFX feature coverage

---

## Technical Implementation Notes

### Natural Language Integration

For each new endpoint, Claude's system prompt needs to understand:

1. **New Action Types:**
   ```python
   # Add to DEFAULT_SYSTEM_PROMPT in app.py
   "5. Breathe effect: POST /api/lights/{selector}/effects/breathe"
   "6. Pulse effect: POST /api/lights/{selector}/effects/pulse"
   "7. Incremental changes: POST /api/lights/{selector}/state/delta"
   ```

2. **Parameter Formats:**
   ```python
   "For breathe/pulse effects:
   - color: target color
   - from_color: starting color (optional)
   - period: seconds per cycle (default: 1)
   - cycles: number of repeats (default: 1)
   - persist: keep final color (true/false)"
   ```

3. **Example Responses:**
   ```json
   {
     "actions": [
       {
         "method": "POST",
         "endpoint": "/api/lights/group:bedroom/effects/breathe",
         "body": {
           "color": "blue",
           "period": 2,
           "cycles": 5,
           "persist": false
         },
         "description": "Create breathing blue effect in bedroom (5 cycles)"
       }
     ],
     "summary": "Making bedroom lights breathe blue"
   }
   ```

### Flask Route Structure

New endpoints should follow Via Clara's existing patterns:

```python
@app.route('/api/lights/<selector>/effects/breathe', methods=['POST'])
@limiter.limit(FLASK_TOGGLE_RATE_LIMIT)
def breathe_effect(selector):
    data = request.get_json() or {}
    response = make_lifx_request('POST',
                                f"{BASE_URL}/lights/{selector}/effects/breathe",
                                headers=headers,
                                json=data)
    if isinstance(response, tuple):
        return response
    return jsonify({"status": response.status_code, "results": response.json()})
```

### Error Handling

Add validation for new parameters:

```python
# For effects
ALLOWED_EFFECT_PARAMS = ['color', 'from_color', 'period', 'cycles', 'persist', 'power_on', 'peak']

# For state delta
ALLOWED_DELTA_PARAMS = ['power', 'duration', 'infrared', 'hue', 'saturation', 'brightness', 'kelvin', 'fast']
```

### Frontend Considerations

- **Effect Controls:** Add "Effects" section to dashboard
- **Effect Status Badges:** Show "(BREATHING)" or "(PULSING)" on active lights
- **Stop Button:** One-click "Stop All Effects" in header
- **Rate Limit Display:** Show "API: 87/120" in status bar
- **Capability Indicators:** Show device icons (color, IR, zones, tiles)

---

## Conclusion

Via Clara has a solid foundation but uses only **33% of available LIFX API features**. The biggest opportunities are:

1. **Visual Effects** (breathe, pulse, move) - High user impact, low effort
2. **Advanced State Management** (delta, batch operations) - Better control, efficiency
3. **Capability Utilization** - Make full use of existing device data

Implementing **Phase 1 (Quick Wins)** would dramatically enhance Via Clara's appeal while requiring minimal development time. The effects system alone would differentiate Via Clara from basic LIFX controllers and showcase the power of natural language control.

---

## Sources & References

- [LIFX HTTP API Introduction](https://api.developer.lifx.com/)
- [LIFX API Reference](https://api.developer.lifx.com/reference/introduction)
- [LIFX Documentation](https://api.developer.lifx.com/docs/introduction)
- [LIFX Rate Limits](https://api.developer.lifx.com/docs/rate-limits)
- [LIFX Selectors](https://api.developer.lifx.com/docs/selectors)
- [LIFX Colors](https://api.developer.lifx.com/docs/colors)
- [Set State Endpoint](https://api.developer.lifx.com/docs/set-state)
- [Breathe Effect](https://api.developer.lifx.com/docs/breathe-effect)
- [Pulse Effect](https://api.developer.lifx.com/docs/pulse-effect)
- [Move Effect](https://api.developer.lifx.com/docs/move-effect)
- [Morph Effect](https://api.developer.lifx.com/docs/morph-effect)
- [Flame Effect](https://api.developer.lifx.com/docs/flame-effect)
- [State Delta](https://api.developer.lifx.com/docs/state-delta)
- [Set States](https://api.developer.lifx.com/docs/set-states)
- [Cycle](https://api.developer.lifx.com/docs/cycle)
- [Effects Off](https://api.developer.lifx.com/docs/effects-off)
- [Validate Color](https://api.developer.lifx.com/docs/validate-color)
- [Clean Mode](https://api.developer.lifx.com/docs/clean)
- [List Lights](https://api.developer.lifx.com/docs/list-lights)

---

**End of Document**
