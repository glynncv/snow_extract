"""
ServiceNow Analytics Toolkit
============================

A comprehensive toolkit for extracting, processing, and analyzing ServiceNow incident data.

Main modules:
- core: Data loading, transformation, and validation
- analysis: Metrics, quality checks, and pattern detection
- connectors: ServiceNow API integration
- cli: Command-line interface

Note: For PII redaction when sharing data externally, use the separate redaction utility (src/redact5.py)

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "ServiceNow Analytics Team"

# Core functionality
from snow_analytics.core.loaders import load_incidents, load_from_api, load_from_csv
from snow_analytics.core.transform import transform_incidents
from snow_analytics.core.config import Config

# Analysis
from snow_analytics.analysis.metrics import calculate_sla_metrics, analyze_resolution_times

__all__ = [
    # Version
    "__version__",

    # Core
    "load_incidents",
    "load_from_api",
    "load_from_csv",
    "transform_incidents",
    "Config",

    # Analysis
    "calculate_sla_metrics",
    "analyze_resolution_times",
]
