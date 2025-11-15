# ServiceNow Analytics Toolkit

**A comprehensive, modular Python package for extracting, processing, and analyzing ServiceNow incident data.**

---

## What Changed? 🔄

This repository has been **completely refactored** from exploratory scripts into a professional Python package:

### Before (Old Structure):
```
❌ Multiple overlapping scripts (real_data_extraction.py, servicenow_extraction.py, etc.)
❌ Hard-coded Windows paths
❌ Repeated logic across files
❌ Inconsistent imports and naming
❌ Limited tests
❌ No proper package structure
```

### After (New Structure):
```
✅ Clean modular package (`snow_analytics/`)
✅ Reusable, tested modules
✅ Configuration-driven (no hard-coded paths)
✅ Comprehensive API
✅ Type hints and docstrings
✅ Proper Python packaging (setup.py, pyproject.toml)
✅ CLI interface
✅ Extensive documentation
```

> **Note on PII Redaction:** The privacy module has been removed from the core package. For internal ITSM analysis, use full, unredacted data. For PII redaction when sharing data externally, use the separate redaction utility (`src/redact5.py`).

---

## Installation

### Development Installation (Recommended)

```bash
# Clone repository
cd snow_extract

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Optional: Install visualization and notebook support
pip install -e ".[viz,notebooks]"
```

### Production Installation

```bash
pip install -e .
```

---

## Quick Start

### 1. Configure Credentials

Create a `.env` file:

```bash
SNOW_INSTANCE_URL=https://your-instance.service-now.com
SNOW_USERNAME=your_username
SNOW_PASSWORD=your_password
```

Or use a YAML config file (`config/default_config.yaml`):

```yaml
servicenow:
  instance_url: "https://your-instance.service-now.com"
  username: "your_username"
  password: "your_password"
  timeout: 30

extraction:
  batch_size: 1000
  query_filter: "assignment_groupLIKEnetwork"

sla:
  rules:
    "1 - Critical": 4
    "2 - High": 24
    "3 - Moderate": 72
    "4 - Low": 120
```

### 2. Basic Usage (Python API)

```python
from snow_analytics import load_incidents, transform_incidents, calculate_sla_metrics

# Load incidents from ServiceNow API
df_raw = load_incidents(source='api', limit=1000)

# Or load from CSV
df_raw = load_incidents(source='csv', file_path='data/incidents.csv')

# Or generate sample data for testing
df_raw = load_incidents(source='sample', num_records=50)

# Transform data (ETL)
df_transformed = transform_incidents(df_raw)

# Calculate SLA metrics
sla_metrics = calculate_sla_metrics(df_transformed)
print(f"SLA Breach Rate: {sla_metrics['breach_rate_pct']}%")

# Save results
df_transformed.to_csv('output/incidents_processed.csv', index=False)

# Note: For PII redaction when sharing externally, use src/redact5.py
```

### 3. CLI Usage

```bash
# Extract incidents from API
snow-analytics extract --source api --limit 1000 --output data/raw/incidents.csv

# Load and transform CSV file
snow-analytics transform data/raw/incidents.csv --output data/processed/incidents.csv

# Calculate metrics
snow-analytics analyze data/processed/incidents.csv --metrics sla,quality,patterns

# Generate RCA report
snow-analytics rca INC0012345 --format markdown --output reports/rca_inc0012345.md

# Full pipeline (extract, transform, analyze, redact)
snow-analytics pipeline --source api --limit 1000 --full
```

---

## Project Structure

```
snow_analytics/                    # Main package
├── core/                          # Core functionality
│   ├── loaders.py                # Data loading (API, CSV, sample)
│   ├── transform.py              # ETL transformations
│   ├── validators.py             # Schema & data validation
│   └── config.py                 # Configuration management
│
├── analysis/                      # Analytics modules
│   ├── metrics.py                # KPI calculations (SLA, resolution, backlog)
│   ├── quality.py                # Quality checks
│   └── patterns.py               # Pattern detection
│
├── connectors/                    # ServiceNow connectivity
│   ├── api.py                    # REST API client
│   └── exceptions.py             # Custom exceptions
│
├── rca/                          # Root Cause Analysis
│   ├── generator.py              # RCA generation
│   └── formatter.py              # Report formatting
│
└── cli/                          # Command-line interface
    └── main.py                   # CLI entry point
```

---

## Key Features

### 1. **Unified Data Loading**

Load from multiple sources with a consistent API:

```python
# API
df = load_incidents('api', limit=1000)

# CSV file
df = load_incidents('csv', file_path='data/incidents.csv')

# Sample data (for testing)
df = load_incidents('sample', num_records=100)
```

### 2. **Configurable ETL Transformations**

Apply transformations modularly:

```python
from snow_analytics.core import transform_incidents

# Apply all transformations
df = transform_incidents(df_raw)

# Apply specific transformations only
df = transform_incidents(df_raw, transformations=['dates', 'status', 'durations', 'sla'])
```

Added fields:
- `isActive`, `isResolved`, `isHighImpact`, `isCritical` - Status flags
- `patternCategory` - Incident categorization (WiFi, VPN, DNS, etc.)
- `resolutionTimeHrs`, `resolutionTimeDays` - Resolution duration
- `ageHrs`, `ageDays` - Age for active incidents
- `slaBreach`, `slaMarginHrs` - SLA compliance
- `userImpactEstimate` - Estimated user impact
- `week`, `month`, `quarter`, `dayOfWeek`, `hourOfDay` - Temporal fields

### 3. **Comprehensive Metrics**

```python
from snow_analytics.analysis import (
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics,
    analyze_reassignments
)

# SLA metrics
sla = calculate_sla_metrics(df)
# Returns: breach_rate_pct, by_priority breakdown, etc.

# Resolution time analysis
resolution = analyze_resolution_times(df, by_priority=True, by_category=True)
# Returns: mean, median, percentiles by priority and category

# Backlog metrics
backlog = calculate_backlog_metrics(df)
# Returns: total_backlog, by_age, by_priority, avg_age_days

# Reassignment analysis
reassignments = analyze_reassignments(df, threshold=2)
# Returns: DataFrame of incidents with excessive reassignments
```

### 4. **Quality Checks**

```python
from snow_analytics.analysis.quality import (
    check_incident_quality,
    detect_priority_misclassification,
    detect_on_hold_abuse,
    flag_excessive_reassignments
)

# Comprehensive quality check
df_quality = check_incident_quality(df)

# Individual checks
df = detect_priority_misclassification(df)
df = detect_on_hold_abuse(df, threshold_hours=72)
df = flag_excessive_reassignments(df, threshold=3)

# View quality issues
quality_issues = df_quality[df_quality['quality_issues_count'] > 0]
```

### 5. **PII Redaction** (External Utility)

For PII redaction when sharing data externally, use the separate redaction utility:

```python
# Export your data first
df_transformed.to_csv('output/incidents_for_sharing.csv', index=False)

# Then run the redaction utility
from src.redact5 import redact_dataframe_columns

df_redacted = redact_dataframe_columns(
    df,
    text_columns=['description', 'work_notes'],
    id_columns=['number'],
    drop_columns=['caller_id', 'assigned_to']
)

df_redacted.to_csv('output/incidents_redacted.csv', index=False)
```

**Note:** Internal ITSM analysis should use full, unredacted data. Only redact when data leaves organizational control.

### 6. **Root Cause Analysis**

```python
from snow_analytics.rca import RCAGenerator, RCAReportFormatter

# Initialize generator
rca_gen = RCAGenerator(
    instance_url='https://instance.service-now.com',
    username='user',
    password='pass'
)

# Generate RCA
incident_data = rca_gen.extract_incident_data('INC0012345')
analysis = rca_gen.analyze_root_cause(incident_data)

# Format report
formatter = RCAReportFormatter()
report = formatter.generate_report(incident_data, analysis, format='markdown')

# Save report
formatter.save_report(report, 'output/rca_inc0012345.md', format='markdown')
```

---

## Configuration

### SLA Rules (`config/default_config.yaml`)

```yaml
sla:
  rules:
    "1 - Critical": 4     # 4 hours
    "2 - High": 24        # 24 hours
    "3 - Moderate": 72    # 72 hours
    "4 - Low": 120        # 120 hours
```

### Categorization Rules

```yaml
categorization:
  rules:
    "WiFi/Wireless": ["wifi", "wireless", "access point", "wap", "ssid"]
    "VPN/Remote Access": ["vpn", "remote", "zscaler"]
    "Network Printing": ["printer", "print", "printing"]
    "DNS/Resolution": ["dns", "resolution", "name resolution"]
    "Firewall/Security": ["firewall", "blocked", "security"]
```

### Quality Check Thresholds

```yaml
quality:
  min_description_length: 20
  max_reassignment_threshold: 3
  on_hold_threshold_hours: 72
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=snow_analytics --cov-report=html

# Run specific test file
pytest tests/test_loaders.py

# Run specific test
pytest tests/test_transform.py::test_normalize_columns
```

---

## Examples

See the `examples/` directory for complete usage examples:

- `examples/basic_extraction.py` - Simple extraction and analysis
- `examples/full_pipeline.py` - Complete pipeline with all features
- `examples/notebooks/exploratory_analysis.ipynb` - Interactive analysis

---

## Refactor Mapping

### Old → New Module Mapping

| Old File | New Module | Key Functions |
|----------|-----------|---------------|
| `real_data_extraction.py` | `core/loaders.py` | `load_from_api()`, `load_from_csv()` |
| `network_incident_etl.py` | `core/transform.py` | `transform_incidents()`, `calculate_durations()` |
| `redact5.py` | `src/redact5.py` (separate utility) | `redact_dataframe_columns()`, `hash_id()` |
| `config_manager.py` | `core/config.py` | `Config` class (enhanced) |
| `rca_generator.py` | `rca/generator.py` | `RCAGenerator` class (refactored) |
| `rca_report_formatter.py` | `rca/formatter.py` | `RCAReportFormatter` class |

### Breaking Changes

1. **No hard-coded paths** - All paths now passed as parameters or configured
2. **Consistent imports** - Import from `snow_analytics.*` instead of direct file imports
3. **Column naming** - Standardized to `openedDate`, `resolvedDate` (was inconsistent)
4. **API changes**:
   - `transform_incident_frame()` → `transform_incidents()`
   - ServiceNow API client now in `connectors.api.ServiceNowAPI`
5. **Privacy module removed** - Use `src/redact5.py` directly for external data sharing

---

## Migration Guide

### For Existing Scripts

**Old:**
```python
# Old import style
import sys
sys.path.insert(0, 'src')
from network_incident_etl import transform_incident_frame
from redact5 import redact_dataframe_columns

# Old usage with hard-coded paths
df = pd.read_csv(r"C:\Users\...\data.csv")
df_transformed = transform_incident_frame(df)
df_redacted = redact_dataframe_columns(df)
```

**New:**
```python
# New clean imports
from snow_analytics import load_incidents, transform_incidents

# New usage with configuration
df = load_incidents('csv', file_path='data/incidents.csv')
df_transformed = transform_incidents(df)

# For external sharing, use separate redaction utility:
# from src.redact5 import redact_dataframe_columns
# df_redacted = redact_dataframe_columns(df_transformed)
```

---

## Contributing

1. Install development dependencies: `pip install -e ".[dev]"`
2. Make changes to code
3. Run tests: `pytest`
4. Format code: `black snow_analytics/`
5. Check linting: `flake8 snow_analytics/`
6. Submit pull request

---

## License

MIT License

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/snow-analytics/issues
- Documentation: https://docs.snow-analytics.com
- Email: analytics@company.com

---

## Changelog

### v1.0.0 (2025-11-14)

**Major Refactor:**
- ✅ Converted exploratory scripts to professional Python package
- ✅ Created modular structure with clear separation of concerns
- ✅ Added comprehensive test suite
- ✅ Implemented CLI interface
- ✅ Added configuration management (YAML/JSON)
- ✅ Removed hard-coded paths and values
- ✅ Added type hints and documentation
- ✅ Improved error handling and logging
- ✅ Added quality checks module
- ✅ Enhanced PII redaction
- ✅ Refactored RCA generation

**Breaking Changes:**
- Module reorganization (see Migration Guide)
- Function renames for consistency
- Configuration now required for some operations

---

**Built with ❤️ by the ServiceNow Analytics Team**
