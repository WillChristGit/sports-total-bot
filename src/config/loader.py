"""
Configuration loader with environment variable support
Loads settings from YAML and overrides with environment variables
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager with environment variable support
    Environment variables override YAML config values
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            self._config = {}
            return

        try:
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            self._config = {}

        # Apply environment variable overrides
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Override config values with environment variables"""
        # API keys from environment
        if os.getenv("ODDS_API_KEY"):
            self._set_nested("api_keys.the_odds_api", os.getenv("ODDS_API_KEY"))

        if os.getenv("NBA_API_KEY"):
            self._set_nested("api_keys.api_nba", os.getenv("NBA_API_KEY"))

        if os.getenv("RAPID_API_KEY"):
            self._set_nested("api_keys.rapid_api", os.getenv("RAPID_API_KEY"))

        # Discord webhook
        if os.getenv("DISCORD_WEBHOOK"):
            self._set_nested("output.discord_webhook", os.getenv("DISCORD_WEBHOOK"))

        # Telegram config
        if os.getenv("TELEGRAM_TOKEN"):
            self._set_nested("output.telegram_token", os.getenv("TELEGRAM_TOKEN"))
        if os.getenv("TELEGRAM_CHAT_ID"):
            self._set_nested("output.telegram_chat_id", os.getenv("TELEGRAM_CHAT_ID"))

        # Analysis settings
        if os.getenv("MIN_EV_THRESHOLD"):
            self._set_nested("analysis.min_ev_threshold", float(os.getenv("MIN_EV_THRESHOLD")))
        if os.getenv("MIN_CONFIDENCE"):
            self._set_nested("analysis.min_confidence", float(os.getenv("MIN_CONFIDENCE")))

        # Database path
        if os.getenv("DATABASE_PATH"):
            self._set_nested("database.path", os.getenv("DATABASE_PATH"))

        # Log level
        if os.getenv("LOG_LEVEL"):
            self._set_nested("bot.log_level", os.getenv("LOG_LEVEL"))

    def _set_nested(self, path: str, value: Any):
        """Set a nested config value using dot notation"""
        keys = path.split('.')
        current = self._config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a config value using dot notation

        Examples:
            config.get("api_keys.the_odds_api")
            config.get("analysis.min_ev_threshold", 0.02)
        """
        keys = path.split('.')
        current = self._config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        return self.get(f"api_keys.{service}")

    def validate(self) -> bool:
        """Validate that required config values are set"""
        required_keys = [
            ("api_keys.the_odds_api", "The Odds API key"),
        ]

        missing = []
        for key_path, name in required_keys:
            value = self.get(key_path)
            if not value or value == "YOUR_API_KEY_HERE":
                missing.append(name)

        if missing:
            logger.error(f"Missing required config: {', '.join(missing)}")
            logger.info("Set them via environment variables or in config/config.yaml")
            return False

        return True

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access"""
        return self._config.get(key)

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator"""
        return key in self._config

    def to_dict(self) -> Dict[str, Any]:
        """Return the full config as dict"""
        return self._config.copy()


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load and return configuration"""
    return Config(config_path)
