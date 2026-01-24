"""
Scene status detection and light state matching logic.
Extracts duplicate code from scene status endpoints.
"""

from typing import List, Dict, Any
from constants import (
    BRIGHTNESS_TOLERANCE,
    SATURATION_TOLERANCE,
    HUE_TOLERANCE_DEGREES,
    HUE_WRAPAROUND_THRESHOLD,
    KELVIN_TOLERANCE,
    SCENE_MATCH_THRESHOLD
)


class SceneMatcher:
    """Handles scene status detection and light state comparison"""

    @staticmethod
    def matches_selector(light: Dict[str, Any], selector: str) -> bool:
        """
        Check if a light matches a given selector string.

        Args:
            light: Light object from LIFX API
            selector: Selector string (e.g., 'all', 'id:d073d5', 'group:Kitchen')

        Returns:
            True if light matches the selector
        """
        if selector == 'all':
            return True

        if selector.startswith('id:'):
            return f"id:{light['id']}" == selector

        if selector.startswith('group:'):
            group_name = selector.replace('group:', '').lower()
            return (light.get('group') and
                   light['group']['name'].lower() == group_name)

        if selector.startswith('location:'):
            location_name = selector.replace('location:', '').lower()
            return (light.get('location') and
                   light['location']['name'].lower() == location_name)

        return False

    @staticmethod
    def find_matching_lights(lights: List[Dict], selector: str) -> List[Dict]:
        """
        Find all lights matching a selector.

        Args:
            lights: List of light objects from LIFX API
            selector: Selector string

        Returns:
            List of matching lights
        """
        return [light for light in lights
                if SceneMatcher.matches_selector(light, selector)]

    @staticmethod
    def check_power_match(light: Dict, expected_state: Dict) -> bool:
        """
        Check if light power state matches expected.

        Args:
            light: Light object
            expected_state: Expected state dict

        Returns:
            True if power matches or no power constraint
        """
        if 'power' not in expected_state:
            return True  # No power constraint
        return light['power'] == expected_state['power']

    @staticmethod
    def check_brightness_match(light: Dict, expected_state: Dict) -> bool:
        """
        Check if light brightness matches expected (within tolerance).

        Args:
            light: Light object
            expected_state: Expected state dict

        Returns:
            True if brightness matches within tolerance
        """
        if 'brightness' not in expected_state:
            return True  # No brightness constraint

        expected = expected_state['brightness']
        actual = light['brightness']
        return abs(actual - expected) <= BRIGHTNESS_TOLERANCE

    @staticmethod
    def check_hue_match(expected_hue: float, actual_hue: float) -> bool:
        """
        Check if hue matches (handles 360-degree wraparound).

        Args:
            expected_hue: Expected hue value (0-360)
            actual_hue: Actual hue value (0-360)

        Returns:
            True if hue matches within tolerance
        """
        hue_diff = abs(actual_hue - expected_hue)
        # Handle wraparound: 359° and 1° should be close
        return (hue_diff <= HUE_TOLERANCE_DEGREES or
                hue_diff >= HUE_WRAPAROUND_THRESHOLD)

    @staticmethod
    def check_saturation_match(expected_sat: float, actual_sat: float) -> bool:
        """
        Check if saturation matches (within tolerance).

        Args:
            expected_sat: Expected saturation value (0-1)
            actual_sat: Actual saturation value (0-1)

        Returns:
            True if saturation matches within tolerance
        """
        return abs(actual_sat - expected_sat) <= SATURATION_TOLERANCE

    @staticmethod
    def check_kelvin_match(expected_kelvin: int, actual_kelvin: int) -> bool:
        """
        Check if color temperature matches (within tolerance).

        Args:
            expected_kelvin: Expected color temperature (1500-9000K)
            actual_kelvin: Actual color temperature (1500-9000K)

        Returns:
            True if kelvin matches within tolerance
        """
        return abs(actual_kelvin - expected_kelvin) <= KELVIN_TOLERANCE

    @staticmethod
    def check_color_match(light: Dict, expected_state: Dict) -> bool:
        """
        Check if light color matches expected.

        Args:
            light: Light object
            expected_state: Expected state dict

        Returns:
            True if color matches or no color constraint
        """
        if 'color' not in expected_state or 'color' not in light:
            return True  # No color constraint or data

        expected_color = expected_state['color']
        actual_color = light['color']

        # Check hue if present
        if 'hue' in expected_color and 'hue' in actual_color:
            if not SceneMatcher.check_hue_match(
                expected_color['hue'], actual_color['hue']
            ):
                return False

        # Check saturation if present
        if 'saturation' in expected_color and 'saturation' in actual_color:
            if not SceneMatcher.check_saturation_match(
                expected_color['saturation'], actual_color['saturation']
            ):
                return False

        # Check kelvin (color temperature) if present
        if 'kelvin' in expected_color and 'kelvin' in actual_color:
            if not SceneMatcher.check_kelvin_match(
                expected_color['kelvin'], actual_color['kelvin']
            ):
                return False

        return True

    @staticmethod
    def light_matches_state(light: Dict, expected_state: Dict) -> bool:
        """
        Check if a light matches all expected state parameters.

        Args:
            light: Light object
            expected_state: Expected state dict

        Returns:
            True if all state parameters match
        """
        return (SceneMatcher.check_power_match(light, expected_state) and
                SceneMatcher.check_brightness_match(light, expected_state) and
                SceneMatcher.check_color_match(light, expected_state))

    @staticmethod
    def check_scene_status(
        scene: Dict[str, Any],
        lights: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if a scene is currently active based on light states.

        Args:
            scene: Scene object from LIFX API
            lights: List of light objects from LIFX API

        Returns:
            Dict with keys:
            - active: bool - Is the scene active?
            - matched_states: int - Number of matching states
            - total_states: int - Total states in scene
            - match_percentage: float - Percentage of matched states
            - reason: Optional[str] - Reason if not active
        """
        # Validate scene has states
        if 'states' not in scene:
            return {
                "active": False,
                "matched_states": 0,
                "total_states": 0,
                "match_percentage": 0.0,
                "reason": "No scene states defined"
            }

        scene_states = scene['states']
        total_states = len(scene_states)

        if total_states == 0:
            return {
                "active": False,
                "matched_states": 0,
                "total_states": 0,
                "match_percentage": 0.0,
                "reason": "Scene has no lights"
            }

        matched_count = 0

        # Check each scene state
        for scene_state in scene_states:
            selector = scene_state.get('selector')
            if not selector:
                continue

            # Find lights matching this selector
            matching_lights = SceneMatcher.find_matching_lights(lights, selector)

            # Check if any matching light has the expected state
            for light in matching_lights:
                if SceneMatcher.light_matches_state(light, scene_state):
                    matched_count += 1
                    break  # Found at least one matching light

        # Calculate match percentage
        match_percentage = (matched_count / total_states) * 100
        is_active = (matched_count / total_states) >= SCENE_MATCH_THRESHOLD

        return {
            "active": is_active,
            "matched_states": matched_count,
            "total_states": total_states,
            "match_percentage": round(match_percentage, 1)
        }
