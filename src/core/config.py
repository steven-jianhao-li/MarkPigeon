"""
MarkPigeon Configuration Module

Manages user configuration for GitHub integration and app settings.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    # Use user's home directory
    config_dir = Path.home() / ".markpigeon"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.json"


def get_themes_dir() -> Path:
    """Get the user themes directory path.

    Creates the directory if it doesn't exist.
    Returns ~/.markpigeon/themes/
    """
    themes_dir = get_config_dir() / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)
    return themes_dir


@dataclass
class AppConfig:
    """Application configuration."""

    # GitHub settings
    github_token: str = ""
    github_repo_name: str = "markpigeon-shelf"
    github_username: str = ""

    # Privacy settings
    privacy_warning_enabled: bool = True

    # UI settings
    last_output_dir: str = ""
    last_theme: str = ""
    language: str = "en"

    # Internal
    has_starred_markpigeon: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from file."""
        config_file = get_config_file()

        if not config_file.exists():
            logger.info("No config file found, using defaults")
            return cls()

        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            # Filter to only known fields
            known_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data.items() if k in known_fields}
            return cls(**filtered_data)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return cls()

    def save(self) -> bool:
        """Save configuration to file."""
        config_file = get_config_file()

        try:
            config_file.write_text(
                json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info(f"Config saved to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def update(self, **kwargs) -> None:
        """Update configuration fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def save_config() -> bool:
    """Save the global configuration."""
    return get_config().save()
