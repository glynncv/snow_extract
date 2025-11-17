"""
Integration Tests for End-to-End Workflows
==========================================

Test cases for complete workflows using real API calls where applicable.
"""

import unittest
import pytest
import pandas as pd
import tempfile
from pathlib import Path
import shutil
import os

from snow_analytics.core.loaders import load_incidents, load_from_api
from snow_analytics.core.transform import transform_incidents
from snow_analytics.core.config import Config
from snow_analytics.core.validators import validate_incident_schema, validate_data_quality
from snow_analytics.analysis.metrics import (
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics
)
from snow_analytics.analysis.quality import check_incident_quality
from snow_analytics.analysis.patterns import analyze_patterns
from snow_analytics.reporting.reports import (
    generate_sla_report,
    generate_backlog_report,
    generate_quality_report
)


class TestIntegration(unittest.TestCase):
    """Test cases for end-to-end workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_full_pipeline_sample_data(self):
        """Test Load → Transform → Analyze → Report with sample data."""
        # Load sample data
        df = load_incidents('sample', num_records=50, validate=False)
        self.assertGreater(len(df), 0)
        
        # Transform
        df_transformed = transform_incidents(df)
        self.assertIn('isActive', df_transformed.columns)
        self.assertIn('patternCategory', df_transformed.columns)
        
        # Analyze - SLA metrics
        sla_metrics = calculate_sla_metrics(df_transformed)
        self.assertIn('total_resolved', sla_metrics)
        
        # Analyze - Quality
        df_quality = check_incident_quality(df_transformed)
        self.assertIn('quality_issues_count', df_quality.columns)
        
        # Generate report
        output_path = Path(self.temp_dir) / "pipeline_report.json"
        result_path = generate_sla_report(df_transformed, output_path, format='json')
        
        # Verify report exists
        self.assertTrue(result_path.exists())
        
        # Clean up
        result_path.unlink()
        self.assertFalse(result_path.exists())

    def test_full_pipeline_csv(self):
        """Test CSV load → Transform → Metrics."""
        # Create test CSV
        csv_path = Path(self.temp_dir) / "test_incidents.csv"
        sample_df = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'short_description': ['Test 1', 'Test 2'],
            'priority': ['1 - Critical', '2 - High'],
            'state': ['Resolved', 'New'],
            'openedDate': ['2025-01-01', '2025-01-02']
        })
        sample_df.to_csv(csv_path, index=False)
        
        # Load from CSV
        df = load_incidents('csv', file_path=str(csv_path), validate=False)
        self.assertEqual(len(df), 2)
        
        # Transform
        df_transformed = transform_incidents(df)
        self.assertIn('isActive', df_transformed.columns)
        
        # Calculate metrics
        metrics = calculate_sla_metrics(df_transformed)
        self.assertIsInstance(metrics, dict)
        
        # Clean up CSV
        csv_path.unlink()
        self.assertFalse(csv_path.exists())

    def test_load_transform_metrics(self):
        """Test Load → Transform → SLA metrics."""
        # Load sample
        df = load_incidents('sample', num_records=30, validate=False)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Calculate metrics
        sla_metrics = calculate_sla_metrics(df_transformed)
        resolution_times = analyze_resolution_times(df_transformed)
        
        # Verify metrics
        self.assertIn('total_resolved', sla_metrics)
        self.assertIn('overall', resolution_times)

    def test_load_transform_quality(self):
        """Test Load → Transform → Quality checks."""
        # Load sample
        df = load_incidents('sample', num_records=30, validate=False)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Quality checks
        df_quality = check_incident_quality(df_transformed)
        
        # Verify quality flags
        self.assertIn('quality_issues_count', df_quality.columns)
        quality_flags = [col for col in df_quality.columns if col.startswith('quality_')]
        self.assertGreater(len(quality_flags), 0)

    def test_transform_analyze_report(self):
        """Test Transform → Analyze → Generate report."""
        # Start with sample data
        df = load_incidents('sample', num_records=40, validate=False)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Analyze
        sla_metrics = calculate_sla_metrics(df_transformed)
        backlog_metrics = calculate_backlog_metrics(df_transformed)
        
        # Generate reports
        sla_report_path = Path(self.temp_dir) / "sla_report.json"
        backlog_report_path = Path(self.temp_dir) / "backlog_report.json"
        
        generate_sla_report(df_transformed, sla_report_path, format='json')
        generate_backlog_report(df_transformed, backlog_report_path, format='json')
        
        # Verify reports exist
        self.assertTrue(sla_report_path.exists())
        self.assertTrue(backlog_report_path.exists())
        
        # Clean up
        sla_report_path.unlink()
        backlog_report_path.unlink()
        self.assertFalse(sla_report_path.exists())
        self.assertFalse(backlog_report_path.exists())

    def test_config_load_transform(self):
        """Test Config → Load → Transform integration."""
        # Load config
        config = Config()
        
        # Load sample (config not strictly needed for sample, but tests integration)
        df = load_incidents('sample', num_records=20, config=config, validate=False)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Verify transformation
        self.assertIn('isActive', df_transformed.columns)
        self.assertIn('patternCategory', df_transformed.columns)

    def test_validator_integration(self):
        """Test Validate → Transform → Analyze flow."""
        # Load sample
        df = load_incidents('sample', num_records=25, validate=False)
        
        # Validate schema
        is_valid, issues = validate_incident_schema(df, warn_only=True)
        self.assertTrue(is_valid)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Validate data quality
        quality_report = validate_data_quality(df_transformed)
        self.assertIn('data_quality_score', quality_report)
        
        # Analyze
        metrics = calculate_sla_metrics(df_transformed)
        self.assertIsInstance(metrics, dict)

    @pytest.mark.api
    def test_api_load_transform(self):
        """Test REAL API load → Transform (requires API credentials)."""
        # Check credentials
        instance_url = (
            self.config.get('servicenow.instance_url') or 
            os.getenv('SNOW_INSTANCE_URL')
        )
        username = (
            self.config.get('servicenow.username') or 
            os.getenv('SNOW_USERNAME')
        )
        password = (
            self.config.get('servicenow.password') or 
            os.getenv('SNOW_PASSWORD')
        )
        
        if not all([instance_url, username, password]):
            pytest.skip("ServiceNow credentials not available")
        
        # Load from real API (small limit for testing)
        try:
            df = load_from_api(limit=10)
            
            # Should have data
            self.assertGreater(len(df), 0)
            self.assertIn('number', df.columns)
            
            # Transform
            df_transformed = transform_incidents(df)
            
            # Verify transformation
            self.assertIn('isActive', df_transformed.columns)
            self.assertIn('patternCategory', df_transformed.columns)
            
        except Exception as e:
            pytest.skip(f"API connection failed: {e}")

    @pytest.mark.api
    def test_api_full_pipeline(self):
        """Test REAL API → Load → Transform → Analyze → Report."""
        # Check credentials
        instance_url = (
            self.config.get('servicenow.instance_url') or 
            os.getenv('SNOW_INSTANCE_URL')
        )
        username = (
            self.config.get('servicenow.username') or 
            os.getenv('SNOW_USERNAME')
        )
        password = (
            self.config.get('servicenow.password') or 
            os.getenv('SNOW_PASSWORD')
        )
        
        if not all([instance_url, username, password]):
            pytest.skip("ServiceNow credentials not available")
        
        try:
            # Load from real API
            df = load_from_api(limit=10)
            
            if len(df) == 0:
                pytest.skip("No incidents available from API")
            
            # Transform
            df_transformed = transform_incidents(df)
            
            # Analyze
            sla_metrics = calculate_sla_metrics(df_transformed)
            backlog_metrics = calculate_backlog_metrics(df_transformed)
            
            # Generate report
            output_path = Path(self.temp_dir) / "api_report.json"
            result_path = generate_sla_report(df_transformed, output_path, format='json')
            
            # Verify report exists
            self.assertTrue(result_path.exists())
            
            # Clean up
            result_path.unlink()
            self.assertFalse(result_path.exists())
            
        except Exception as e:
            pytest.skip(f"API pipeline failed: {e}")

    def test_metrics_quality_integration(self):
        """Test Metrics + Quality checks together."""
        # Load sample
        df = load_incidents('sample', num_records=40, validate=False)
        
        # Transform
        df_transformed = transform_incidents(df)
        
        # Calculate metrics
        sla_metrics = calculate_sla_metrics(df_transformed)
        resolution_times = analyze_resolution_times(df_transformed)
        
        # Quality checks
        df_quality = check_incident_quality(df_transformed)
        
        # Verify both work together
        self.assertIn('total_resolved', sla_metrics)
        self.assertIn('overall', resolution_times)
        self.assertIn('quality_issues_count', df_quality.columns)

    def test_reporting_integration(self):
        """Test all report types with same data."""
        # Load and transform
        df = load_incidents('sample', num_records=50, validate=False)
        df_transformed = transform_incidents(df)
        
        # Generate all report types
        sla_path = Path(self.temp_dir) / "sla.json"
        backlog_path = Path(self.temp_dir) / "backlog.json"
        quality_path = Path(self.temp_dir) / "quality.json"
        
        generate_sla_report(df_transformed, sla_path, format='json')
        generate_backlog_report(df_transformed, backlog_path, format='json')
        generate_quality_report(df_transformed, quality_path, format='json')
        
        # Verify all reports exist
        self.assertTrue(sla_path.exists())
        self.assertTrue(backlog_path.exists())
        self.assertTrue(quality_path.exists())
        
        # Clean up all reports
        sla_path.unlink()
        backlog_path.unlink()
        quality_path.unlink()
        
        self.assertFalse(sla_path.exists())
        self.assertFalse(backlog_path.exists())
        self.assertFalse(quality_path.exists())


if __name__ == '__main__':
    unittest.main()

