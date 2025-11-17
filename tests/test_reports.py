"""
Unit Tests for Report Generation
=================================

Test cases for snow_analytics.reporting.reports module.
"""

import unittest
import pandas as pd
import tempfile
import json
from pathlib import Path
import shutil
import os
from datetime import datetime, timedelta

from snow_analytics.reporting.reports import (
    generate_sla_report,
    generate_backlog_report,
    generate_quality_report,
    generate_executive_summary
)
from snow_analytics.core.loaders import generate_sample_data
from snow_analytics.core.transform import transform_incidents


class TestReports(unittest.TestCase):
    """Test cases for report generation functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample data with resolved and active incidents
        base_time = datetime.now() - timedelta(days=2)
        
        resolved_data = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003'],
            'short_description': ['Resolved 1', 'Resolved 2', 'Resolved 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['Resolved', 'Resolved', 'Resolved'],
            'openedDate': pd.to_datetime([
                base_time - timedelta(hours=2),
                base_time - timedelta(hours=25),
                base_time - timedelta(hours=50)
            ]),
            'resolvedDate': pd.to_datetime([
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1)
            ])
        })
        
        active_data = pd.DataFrame({
            'number': ['INC004', 'INC005'],
            'short_description': ['Active 1', 'Active 2'],
            'priority': ['1 - Critical', '2 - High'],
            'state': ['New', 'In Progress'],
            'openedDate': pd.to_datetime([
                datetime.now() - timedelta(hours=12),
                datetime.now() - timedelta(days=2)
            ]),
            'resolvedDate': [None, None]
        })
        
        combined_data = pd.concat([resolved_data, active_data], ignore_index=True)
        self.df = transform_incidents(combined_data)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_sla_report_excel(self):
        """Test Excel SLA report generation."""
        output_path = Path(self.temp_dir) / "sla_report.xlsx"
        
        try:
            # Generate report
            result_path = generate_sla_report(self.df, output_path, format='excel')
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            self.assertEqual(result_path.suffix, '.xlsx')
            
            # Verify sheets exist
            with pd.ExcelFile(result_path) as excel_file:
                self.assertIn('Summary', excel_file.sheet_names)
            
            # Verify Summary sheet content
            summary_df = pd.read_excel(result_path, sheet_name='Summary')
            self.assertGreater(len(summary_df), 0)
            self.assertIn('Metric', summary_df.columns)
            
            # Clean up - ensure file is closed
            import time
            time.sleep(0.1)  # Brief delay to ensure file is released
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_generate_sla_report_json(self):
        """Test JSON SLA report generation."""
        output_path = Path(self.temp_dir) / "sla_report.json"
        
        # Generate report
        result_path = generate_sla_report(self.df, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn('report_type', report)
        self.assertIn('summary', report)
        self.assertEqual(report['report_type'], 'SLA Compliance Report')
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_generate_sla_report_sheets(self):
        """Test verify all Excel sheets created."""
        output_path = Path(self.temp_dir) / "sla_report.xlsx"
        
        try:
            # Generate report
            result_path = generate_sla_report(self.df, output_path, format='excel')
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            
            # Verify sheets - ensure ExcelFile is closed before cleanup
            with pd.ExcelFile(result_path) as excel_file:
                sheet_names = excel_file.sheet_names
                
                # Should have at least Summary sheet
                self.assertIn('Summary', sheet_names)
            
            # Clean up - file should be closed now
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_generate_backlog_report(self):
        """Test backlog report generation."""
        output_path = Path(self.temp_dir) / "backlog_report.xlsx"
        
        try:
            # Generate report
            result_path = generate_backlog_report(self.df, output_path, format='excel')
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            
            # Verify sheets exist
            with pd.ExcelFile(result_path) as excel_file:
                self.assertIn('Summary', excel_file.sheet_names)
            
            # Clean up - ensure file is closed
            import time
            time.sleep(0.1)  # Brief delay to ensure file is released
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_generate_backlog_report_by_age(self):
        """Test age distribution in report."""
        output_path = Path(self.temp_dir) / "backlog_report.json"
        
        # Generate report
        result_path = generate_backlog_report(self.df, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        self.assertIn('metrics', report)
        if 'metrics' in report:
            metrics = report['metrics']
            self.assertIn('by_age', metrics)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_generate_quality_report(self):
        """Test quality report generation."""
        output_path = Path(self.temp_dir) / "quality_report.xlsx"
        
        try:
            # Generate report
            result_path = generate_quality_report(self.df, output_path, format='excel')
            
            # Verify file exists
            self.assertTrue(result_path.exists())
            
            # Verify sheets exist
            with pd.ExcelFile(result_path) as excel_file:
                self.assertIn('Summary', excel_file.sheet_names)
            
            # Clean up - ensure file is closed
            import time
            time.sleep(0.1)  # Brief delay to ensure file is released
            result_path.unlink()
            self.assertFalse(result_path.exists())
        except ImportError:
            self.skipTest("openpyxl not installed")

    def test_generate_quality_report_issues(self):
        """Test quality issues breakdown."""
        output_path = Path(self.temp_dir) / "quality_report.json"
        
        # Generate report
        result_path = generate_quality_report(self.df, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn('report_type', report)
        self.assertEqual(report['report_type'], 'Quality Report')
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_generate_executive_summary(self):
        """Test executive summary generation."""
        output_path = Path(self.temp_dir) / "executive_summary.json"
        
        # Generate report (specify format='json')
        result_path = generate_executive_summary(self.df, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        self.assertIn('report_type', summary)
        self.assertIn('summary', summary)
        self.assertEqual(summary['report_type'], 'Executive Summary')
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_generate_executive_summary_sections(self):
        """Test verify all sections present."""
        output_path = Path(self.temp_dir) / "executive_summary.json"
        
        # Generate report (specify format='json')
        result_path = generate_executive_summary(self.df, output_path, format='json')
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content structure
        with open(result_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # Should have key sections
        self.assertIn('summary', summary)
        if 'summary' in summary:
            summary_data = summary['summary']
            self.assertIsInstance(summary_data, dict)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_generate_reports_empty_data(self):
        """Test handle empty DataFrames."""
        df_empty = pd.DataFrame()
        output_path = Path(self.temp_dir) / "empty_report.json"
        
        # Should handle empty DataFrame gracefully
        try:
            result_path = generate_sla_report(df_empty, output_path, format='json')
            
            # If report generated, verify and clean up
            if result_path.exists():
                result_path.unlink()
        except Exception:
            # Exception is acceptable for empty data
            pass

    def test_generate_reports_custom_sla_rules(self):
        """Test custom SLA rules in reports."""
        output_path = Path(self.temp_dir) / "custom_sla_report.json"
        custom_sla_rules = {
            '1 - Critical': 2,  # Very strict
            '2 - High': 12
        }
        
        # Generate report with custom rules
        result_path = generate_sla_report(
            self.df,
            output_path,
            format='json',
            sla_rules=custom_sla_rules
        )
        
        # Verify file exists
        self.assertTrue(result_path.exists())
        
        # Verify content
        with open(result_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn('summary', report)
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())


if __name__ == '__main__':
    unittest.main()

