"""
Configuration Management
=======================

Centralized configuration management for ServiceNow Analytics.
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager with support for JSON/YAML files and environment variables.

    Examples:
        >>> config = Config()
        >>> instance_url = config.get('servicenow.instance_url')

        >>> # With custom config file
        >>> config = Config(config_path='config/custom_config.yaml')
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.config_path = self._resolve_config_path(config_path)
        self.config = self._load_config()

    def _resolve_config_path(self, config_path: Optional[str]) -> Optional[Path]:
        """Resolve configuration file path."""
        if config_path:
            return Path(config_path)

        # Try default locations
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent

        default_paths = [
            project_root / "config" / "default_config.yaml",
            project_root / "config" / "config.yaml",
            project_root / "config" / "config.json",
            project_root / "config" / "config_template.json",
        ]

        for path in default_paths:
            if path.exists():
                return path

        logger.debug("No config file found, using defaults and environment variables")
        return None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_path is None:
            logger.info("Using default configuration")
            return self._get_default_config()

        try:
            logger.info(f"Loading configuration from: {self.config_path}")

            with open(self.config_path, 'r') as f:
                if self.config_path.suffix in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            logger.info("Configuration loaded successfully")
            return config

        except Exception as e:
            logger.warning(f"Error loading config file: {e}. Using defaults.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "servicenow": {
                "instance_url": os.getenv("SNOW_INSTANCE_URL", ""),
                "username": os.getenv("SNOW_USERNAME", ""),
                "password": os.getenv("SNOW_PASSWORD", ""),
                "timeout": 30
            },
            "extraction": {
                "batch_size": 1000,
                "output_format": "csv",
                "include_attachments": False,
                "query_filter": "assignment_groupLIKEnetwork^state!=6"
            },
            "sla": {
                "rules": {
                    "1 - Critical": 4,
                    "2 - High": 24,
                    "3 - Moderate": 72,
                    "4 - Low": 120
                }
            },
            "categorization": {
                "rules": {
                    "WiFi/Wireless": ["wifi", "wireless", "access point", "wap", "ssid"],
                    "VPN/Remote Access": ["vpn", "remote", "zscaler", "remote access"],
                    "Network Printing": ["printer", "print", "printing"],
                    "Server/Performance": ["server", "performance", "slow", "clearcase"],
                    "DNS/Resolution": ["dns", "resolution", "name resolution"],
                    "Firewall/Security": ["firewall", "blocked", "security"],
                    "Connectivity": ["connectivity", "connection", "network", "ping"],
                    "Hardware": ["hardware", "device", "router", "switch"]
                }
            },
            "quality": {
                "min_description_length": 20,
                "max_reassignment_threshold": 3,
                "on_hold_threshold_hours": 72
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "paths": {
                "output_dir": "output",
                "logs_dir": "logs",
                "data_dir": "data"
            },
            "redaction": {
                "enabled": True,
                "hash_salt": "snow_extract_2025",
                "redaction_char": "X"
            }
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Configuration key path (e.g., 'servicenow.instance_url')
            default: Default value if key not found

        Returns:
            Configuration value

        Examples:
            >>> config.get('servicenow.instance_url')
            'https://instance.service-now.com'

            >>> config.get('sla.rules.1 - Critical', default=4)
            4
        """
        keys = key_path.split('.')
        value = self.config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            # Try environment variable as fallback
            env_var = '_'.join(keys).upper()
            env_value = os.getenv(env_var)
            if env_value is not None:
                return env_value

            logger.debug(f"Configuration key not found: {key_path}, using default: {default}")
            return default

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key_path: Configuration key path
            value: Value to set

        Examples:
            >>> config.set('extraction.batch_size', 500)
        """
        keys = key_path.split('.')
        config_section = self.config

        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in config_section:
                config_section[key] = {}
            config_section = config_section[key]

        # Set value
        config_section[keys[-1]] = value
        logger.debug(f"Set configuration: {key_path} = {value}")

    def save(self, output_path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            output_path: Output file path (uses config_path if not specified)
        """
        if output_path is None:
            output_path = self.config_path

        if output_path is None:
            raise ValueError("No output path specified and no config file loaded")

        output_path = Path(output_path)

        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                if output_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self.config, f, indent=2)

            logger.info(f"Saved configuration to: {output_path}")

        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid
        """
        required_keys = [
            'extraction.batch_size',
            'logging.level'
        ]

        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"Missing required configuration: {key}")
                return False

        return True

    def get_all(self) -> Dict[str, Any]:
        """
        Get entire configuration dictionary.

        Returns:
            Complete configuration dict
        """
        return self.config.copy()
