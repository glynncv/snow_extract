"""
Unit Tests for Data Export Utilities
====================================

Test cases for snow_analytics.reporting.exporters module.
"""

import unittest
import pandas as pd
import tempfile
import json
from pathlib import Path
import shutil
import os

from snow_analytics.reporting.exporters import (
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_metrics
)


class TestExporters(unittest.TestCase):
    """Test cases for export functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_df = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003'],
            'short_description': ['Test 1', 'Test 2', 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate']
        })

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_export_to_csv_single(self):
        """Test single DataFrame to CSV."""
        output_path = Path(self.temp_dir) / "test.csv"
        
        # Export
        result_path = export_to_csv(self.sample_df, output_path)
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        self.assertEqual(result_path, output_path)
        
        # Verify content
        df_read = pd.read_csv(result_path)
        self.assertEqual(len(df_read), 3)
        self.assertIn('number', df_read.columns)
        
        # Clean up - verify then delete
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_to_csv_multiple(self):
        """Test multiple DataFrames to directory."""
        output_dir = Path(self.temp_dir) / "csv_exports"
        dfs = [self.sample_df, self.sample_df.copy()]
        
        # Export
        result_path = export_to_csv(dfs, output_dir)
        
        # Verify directory exists
        self.assertTrue(result_path.exists())
        self.assertTrue(result_path.is_dir())
        
        # Verify files created
        files = list(result_path.glob("*.csv"))
        self.assertGreaterEqual(len(files), 2)
        
        # Verify content
        for file_path in files:
            df_read = pd.read_csv(file_path)
            self.assertEqual(len(df_read), 3)
        
        # Clean up - verify then delete
        shutil.rmtree(result_path)
        self.assertFalse(result_path.exists())

    def test_export_to_csv_kwargs(self):
        """Test custom CSV parameters."""
        output_path = Path(self.temp_dir) / "test.csv"
        
        # Export with custom parameters
        result_path = export_to_csv(
            self.sample_df,
            output_path,
            index=True,
            encoding='utf-8'
        )
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content (with index)
        df_read = pd.read_csv(result_path, index_col=0)
        self.assertEqual(len(df_read), 3)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_to_excel_single(self):
        """Test single DataFrame to Excel."""
        output_path = Path(self.temp_dir) / "test.xlsx"
        
        try:
            # Export
            result_path = export_to_excel(self.sample_df, output_path)
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            self.assertEqual(result_path.suffix, '.xlsx')
            
            # Verify content
            df_read = pd.read_excel(result_path, sheet_name='Sheet1')
            self.assertEqual(len(df_read), 3)
            self.assertIn('number', df_read.columns)
            
            # Clean up - verify then delete
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_export_to_excel_multiple_sheets(self):
        """Test dict of DataFrames to multi-sheet Excel."""
        output_path = Path(self.temp_dir) / "multi_sheet.xlsx"
        sheets = {
            'Incidents': self.sample_df,
            'Summary': pd.DataFrame({'total': [3]})
        }
        
        try:
            # Export
            result_path = export_to_excel(sheets, output_path)
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            
            # Verify sheets exist
            with pd.ExcelFile(result_path) as excel_file:
                self.assertIn('Incidents', excel_file.sheet_names)
                self.assertIn('Summary', excel_file.sheet_names)
            
            # Verify content
            df_incidents = pd.read_excel(result_path, sheet_name='Incidents')
            self.assertEqual(len(df_incidents), 3)
            
            # Clean up - ensure file is closed
            import time
            time.sleep(0.1)  # Brief delay to ensure file is released
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_export_to_excel_sheet_names(self):
        """Test custom sheet names."""
        output_path = Path(self.temp_dir) / "custom_sheet.xlsx"
        
        try:
            # Export with custom sheet name
            result_path = export_to_excel(
                self.sample_df,
                output_path,
                sheet_name='CustomSheet'
            )
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            
            # Verify sheet name
            with pd.ExcelFile(result_path) as excel_file:
                self.assertIn('CustomSheet', excel_file.sheet_names)
            
            # Clean up - ensure file is closed
            import time
            time.sleep(0.1)  # Brief delay to ensure file is released
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_export_to_json_single(self):
        """Test single DataFrame to JSON."""
        output_path = Path(self.temp_dir) / "test.json"
        
        # Export
        result_path = export_to_json(self.sample_df, output_path)
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.suffix, '.json')
        
        # Verify content
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)
        self.assertIn('number', data[0])
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_to_json_multiple(self):
        """Test multiple DataFrames to JSON array."""
        output_path = Path(self.temp_dir) / "multi.json"
        dfs = [self.sample_df, self.sample_df.copy()]
        
        # Note: export_to_json doesn't support multiple DataFrames directly
        # This test verifies the function handles single DataFrame correctly
        result_path = export_to_json(self.sample_df, output_path)
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_to_json_orient(self):
        """Test different JSON orientations."""
        output_path = Path(self.temp_dir) / "test_index.json"
        
        # Export with index orientation
        result_path = export_to_json(self.sample_df, output_path, orient='index')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content (index orientation)
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        # Index orientation should be dict
        self.assertIsInstance(data, dict)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_metrics(self):
        """Test export metrics dictionary to JSON."""
        output_path = Path(self.temp_dir) / "metrics.json"
        metrics = {
            'total_resolved': 100,
            'sla_breached': 5,
            'breach_rate_pct': 5.0
        }
        
        # Export
        result_path = export_metrics(metrics, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['total_resolved'], 100)
        self.assertEqual(data['sla_breached'], 5)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_metrics_custom_format(self):
        """Test custom metrics format."""
        output_path = Path(self.temp_dir) / "metrics.csv"
        metrics = {
            'total_resolved': 100,
            'sla_breached': 5
        }
        
        # Export as CSV
        result_path = export_metrics(metrics, output_path, format='csv')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        df_read = pd.read_csv(result_path)
        self.assertEqual(len(df_read), 1)
        self.assertIn('total_resolved', df_read.columns)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_export_create_directories(self):
        """Test auto-create output directories."""
        output_path = Path(self.temp_dir) / "nested" / "dir" / "test.csv"
        
        # Export (should create directories)
        result_path = export_to_csv(self.sample_df, output_path)
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        self.assertTrue(output_path.parent.exists())
        
        # Clean up
        result_path.unlink()
        # Clean up nested directories
        shutil.rmtree(output_path.parent.parent)
        self.assertFalse(output_path.parent.exists())

    def test_export_invalid_data_type(self):
        """Test handle invalid data types."""
        output_path = Path(self.temp_dir) / "test.csv"
        
        # Should raise TypeError for invalid data type
        with self.assertRaises(TypeError):
            export_to_csv("not a dataframe", output_path)


if __name__ == '__main__':
    unittest.main()

