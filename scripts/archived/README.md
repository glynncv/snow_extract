# Archived Scripts

This directory contains legacy scripts from before the project refactoring (November 2025).

## ⚠️ Status: DEPRECATED

These scripts are **no longer maintained** and have been replaced by the new `snow_analytics` package structure.

## What Happened?

The project was refactored from exploratory scripts into a professional, modular analytics toolkit. All functionality has been migrated to the new package structure.

## Migration Guide

### Old Scripts → New Modules

| Old Script | New Location | Notes |
|------------|--------------|-------|
| `real_data_extraction.py` | `snow_analytics/core/loaders.py` | Use `load_incidents()` function |
| `servicenow_extraction.py` | `examples/basic_usage.py` | See examples for usage |
| `servicenow_extraction_improved.py` | `examples/itsm_use_cases.py` | See examples for usage |
| `test_servicenow_api.py` | `tests/test_api.py` | Use pytest: `pytest -m api` |
| `src/network_incident_etl.py` | `snow_analytics/core/transform.py` | Use `transform_incidents()` function |
| `src/config_manager.py` | `snow_analytics/core/config.py` | Use `Config` class |
| `src/rca_generator.py` | `snow_analytics/rca/generator.py` | **Pending migration** (still in `src/`) |
| `src/rca_report_formatter.py` | `snow_analytics/rca/formatter.py` | **Pending migration** (still in `src/`) |

## New Usage

Instead of running these scripts directly, use the new package:

```python
from snow_analytics import (
    load_incidents,
    transform_incidents,
    calculate_sla_metrics
)

# Load data
df = load_incidents('api', limit=100)

# Transform
df = transform_incidents(df)

# Analyze
metrics = calculate_sla_metrics(df)
```

Or use the example scripts:
- `examples/basic_usage.py` - Basic workflow
- `examples/itsm_use_cases.py` - Real-world scenarios
- `examples/reporting_example.py` - Report generation

## Why Keep These?

These scripts are kept for:
- **Reference**: Understanding the original implementation
- **Migration**: Helping users transition to the new structure
- **Historical context**: Documenting the evolution of the project

## Need Help?

- See `README_REFACTORED.md` for the new structure
- See `REFACTORING_SUMMARY.md` for migration details
- Check `examples/` directory for working examples

---

**Last Updated:** November 2025  
**Refactoring Date:** November 14, 2025

