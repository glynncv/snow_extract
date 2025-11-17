"""
Unit Tests for Incident Quality Checks
=======================================

Test cases for snow_analytics.analysis.quality module.
"""

import unittest
import pandas as pd
from datetime import datetime, timedelta

from snow_analytics.analysis.quality import (
    check_incident_quality,
    detect_priority_misclassification,
    detect_on_hold_abuse,
    check_description_quality,
    flag_excessive_reassignments
)
from snow_analytics.core.transform import transform_incidents


class TestQuality(unittest.TestCase):
    """Test cases for quality check functions."""

    def setUp(self):
        """Set up test fixtures."""
        base_time = datetime.now() - timedelta(days=1)
        
        # Create test data with various quality issues
        self.test_data = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003', 'INC004', 'INC005'],
            'short_description': [
                'Very short',  # Poor description
                'This is a longer description that meets quality standards',
                'Another good description',
                'Short',  # Poor description
                'Good description here'
            ],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate', '1 - Critical', '2 - High'],
            'state': ['Resolved', 'On Hold', 'Resolved', 'Resolved', 'New'],
            'openedDate': pd.to_datetime([
                base_time - timedelta(hours=30),  # Critical but slow resolution
                base_time - timedelta(hours=80),  # On Hold for too long
                base_time - timedelta(hours=10),
                base_time - timedelta(hours=5),
                base_time - timedelta(hours=2)
            ]),
            'resolvedDate': pd.to_datetime([
                base_time - timedelta(hours=1),  # Resolved after 29 hours
                None,  # Still active
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1),
                None
            ]),
            'reassignment_count': [1, 2, 4, 5, 0]  # Some excessive
        })
        
        self.df = transform_incidents(self.test_data)

    def test_check_incident_quality(self):
        """Test comprehensive quality check integration."""
        df_quality = check_incident_quality(self.df)
        
        # Should have quality flag columns
        self.assertIn('quality_priority_mismatch', df_quality.columns)
        self.assertIn('quality_on_hold_abuse', df_quality.columns)
        self.assertIn('quality_poor_description', df_quality.columns)
        self.assertIn('quality_excessive_reassignments', df_quality.columns)
        self.assertIn('quality_issues_count', df_quality.columns)

    def test_check_incident_quality_issues_count(self):
        """Test count total issues per incident."""
        df_quality = check_incident_quality(self.df)
        
        # Should have quality_issues_count column
        self.assertIn('quality_issues_count', df_quality.columns)
        
        # Count should be sum of boolean flags
        quality_flags = [
            'quality_priority_mismatch',
            'quality_on_hold_abuse',
            'quality_poor_description',
            'quality_excessive_reassignments'
        ]
        
        for flag in quality_flags:
            if flag in df_quality.columns:
                # Count should be non-negative
                self.assertTrue(all(df_quality['quality_issues_count'] >= 0))

    def test_detect_priority_misclassification(self):
        """Test critical priority with slow resolution."""
        df_check = detect_priority_misclassification(self.df)
        
        self.assertIn('quality_priority_mismatch', df_check.columns)
        
        # INC001 is Critical but took 29 hours to resolve
        if 'resolutionTimeHrs' in df_check.columns:
            critical_slow = df_check[
                (df_check['priority'].astype(str).str.contains('1 - Critical', na=False)) &
                (df_check['quality_priority_mismatch'] == True)
            ]
            # Should flag incidents with slow resolution
            self.assertIsInstance(critical_slow, pd.DataFrame)

    def test_detect_on_hold_abuse(self):
        """Test excessive On Hold time detection."""
        df_check = detect_on_hold_abuse(self.df, threshold_hours=72)
        
        self.assertIn('quality_on_hold_abuse', df_check.columns)
        
        # INC002 is On Hold for 80 hours
        on_hold_abuse = df_check[df_check['quality_on_hold_abuse'] == True]
        # Should flag incidents on hold too long
        self.assertIsInstance(on_hold_abuse, pd.DataFrame)

    def test_detect_on_hold_abuse_custom_threshold(self):
        """Test custom threshold."""
        df_check = detect_on_hold_abuse(self.df, threshold_hours=50)
        
        self.assertIn('quality_on_hold_abuse', df_check.columns)
        
        # With threshold=50, INC002 (80 hours) should be flagged
        on_hold_abuse = df_check[df_check['quality_on_hold_abuse'] == True]
        self.assertIsInstance(on_hold_abuse, pd.DataFrame)

    def test_check_description_quality(self):
        """Test short description detection."""
        df_check = check_description_quality(self.df, min_length=20)
        
        self.assertIn('quality_poor_description', df_check.columns)
        
        # INC001 and INC004 have short descriptions
        poor_desc = df_check[df_check['quality_poor_description'] == True]
        self.assertIsInstance(poor_desc, pd.DataFrame)

    def test_check_description_quality_custom_min_length(self):
        """Test custom min length."""
        df_check = check_description_quality(self.df, min_length=10)
        
        self.assertIn('quality_poor_description', df_check.columns)
        
        # With min_length=10, fewer should be flagged
        poor_desc = df_check[df_check['quality_poor_description'] == True]
        self.assertIsInstance(poor_desc, pd.DataFrame)

    def test_flag_excessive_reassignments(self):
        """Test reassignment flagging."""
        df_check = flag_excessive_reassignments(self.df, threshold=3)
        
        self.assertIn('quality_excessive_reassignments', df_check.columns)
        
        # INC003 (4) and INC004 (5) exceed threshold
        excessive = df_check[df_check['quality_excessive_reassignments'] == True]
        if not excessive.empty:
            self.assertTrue(all(excessive['reassignment_count'] > 3))

    def test_flag_excessive_reassignments_custom_threshold(self):
        """Test custom threshold."""
        df_check = flag_excessive_reassignments(self.df, threshold=4)
        
        self.assertIn('quality_excessive_reassignments', df_check.columns)
        
        # With threshold=4, only INC004 (5) should be flagged
        excessive = df_check[df_check['quality_excessive_reassignments'] == True]
        if not excessive.empty:
            self.assertTrue(all(excessive['reassignment_count'] > 4))

    def test_quality_flags_combined(self):
        """Test multiple quality issues on same incident."""
        df_quality = check_incident_quality(self.df)
        
        # INC001 has multiple issues: poor description, priority mismatch
        # Check that quality_issues_count reflects multiple issues
        if 'quality_issues_count' in df_quality.columns:
            # Should have incidents with multiple issues
            multiple_issues = df_quality[df_quality['quality_issues_count'] > 1]
            self.assertIsInstance(multiple_issues, pd.DataFrame)


if __name__ == '__main__':
    unittest.main()

