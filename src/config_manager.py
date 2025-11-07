"""
Configuration Management for ServiceNow Extraction
=================================================

Handles loading and managing configuration settings for the ServiceNow extraction process.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for ServiceNow extraction"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to configuration file
        """
        if config_path is None:
            # Default to config directory in project root
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            config_path = project_root / "config" / "config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from: {self.config_path}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
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
        Get configuration value using dot notation
        
        Args:
            key_path: Configuration key path (e.g., 'servicenow.instance_url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            logger.warning(f"Configuration key not found: {key_path}")
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation
        
        Args:
            key_path: Configuration key path
            value: Value to set
        """
        keys = key_path.split('.')
        config_section = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config_section:
                config_section[key] = {}
            config_section = config_section[key]
        
        # Set the value
        config_section[keys[-1]] = value
        logger.info(f"Set configuration: {key_path} = {value}")
    
    def save(self) -> None:
        """Save configuration to file"""
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to: {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        required_keys = [
            'servicenow.instance_url',
            'extraction.batch_size',
            'logging.level'
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"Missing required configuration: {key}")
                return False
        
        return True

# Global configuration instance
config = Config()
