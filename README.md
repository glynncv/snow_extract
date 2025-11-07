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
python scripts\test_servicenow_api.py
```

## 📋 Features

- **ServiceNow API Integration**: Extract data directly from ServiceNow REST API
- **Local File Processing**: Process existing CSV/JSON files
- **ETL Transformations**: Advanced data transformations for network incidents
- **PII Redaction**: Automatic redaction of sensitive information
- **Flexible Output**: CSV, JSON, and Excel output formats
- **Robust Error Handling**: Comprehensive logging and error management

## 🔧 Usage Examples

### Extract from ServiceNow API
```powershell
# Extract 100 recent network incidents
python real_data_extraction.py --api --sample-size 100

# Extract with custom filter
python real_data_extraction.py --api --query "assignment_groupLIKEnetwork^priorityIN1,2"
```

### Process Local Files
```powershell
# Process existing data file
python real_data_extraction.py --file data\raw\incidents.csv

# Process with full ETL pipeline
python real_data_extraction.py --file data\raw\incidents.csv --apply-etl --redact-pii
```

### Sample Data Testing
```powershell
# Generate sample data for testing
python servicenow_extraction_improved.py
```

## 📁 Project Structure

```
snow_extract/
├── src/                    # Source code modules
│   ├── network_incident_etl.py    # ETL transformations
│   ├── redact5.py                 # PII redaction
│   └── config_manager.py          # Configuration management
├── scripts/                # Executable scripts
│   ├── real_data_extraction.py    # Main extraction script
│   ├── test_servicenow_api.py    # API connection test
│   └── servicenow_extraction_improved.py  # Sample data generator
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

### Test API Connection
```powershell
python scripts\test_servicenow_api.py
```

### Validate Sample Data
```powershell
python servicenow_extraction_improved.py
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
