"""
Unit Tests for Data Transformations
===================================

Test cases for snow_analytics.core.transform module.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from snow_analytics.core.transform import (
    transform_incidents,
    normalize_columns,
    parse_dates,
    add_status_fields,
    add_categorization,
    calculate_durations,
    calculate_sla_breach
)


class TestTransform(unittest.TestCase):
    """Test cases for transformation functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample incident data
        base_time = datetime.now() - timedelta(days=1)

        self.sample_data = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003'],
            'short_description': [
                'WiFi connectivity issue',
                'VPN connection problem',
                'DNS resolution failure'
            ],
            'description': [
                'Users unable to connect to WiFi in building A',
                'Remote users cannot establish VPN connection',
                'DNS server not resolving external domains'
            ],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'incident_state': ['New', 'In Progress', 'Resolved'],
            'opened': [
                (base_time - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                (base_time - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'),
                (base_time - timedelta(hours=10)).strftime('%Y-%m-%d %H:%M:%S')
            ],
            'resolved': [
                '',
                '',
                (base_time - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
            ],
            'ci_type': ['Access Point', 'VPN Gateway', 'DNS Server'],
            'reassignment_count': [0, 1, 2]
        })

    def test_normalize_columns(self):
        """Test column normalization."""
        df = normalize_columns(self.sample_data.copy())

        self.assertIn('state', df.columns)
        self.assertIn('openedDate', df.columns)
        self.assertIn('resolvedDate', df.columns)

    def test_parse_dates(self):
        """Test date parsing."""
        df = normalize_columns(self.sample_data.copy())
        df = parse_dates(df)

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['openedDate']))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['resolvedDate']))

    def test_add_status_fields(self):
        """Test status field addition."""
        df = normalize_columns(self.sample_data.copy())
        df = add_status_fields(df)

        self.assertIn('isActive', df.columns)
        self.assertIn('isResolved', df.columns)
        self.assertIn('isHighImpact', df.columns)

        # Test specific values
        self.assertTrue(df.loc[0, 'isActive'])  # New incident
        self.assertFalse(df.loc[2, 'isActive'])  # Resolved incident
        self.assertTrue(df.loc[0, 'isHighImpact'])  # Critical priority

    def test_add_categorization(self):
        """Test incident categorization."""
        df = add_categorization(self.sample_data.copy())

        self.assertIn('patternCategory', df.columns)

        # Check specific categorizations
        self.assertEqual(df.loc[0, 'patternCategory'], 'WiFi/Wireless')
        self.assertEqual(df.loc[1, 'patternCategory'], 'VPN/Remote Access')
        self.assertEqual(df.loc[2, 'patternCategory'], 'DNS/Resolution')

    def test_calculate_durations(self):
        """Test duration calculations."""
        df = normalize_columns(self.sample_data.copy())
        df = parse_dates(df)
        df = add_status_fields(df)
        df = calculate_durations(df)

        self.assertIn('resolutionTimeHrs', df.columns)
        self.assertIn('ageHrs', df.columns)

        # Resolved incident should have resolution time
        self.assertFalse(pd.isna(df.loc[2, 'resolutionTimeHrs']))

        # Active incidents should have age
        self.assertFalse(pd.isna(df.loc[0, 'ageHrs']))

    def test_calculate_sla_breach(self):
        """Test SLA breach calculation."""
        df = normalize_columns(self.sample_data.copy())
        df = parse_dates(df)
        df = add_status_fields(df)
        df = calculate_durations(df)

        # Use custom SLA rules for testing
        sla_rules = {
            '1 - Critical': 1,  # Very strict SLA for testing
            '2 - High': 24,
            '3 - Moderate': 72
        }

        df = calculate_sla_breach(df, sla_rules=sla_rules)

        self.assertIn('slaBreach', df.columns)
        self.assertIn('slaMarginHrs', df.columns)

    def test_transform_incidents_all(self):
        """Test complete transformation pipeline."""
        df = transform_incidents(self.sample_data.copy())

        # Check that all expected columns were added
        expected_columns = [
            'isActive', 'isResolved', 'isHighImpact', 'isCritical',
            'patternCategory', 'resolutionTimeHrs', 'slaBreach',
            'userImpactEstimate'
        ]

        for col in expected_columns:
            self.assertIn(col, df.columns, f"Missing column: {col}")

    def test_transform_incidents_specific(self):
        """Test transformation with specific transformations only."""
        df = transform_incidents(
            self.sample_data.copy(),
            transformations=['normalize', 'dates', 'status']
        )

        # Should have these transformations
        self.assertIn('isActive', df.columns)
        self.assertIn('openedDate', df.columns)

        # Should not have these (not in transformations list)
        self.assertNotIn('resolutionTimeHrs', df.columns)

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df_empty = pd.DataFrame()
        df_result = transform_incidents(df_empty)

        self.assertTrue(df_result.empty)


if __name__ == '__main__':
    unittest.main()
