"""
Unit Tests for Data Loaders
===========================

Test cases for snow_analytics.core.loaders module.
"""

import unittest
import pandas as pd
from pathlib import Path
import tempfile
import os

from snow_analytics.core.loaders import (
    load_incidents,
    load_from_csv,
    generate_sample_data,
    _normalize_api_columns
)


class TestLoaders(unittest.TestCase):
    """Test cases for data loading functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_sample_data(self):
        """Test sample data generation."""
        df = generate_sample_data(num_records=10, template='network')

        self.assertEqual(len(df), 10)
        self.assertIn('number', df.columns)
        self.assertIn('short_description', df.columns)
        self.assertIn('priority', df.columns)
        self.assertIn('state', df.columns)

    def test_generate_sample_data_with_resolved(self):
        """Test sample data includes resolved incidents."""
        df = generate_sample_data(num_records=50, include_resolved=True)

        self.assertTrue(len(df) > 0)
        # Should have some resolved incidents
        resolved_count = df['resolved_at'].notna().sum()
        self.assertTrue(resolved_count > 0)

    def test_load_from_csv(self):
        """Test loading from CSV file."""
        # Create sample CSV
        sample_data = {
            'number': ['INC001', 'INC002'],
            'short_description': ['Test 1', 'Test 2'],
            'priority': ['1 - Critical', '2 - High'],
            'state': ['New', 'Resolved']
        }
        df_sample = pd.DataFrame(sample_data)

        csv_path = Path(self.temp_dir) / 'test_incidents.csv'
        df_sample.to_csv(csv_path, index=False)

        # Load CSV
        df_loaded = load_from_csv(csv_path)

        self.assertEqual(len(df_loaded), 2)
        self.assertListEqual(list(df_loaded['number']), ['INC001', 'INC002'])

    def test_load_from_csv_file_not_found(self):
        """Test loading from non-existent CSV raises error."""
        with self.assertRaises(FileNotFoundError):
            load_from_csv('non_existent_file.csv')

    def test_load_incidents_sample(self):
        """Test load_incidents with sample source."""
        df = load_incidents('sample', num_records=20, validate=False)

        self.assertEqual(len(df), 20)
        self.assertIsInstance(df, pd.DataFrame)

    def test_load_incidents_csv(self):
        """Test load_incidents with CSV source."""
        # Create sample CSV
        sample_data = {
            'number': ['INC001'],
            'short_description': ['Test'],
            'priority': ['1 - Critical'],
            'state': ['New']
        }
        df_sample = pd.DataFrame(sample_data)

        csv_path = Path(self.temp_dir) / 'test.csv'
        df_sample.to_csv(csv_path, index=False)

        # Load via load_incidents
        df = load_incidents('csv', file_path=str(csv_path), validate=False)

        self.assertEqual(len(df), 1)
        self.assertEqual(df['number'].iloc[0], 'INC001')

    def test_load_incidents_invalid_source(self):
        """Test load_incidents with invalid source raises error."""
        with self.assertRaises(ValueError):
            load_incidents('invalid_source')

    def test_normalize_api_columns(self):
        """Test API column normalization."""
        df_api = pd.DataFrame({
            'state': ['New', 'Resolved'],
            'opened_at': ['2025-01-01', '2025-01-02'],
            'resolved_at': ['', '2025-01-03']
        })

        df_normalized = _normalize_api_columns(df_api)

        self.assertIn('incident_state', df_normalized.columns)
        self.assertIn('opened_at', df_normalized.columns)

    def test_sample_data_structure(self):
        """Test that sample data has expected structure."""
        df = generate_sample_data(num_records=5)

        # Check required columns exist
        required_columns = [
            'number', 'short_description', 'description', 'priority',
            'state', 'assignment_group', 'opened_at'
        ]

        for col in required_columns:
            self.assertIn(col, df.columns, f"Missing required column: {col}")

        # Check data types
        self.assertTrue(all(df['number'].str.startswith('INC')))
        self.assertTrue(all(df['reassignment_count'] >= 0))


if __name__ == '__main__':
    unittest.main()
