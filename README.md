# ServiceNow Data Extraction Pipeline

A comprehensive Python pipeline for extracting, processing, and analyzing ServiceNow incident data with PII redaction capabilities.

## 🚀 Quick Start

### 1. Setup Environment
```powershell
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure ServiceNow Connection
```powershell
# Copy environment template
copy .env.template .env

# Edit .env with your ServiceNow credentials
notepad .env
```

### 3. Test Connection
```powershell
# Test API connection using pytest
pytest -m api

# Or use the basic usage example
python examples\basic_usage.py
```

## 📋 Features

- **ServiceNow API Integration**: Extract data directly from ServiceNow REST API
- **Local File Processing**: Process existing CSV/JSON files
- **ETL Transformations**: Advanced data transformations for network incidents
- **PII Redaction**: Automatic redaction of sensitive information
- **Flexible Output**: CSV, JSON, and Excel output formats
- **Robust Error Handling**: Comprehensive logging and error management

## 🔧 Usage Examples

### Quick Start Examples

The `examples/` directory contains three demonstration scripts:

#### 1. Basic Usage (`examples/basic_usage.py`)
Simple workflow demonstration - perfect for getting started:
```powershell
python examples\basic_usage.py
```
Shows: Data loading → Transformation → Metrics → Export

#### 2. ITSM Use Cases (`examples/itsm_use_cases.py`)
Real-world scenarios for common ITSM operations:
```powershell
python examples\itsm_use_cases.py
```
Includes: SLA reports, backlog management, problem identification, quality checks, routing optimization, executive dashboards

#### 3. Reporting Example (`examples/reporting_example.py`)
Export formats and pre-built report templates:
```powershell
python examples\reporting_example.py
```
Shows: CSV/Excel/JSON exports, SLA reports, backlog reports, quality reports, executive summaries

### Using the New Package

The project has been refactored into a modular `snow_analytics` package. Use the examples above or import directly:

```python
from snow_analytics import load_incidents, transform_incidents

# Load from API
df = load_incidents('api', limit=100)

# Load from CSV
df = load_incidents('csv', file_path='data/incidents.csv')

# Transform data
df = transform_incidents(df)
```

> **Note:** Legacy scripts have been moved to `scripts/archived/`. See `README_REFACTORED.md` for the complete guide to the new structure.

## 📁 Project Structure

```
snow_extract/
├── src/                    # Source utilities (mixed legacy/active)
│   ├── redact5.py                 # PII redaction utility (active)
│   ├── rca_generator.py           # RCA generator (legacy, pending migration)
│   ├── rca_report_formatter.py    # RCA formatter (legacy, pending migration)
│   └── archived/                  # Deprecated modules
│       ├── network_incident_etl.py    # → snow_analytics/core/transform.py
│       └── config_manager.py          # → snow_analytics/core/config.py
├── scripts/                # Legacy scripts (archived)
│   └── archived/          # Deprecated scripts - see README_REFACTORED.md
├── examples/               # Example scripts (recommended)
│   ├── basic_usage.py     # Basic workflow example
│   ├── itsm_use_cases.py  # Real-world ITSM scenarios
│   └── reporting_example.py  # Report generation examples
├── snow_analytics/         # Main package (new structure)
├── data/                   # Data directories
│   ├── raw/               # Original data files
│   ├── processed/         # Transformed data
│   └── redacted/          # PII-redacted data
├── config/                # Configuration files
├── logs/                  # Application logs
├── output/                # Final output files
└── tests/                 # Unit tests
```

## 🔑 Configuration

### Environment Variables
Create a `.env` file with your ServiceNow credentials:

```
SNOW_INSTANCE_URL=https://your-instance.service-now.com
SNOW_USERNAME=your_username
SNOW_PASSWORD=your_password
```

### ServiceNow Configuration
Edit `config/servicenow_config.json` for advanced settings:

```json
{
  "servicenow": {
    "instance_url": "https://your-instance.service-now.com",
    "timeout": 30
  },
  "extraction": {
    "batch_size": 1000,
    "query_filters": {
      "network_incidents": "assignment_groupLIKEnetwork"
    }
  }
}
```

## 🔄 Data Pipeline

### 1. Extraction
- **API Mode**: Connects to ServiceNow REST API
- **File Mode**: Reads local CSV/JSON files
- **Configurable filters**: Query specific incident types

### 2. ETL Transformation
The `network_incident_etl.py` module adds analytical columns:
- `isActive`: Boolean indicating if incident is active
- `isHighImpact`: High priority/impact incidents
- `patternCategory`: Categorization based on description patterns
- `resolutionTimeHrs`: Time to resolution in hours
- `slaBreach`: SLA compliance status
- `locationParsed`: Structured location information
- `priorityScore`: Numerical priority scoring

### 3. PII Redaction
The `redact5.py` module handles:
- Email addresses
- Phone numbers
- IP addresses
- Personal names
- Custom patterns

### 4. Output Generation
- **CSV**: Standard comma-separated format
- **JSON**: Structured JSON with metadata
- **Excel**: Multi-sheet workbooks with summaries

## 🧪 Testing

### Run All Tests
```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=snow_analytics

# Run API tests (requires credentials)
pytest -m api

# Run specific test file
pytest tests/test_loaders.py
```

### Example Scripts
```powershell
# Basic usage example
python examples\basic_usage.py

# ITSM use cases
python examples\itsm_use_cases.py

# Reporting examples
python examples\reporting_example.py
```

## 🔐 Security

- **Credential Management**: Use environment variables, never hardcode
- **PII Protection**: Automatic redaction of sensitive data
- **API Security**: HTTPS-only connections with proper authentication
- **Audit Trail**: Comprehensive logging of all operations

## 🚨 Common Issues

### Connection Problems
- Verify ServiceNow instance URL
- Check username/password
- Ensure API access permissions

### Data Issues
- Validate CSV file format
- Check column mappings
- Review query filters
