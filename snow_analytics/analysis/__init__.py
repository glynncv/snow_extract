"""
Analysis Modules
===============

Analytics, metrics, quality checks, and pattern detection for ServiceNow incidents.
"""

from snow_analytics.analysis.metrics import (
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics,
    analyze_reassignments
)
from snow_analytics.analysis.quality import (
    check_incident_quality,
    detect_priority_misclassification,
    detect_on_hold_abuse,
    check_description_quality,
    flag_excessive_reassignments
)
from snow_analytics.analysis.patterns import (
    analyze_patterns,
    find_recurring_issues
)

__all__ = [
    # Metrics
    "calculate_sla_metrics",
    "analyze_resolution_times",
    "calculate_backlog_metrics",
    "analyze_reassignments",

    # Quality
    "check_incident_quality",
    "detect_priority_misclassification",
    "detect_on_hold_abuse",
    "check_description_quality",
    "flag_excessive_reassignments",

    # Patterns
    "analyze_patterns",
    "find_recurring_issues",
]
