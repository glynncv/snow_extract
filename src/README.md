# Source Directory (`/src`)

This directory contains a mix of **legacy code** and **active utilities**.

## File Status

### ✅ Active (Keep)
- **`redact5.py`** - PII redaction utility for external data sharing
  - **Status:** Active utility (intentionally kept separate from core package)
  - **Purpose:** Redact PII when sharing data externally
  - **Usage:** Import directly: `from src.redact5 import redact_dataframe_columns`
  - **Note:** Internal ITSM analysis uses full, unredacted data

### ⚠️ Legacy (Deprecated - Replaced)
- **`network_incident_etl.py`** - ETL transformations
  - **Status:** DEPRECATED - Replaced by `snow_analytics/core/transform.py`
  - **Migration:** Use `from snow_analytics import transform_incidents`
  - **Old:** `from network_incident_etl import transform_incident_frame`
  - **New:** `from snow_analytics import transform_incidents`

- **`config_manager.py`** - Configuration management
  - **Status:** DEPRECATED - Replaced by `snow_analytics/core/config.py`
  - **Migration:** Use `from snow_analytics.core import Config`
  - **Old:** `from config_manager import config`
  - **New:** `from snow_analytics.core import Config`

### ✅ Migrated (Now in snow_analytics package)
- **`rca_generator.py`** - Root Cause Analysis generator
  - **Status:** MIGRATED - Now in `snow_analytics/rca/generator.py`
  - **New Import:** `from snow_analytics.rca import RCAGenerator`
  - **Old Import:** `from rca_generator import ServiceNowRCAGenerator` (deprecated)
  - **Note:** Old file moved to `src/archived/`

- **`rca_report_formatter.py`** - RCA report formatting
  - **Status:** MIGRATED - Now in `snow_analytics/rca/formatter.py`
  - **New Import:** `from snow_analytics.rca import RCAReportFormatter`
  - **Old Import:** `from rca_report_formatter import RCAReportFormatter` (deprecated)
  - **Note:** Old file moved to `src/archived/`

## Migration Guide

### For ETL Transformations
```python
# Old (deprecated)
from network_incident_etl import transform_incident_frame
df = transform_incident_frame(df_raw)

# New (recommended)
from snow_analytics import transform_incidents
df = transform_incidents(df_raw)
```

### For Configuration
```python
# Old (deprecated)
from config_manager import config
instance_url = config.get('servicenow', 'instance_url')

# New (recommended)
from snow_analytics.core import Config
config = Config()
instance_url = config.get('servicenow.instance_url')
```

### For RCA (Root Cause Analysis)
```python
# New (recommended)
from snow_analytics import RCAGenerator, RCAReportFormatter

generator = RCAGenerator()
rca_data = generator.generate_rca(incident_sys_id='...')
formatter = RCAReportFormatter()
report = formatter.format_report(rca_data)
```

### For PII Redaction (Still Active)
```python
# Current (still valid)
from src.redact5 import redact_dataframe_columns
df_redacted = redact_dataframe_columns(df, columns=['description', 'comments'])
```

## Recommendations

1. **Use `snow_analytics` package** for all new development
2. **Keep `redact5.py`** - It's intentionally separate for external data sharing
3. ✅ **RCA modules migrated** - Now available in `snow_analytics/rca/` (November 2025)
4. ✅ **Legacy files archived** - All deprecated modules moved to `src/archived/`

---

**Last Updated:** November 2025  
**Refactoring Date:** November 14, 2025

