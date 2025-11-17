"""
Unit Tests for Data Validation
===============================

Test cases for snow_analytics.core.validators module.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from snow_analytics.core.validators import (
    validate_incident_schema,
    validate_data_quality
)


class TestValidators(unittest.TestCase):
    """Test cases for validation functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_df = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003'],
            'short_description': ['Test 1', 'Test 2', 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['New', 'In Progress', 'Resolved'],
            'openedDate': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03'])
        })

    def test_validate_incident_schema_success(self):
        """Test valid schema passes validation."""
        is_valid, issues = validate_incident_schema(self.valid_df, warn_only=False)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)

    def test_validate_incident_schema_missing_columns(self):
        """Test missing required columns."""
        df_missing = pd.DataFrame({
            'number': ['INC001'],
            'short_description': ['Test']
            # Missing priority and state
        })
        
        is_valid, issues = validate_incident_schema(df_missing, warn_only=False)
        
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any('Missing required columns' in issue for issue in issues))

    def test_validate_incident_schema_empty_dataframe(self):
        """Test empty DataFrame handling."""
        df_empty = pd.DataFrame()
        
        is_valid, issues = validate_incident_schema(df_empty, warn_only=False)
        
        self.assertFalse(is_valid)
        self.assertIn('DataFrame is empty', issues)

    def test_validate_incident_schema_null_columns(self):
        """Test all-null columns warning."""
        df_null_col = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'short_description': ['Test 1', 'Test 2'],
            'priority': ['1 - Critical', '2 - High'],
            'state': ['New', 'In Progress'],
            'null_column': [None, None]  # All null
        })
        
        is_valid, issues = validate_incident_schema(df_null_col, warn_only=True)
        
        # Should warn about null column
        self.assertTrue(any('null values' in issue.lower() for issue in issues))

    def test_validate_incident_schema_duplicate_numbers(self):
        """Test duplicate incident numbers."""
        df_duplicate = pd.DataFrame({
            'number': ['INC001', 'INC001', 'INC002'],  # Duplicate
            'short_description': ['Test 1', 'Test 2', 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['New', 'In Progress', 'Resolved']
        })
        
        is_valid, issues = validate_incident_schema(df_duplicate, warn_only=True)
        
        # Should warn about duplicates
        self.assertTrue(any('duplicate' in issue.lower() for issue in issues))

    def test_validate_incident_schema_date_types(self):
        """Test date column type checking."""
        df_string_dates = pd.DataFrame({
            'number': ['INC001'],
            'short_description': ['Test'],
            'priority': ['1 - Critical'],
            'state': ['New'],
            'openedDate': ['2025-01-01']  # String, not datetime
        })
        
        is_valid, issues = validate_incident_schema(df_string_dates, warn_only=True)
        
        # Should warn about date type
        self.assertTrue(any('datetime' in issue.lower() for issue in issues))

    def test_validate_incident_schema_warn_only(self):
        """Test warn-only mode."""
        df_missing = pd.DataFrame({
            'number': ['INC001']
            # Missing required columns
        })
        
        is_valid, issues = validate_incident_schema(df_missing, warn_only=True)
        
        # Should return True in warn-only mode even with issues
        self.assertTrue(is_valid)
        self.assertGreater(len(issues), 0)

    def test_validate_incident_schema_strict(self):
        """Test strict validation mode."""
        df_missing = pd.DataFrame({
            'number': ['INC001']
            # Missing required columns
        })
        
        is_valid, issues = validate_incident_schema(df_missing, warn_only=False)
        
        # Should return False in strict mode
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)

    def test_validate_data_quality(self):
        """Test overall quality score calculation."""
        quality_report = validate_data_quality(self.valid_df)
        
        self.assertIn('total_records', quality_report)
        self.assertIn('data_quality_score', quality_report)
        self.assertEqual(quality_report['total_records'], 3)
        self.assertGreaterEqual(quality_report['data_quality_score'], 0)
        self.assertLessEqual(quality_report['data_quality_score'], 100)

    def test_validate_data_quality_null_percentages(self):
        """Test null percentage tracking."""
        df_with_nulls = pd.DataFrame({
            'number': ['INC001', 'INC002', None],
            'short_description': ['Test 1', None, 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['New', 'In Progress', 'Resolved']
        })
        
        quality_report = validate_data_quality(df_with_nulls)
        
        self.assertIn('null_percentages', quality_report)
        self.assertIn('number', quality_report['null_percentages'])
        self.assertGreater(quality_report['null_percentages']['number'], 0)

    def test_validate_data_quality_critical_columns(self):
        """Test critical column validation."""
        df_missing_critical = pd.DataFrame({
            'number': ['INC001', None, 'INC003'],  # One null
            'short_description': ['Test 1', 'Test 2', 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['New', 'In Progress', 'Resolved']
        })
        
        quality_report = validate_data_quality(df_missing_critical)
        
        # Should have issues for null in critical column
        self.assertGreater(len(quality_report['issues']), 0)
        self.assertLess(quality_report['data_quality_score'], 100)

    def test_validate_data_quality_short_descriptions(self):
        """Test description quality check."""
        df_short_desc = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'short_description': ['A', 'Very short'],  # Very short descriptions
            'priority': ['1 - Critical', '2 - High'],
            'state': ['New', 'In Progress']
        })
        
        quality_report = validate_data_quality(df_short_desc)
        
        # Should warn about short descriptions
        self.assertGreater(len(quality_report['warnings']), 0)

    def test_validate_data_quality_invalid_priorities(self):
        """Test priority validation."""
        df_invalid_priority = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'short_description': ['Test 1', 'Test 2'],
            'priority': ['Invalid', '5 - Unknown'],  # Invalid priorities
            'state': ['New', 'In Progress']
        })
        
        quality_report = validate_data_quality(df_invalid_priority)
        
        # Should warn about invalid priorities
        self.assertTrue(
            any('invalid priority' in warning.lower() 
                for warning in quality_report['warnings'])
        )

    def test_validate_data_quality_empty(self):
        """Test empty DataFrame handling."""
        df_empty = pd.DataFrame()
        
        quality_report = validate_data_quality(df_empty)
        
        self.assertEqual(quality_report['total_records'], 0)
        self.assertEqual(quality_report['data_quality_score'], 0.0)
        self.assertIn('DataFrame is empty', quality_report['issues'])


if __name__ == '__main__':
    unittest.main()

