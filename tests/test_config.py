"""
Unit Tests for Configuration Management
========================================

Test cases for snow_analytics.core.config module.
"""

import unittest
import tempfile
import os
import json
import yaml
from pathlib import Path
import shutil

from snow_analytics.core.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_config_path = self.temp_dir / "test_config.yaml"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_config_default_loading(self):
        """Test loading default config from config/default_config.yaml."""
        config = Config()
        
        # Should load without error
        self.assertIsNotNone(config.config)
        # Should have servicenow section
        self.assertIn('servicenow', config.config)

    def test_config_custom_path(self):
        """Test loading custom config file."""
        # Create test YAML config
        test_config = {
            'servicenow': {
                'instance_url': 'https://test.service-now.com',
                'username': 'test_user',
                'timeout': 60
            }
        }
        
        with open(self.temp_config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path=str(self.temp_config_path))
        
        self.assertEqual(
            config.get('servicenow.instance_url'),
            'https://test.service-now.com'
        )
        self.assertEqual(config.get('servicenow.timeout'), 60)

    def test_config_yaml_format(self):
        """Test YAML file loading."""
        test_config = {
            'sla': {
                'rules': {
                    '1 - Critical': 4
                }
            }
        }
        
        yaml_path = Path(self.temp_dir) / "test.yaml"
        with open(yaml_path, 'w') as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path=str(yaml_path))
        self.assertEqual(config.get('sla.rules.1 - Critical'), 4)

    def test_config_json_format(self):
        """Test JSON file loading."""
        test_config = {
            'sla': {
                'rules': {
                    '1 - Critical': 4
                }
            }
        }
        
        json_path = Path(self.temp_dir) / "test.json"
        with open(json_path, 'w') as f:
            json.dump(test_config, f)
        
        config = Config(config_path=str(json_path))
        self.assertEqual(config.get('sla.rules.1 - Critical'), 4)

    def test_config_env_fallback(self):
        """Test environment variable fallback."""
        # Set environment variables
        os.environ['SNOW_INSTANCE_URL'] = 'https://env-test.service-now.com'
        os.environ['SNOW_USERNAME'] = 'env_user'
        
        try:
            config = Config()
            # Should use env vars if config file doesn't have them
            instance_url = config.get('servicenow.instance_url')
            # May be from env or config, but should not be empty
            self.assertIsNotNone(instance_url)
        finally:
            # Clean up env vars
            os.environ.pop('SNOW_INSTANCE_URL', None)
            os.environ.pop('SNOW_USERNAME', None)

    def test_config_get_dot_notation(self):
        """Test dot notation access."""
        test_config = {
            'servicenow': {
                'instance_url': 'https://test.service-now.com',
                'timeout': 30
            },
            'sla': {
                'rules': {
                    '1 - Critical': 4
                }
            }
        }
        
        with open(self.temp_config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path=str(self.temp_config_path))
        
        self.assertEqual(
            config.get('servicenow.instance_url'),
            'https://test.service-now.com'
        )
        self.assertEqual(config.get('sla.rules.1 - Critical'), 4)

    def test_config_get_nested(self):
        """Test nested configuration access."""
        test_config = {
            'sla': {
                'rules': {
                    '1 - Critical': 4,
                    '2 - High': 24
                }
            }
        }
        
        with open(self.temp_config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path=str(self.temp_config_path))
        
        rules = config.get('sla.rules')
        self.assertIsInstance(rules, dict)
        self.assertEqual(rules['1 - Critical'], 4)

    def test_config_get_default_value(self):
        """Test default value handling."""
        config = Config()
        
        # Get non-existent key with default
        value = config.get('nonexistent.key', default='default_value')
        self.assertEqual(value, 'default_value')
        
        # Get non-existent key without default
        value = config.get('nonexistent.key')
        self.assertIsNone(value)

    def test_config_missing_file(self):
        """Test handling missing config file gracefully."""
        non_existent_path = Path(self.temp_dir) / "nonexistent.yaml"
        config = Config(config_path=str(non_existent_path))
        
        # Should not raise error, should use defaults
        self.assertIsNotNone(config.config)

    def test_config_invalid_format(self):
        """Test handling invalid config format."""
        invalid_path = Path(self.temp_dir) / "invalid.txt"
        with open(invalid_path, 'w') as f:
            f.write("This is not valid YAML or JSON")
        
        # Should handle gracefully and use defaults
        config = Config(config_path=str(invalid_path))
        self.assertIsNotNone(config.config)

    def test_config_get_sla_rules(self):
        """Test retrieving SLA rules."""
        config = Config()
        sla_rules = config.get('sla.rules')
        
        # Should have SLA rules
        if sla_rules:
            self.assertIsInstance(sla_rules, dict)
            # Should have priority levels
            self.assertIn('1 - Critical', sla_rules)

    def test_config_get_categorization_rules(self):
        """Test retrieving categorization rules."""
        config = Config()
        cat_rules = config.get('categorization.rules')
        
        # Should have categorization rules
        if cat_rules:
            self.assertIsInstance(cat_rules, dict)
            # Should have categories
            self.assertIn('WiFi/Wireless', cat_rules)


if __name__ == '__main__':
    unittest.main()

