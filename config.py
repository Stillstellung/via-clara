"""
Configuration management system for LIFX Controller.
Handles persistent storage, validation, and secure credential management.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from constants import DEFAULT_CLAUDE_MODEL


class ConfigError(Exception):
    """Configuration-related errors"""
    pass


class AppConfig:
    """Singleton configuration manager with hot-reloading capability"""

    _instance = None
    CONFIG_FILE = "config.json"

    # Default configuration
    DEFAULTS = {
        "lifx_token": "",
        "claude_api_key": "",
        "claude_model": DEFAULT_CLAUDE_MODEL,
        "system_prompt": ""  # Empty string means use default
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from file or create with defaults"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    file_config = json.load(f)
                    # Merge with defaults to handle missing keys
                    self._config = {**self.DEFAULTS, **file_config}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Error loading config file: {e}")
                self._config = self.DEFAULTS.copy()
        else:
            self._config = self.DEFAULTS.copy()
            self._save_config()

    def _save_config(self) -> None:
        """Persist configuration to file with secure permissions"""
        self._config['last_modified'] = datetime.utcnow().isoformat()
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)
            # Set secure permissions (owner read/write only)
            os.chmod(self.CONFIG_FILE, 0o600)
        except IOError as e:
            raise ConfigError(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values and persist"""
        self._config.update(updates)
        self._save_config()

    def validate_lifx_token(self, token: str) -> bool:
        """
        Validate LIFX token format and connectivity.

        Args:
            token: LIFX API token to validate

        Returns:
            True if token is valid and can connect to LIFX API
        """
        if not token or len(token) < 64:
            return False

        # Test token with actual API call
        try:
            response = requests.get(
                "https://api.lifx.com/v1/lights/all",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            return response.status_code != 401
        except Exception:
            # If we can't connect, assume token might be valid
            # (could be network issue, not token issue)
            return len(token) == 64

    def validate_claude_key(self, key: str) -> bool:
        """
        Validate Claude API key format.

        Args:
            key: Claude API key to validate

        Returns:
            True if key format is valid
        """
        return key.startswith("sk-ant-") and len(key) > 20

    def is_configured(self) -> bool:
        """Check if essential configuration is present"""
        return bool(self._config.get('lifx_token') and
                   self._config.get('claude_api_key'))

    def get_masked_config(self) -> Dict[str, Any]:
        """
        Get configuration with masked secrets for UI display.

        Returns:
            Configuration dict with masked API keys/tokens
        """
        return {
            "lifx_token": self._mask_secret(self._config.get('lifx_token', '')),
            "claude_api_key": self._mask_secret(self._config.get('claude_api_key', '')),
            "claude_model": self._config.get('claude_model', ''),
            "system_prompt": self._config.get('system_prompt', ''),
            "is_configured": self.is_configured()
        }

    @staticmethod
    def _mask_secret(secret: str) -> str:
        """
        Mask API key for display (show first 8 and last 4 chars).

        Args:
            secret: API key or token to mask

        Returns:
            Masked string for display
        """
        if not secret:
            return ''
        if len(secret) <= 12:
            return '***'
        return f"{secret[:8]}...{secret[-4:]}"


# Global instance
config = AppConfig()
