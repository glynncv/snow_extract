"""
Unit Tests for Metrics and KPI Calculations
===========================================

Test cases for snow_analytics.analysis.metrics module.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from snow_analytics.analysis.metrics import (
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics,
    analyze_reassignments
)
from snow_analytics.core.loaders import generate_sample_data
from snow_analytics.core.transform import transform_incidents


class TestMetrics(unittest.TestCase):
    """Test cases for metrics calculations."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample data with resolved incidents
        base_time = datetime.now() - timedelta(days=2)
        
        self.resolved_data = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003', 'INC004'],
            'short_description': ['Test 1', 'Test 2', 'Test 3', 'Test 4'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate', '1 - Critical'],
            'state': ['Resolved', 'Resolved', 'Resolved', 'Resolved'],
            'openedDate': pd.to_datetime([
                base_time - timedelta(hours=2),
                base_time - timedelta(hours=25),
                base_time - timedelta(hours=50),
                base_time - timedelta(hours=5)
            ]),
            'resolvedDate': pd.to_datetime([
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1),
                base_time - timedelta(hours=1)
            ]),
            'patternCategory': ['WiFi/Wireless', 'VPN/Remote Access', 'DNS/Resolution', 'WiFi/Wireless']
        })
        
        # Transform to add required columns
        self.resolved_df = transform_incidents(self.resolved_data)
        
        # Create active incidents for backlog
        self.active_data = pd.DataFrame({
            'number': ['INC005', 'INC006', 'INC007'],
            'short_description': ['Active 1', 'Active 2', 'Active 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'state': ['New', 'In Progress', 'On Hold'],
            'openedDate': pd.to_datetime([
                datetime.now() - timedelta(hours=12),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=5)
            ]),
            'resolvedDate': [None, None, None]
        })
        
        self.active_df = transform_incidents(self.active_data)
        
        # Combined DataFrame
        self.combined_df = pd.concat([self.resolved_df, self.active_df], ignore_index=True)

    def test_calculate_sla_metrics(self):
        """Test overall SLA metrics with resolved incidents."""
        metrics = calculate_sla_metrics(self.resolved_df)
        
        self.assertIn('total_resolved', metrics)
        self.assertIn('sla_breached', metrics)
        self.assertIn('sla_met', metrics)
        self.assertIn('breach_rate_pct', metrics)
        self.assertIn('by_priority', metrics)
        
        self.assertEqual(metrics['total_resolved'], len(self.resolved_df))
        self.assertGreaterEqual(metrics['breach_rate_pct'], 0)
        self.assertLessEqual(metrics['breach_rate_pct'], 100)

    def test_calculate_sla_metrics_empty(self):
        """Test handling empty DataFrame."""
        df_empty = pd.DataFrame()
        metrics = calculate_sla_metrics(df_empty)
        
        self.assertEqual(metrics['total_resolved'], 0)
        self.assertEqual(metrics['breach_rate_pct'], 0.0)

    def test_calculate_sla_metrics_by_priority(self):
        """Test SLA breakdown by priority."""
        metrics = calculate_sla_metrics(self.resolved_df)
        
        self.assertIsInstance(metrics['by_priority'], dict)
        
        # Check that priorities are included
        if metrics['by_priority']:
            for priority, stats in metrics['by_priority'].items():
                self.assertIn('total', stats)
                self.assertIn('breached', stats)
                self.assertIn('breach_rate_pct', stats)

    def test_calculate_sla_metrics_missing_columns(self):
        """Test handle missing required columns."""
        df_no_resolution = pd.DataFrame({
            'number': ['INC001'],
            'priority': ['1 - Critical']
        })
        
        metrics = calculate_sla_metrics(df_no_resolution)
        
        # Should return empty metrics without error
        self.assertEqual(metrics['total_resolved'], 0)

    def test_analyze_resolution_times(self):
        """Test overall resolution time statistics."""
        analysis = analyze_resolution_times(self.resolved_df)
        
        self.assertIn('overall', analysis)
        self.assertIn('by_priority', analysis)
        self.assertIn('by_category', analysis)
        
        overall = analysis['overall']
        self.assertIn('count', overall)
        self.assertIn('mean_hrs', overall)
        self.assertIn('median_hrs', overall)
        self.assertGreater(overall['count'], 0)

    def test_analyze_resolution_times_by_priority(self):
        """Test breakdown by priority."""
        analysis = analyze_resolution_times(self.resolved_df, by_priority=True)
        
        self.assertIsInstance(analysis['by_priority'], dict)
        
        if analysis['by_priority']:
            for priority, stats in analysis['by_priority'].items():
                self.assertIn('count', stats)
                self.assertIn('mean_hrs', stats)
                self.assertIn('median_hrs', stats)

    def test_analyze_resolution_times_by_category(self):
        """Test breakdown by category."""
        analysis = analyze_resolution_times(self.resolved_df, by_category=True)
        
        self.assertIsInstance(analysis['by_category'], dict)
        
        if analysis['by_category']:
            for category, stats in analysis['by_category'].items():
                self.assertIn('count', stats)
                self.assertIn('mean_hrs', stats)

    def test_calculate_backlog_metrics(self):
        """Test backlog metrics for active incidents."""
        metrics = calculate_backlog_metrics(self.active_df)
        
        self.assertIn('total_backlog', metrics)
        self.assertIn('by_priority', metrics)
        self.assertIn('by_age', metrics)
        self.assertIn('avg_age_days', metrics)
        
        self.assertEqual(metrics['total_backlog'], len(self.active_df))
        self.assertGreaterEqual(metrics['avg_age_days'], 0)

    def test_calculate_backlog_metrics_by_age(self):
        """Test age distribution buckets."""
        metrics = calculate_backlog_metrics(self.active_df)
        
        self.assertIn('less_than_24h', metrics['by_age'])
        self.assertIn('24h_to_3days', metrics['by_age'])
        self.assertIn('3days_to_1week', metrics['by_age'])
        self.assertIn('1week_to_1month', metrics['by_age'])
        self.assertIn('more_than_1month', metrics['by_age'])
        
        # Sum of age buckets should equal total backlog
        total_by_age = sum(metrics['by_age'].values())
        self.assertEqual(total_by_age, metrics['total_backlog'])

    def test_calculate_backlog_metrics_by_priority(self):
        """Test backlog by priority."""
        metrics = calculate_backlog_metrics(self.active_df)
        
        self.assertIsInstance(metrics['by_priority'], dict)
        
        # Sum of priorities should equal total backlog
        total_by_priority = sum(metrics['by_priority'].values())
        self.assertEqual(total_by_priority, metrics['total_backlog'])

    def test_calculate_backlog_metrics_empty(self):
        """Test handling empty backlog."""
        df_no_active = pd.DataFrame()
        metrics = calculate_backlog_metrics(df_no_active)
        
        self.assertEqual(metrics['total_backlog'], 0)
        self.assertEqual(metrics['avg_age_days'], 0.0)

    def test_analyze_reassignments(self):
        """Test flag excessive reassignments."""
        df_with_reassignments = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003', 'INC004'],
            'short_description': ['Test 1', 'Test 2', 'Test 3', 'Test 4'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate', '4 - Low'],
            'assignment_group': ['Group A', 'Group B', 'Group C', 'Group D'],
            'reassignment_count': [1, 3, 5, 7]  # 3, 5, 7 exceed threshold of 2
        })
        
        result = analyze_reassignments(df_with_reassignments, threshold=2)
        
        self.assertIsInstance(result, pd.DataFrame)
        if not result.empty:
            self.assertIn('reassignment_count', result.columns)
            self.assertIn('reassignment_severity', result.columns)
            # All results should exceed threshold
            self.assertTrue(all(result['reassignment_count'] > 2))

    def test_analyze_reassignments_threshold(self):
        """Test custom threshold handling."""
        df_with_reassignments = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'short_description': ['Test 1', 'Test 2'],
            'priority': ['1 - Critical', '2 - High'],
            'assignment_group': ['Group A', 'Group B'],
            'reassignment_count': [2, 4]
        })
        
        # With threshold=3, only INC002 should be flagged
        result = analyze_reassignments(df_with_reassignments, threshold=3)
        
        if not result.empty:
            self.assertTrue(all(result['reassignment_count'] > 3))

    def test_analyze_reassignments_severity_classification(self):
        """Test severity classification."""
        df_with_reassignments = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003'],
            'short_description': ['Test 1', 'Test 2', 'Test 3'],
            'priority': ['1 - Critical', '2 - High', '3 - Moderate'],
            'assignment_group': ['Group A', 'Group B', 'Group C'],
            'reassignment_count': [3, 4, 6]  # Moderate, High, Critical
        })
        
        result = analyze_reassignments(df_with_reassignments, threshold=2)
        
        if not result.empty:
            self.assertIn('reassignment_severity', result.columns)
            # Check severity values
            severities = result['reassignment_severity'].unique()
            self.assertTrue(any(s in ['Moderate', 'High', 'Critical'] for s in severities))


if __name__ == '__main__':
    unittest.main()

