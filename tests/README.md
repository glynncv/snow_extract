# Test Suite Documentation

## Overview

Comprehensive test suite for the ServiceNow Analytics Toolkit. Tests cover all modules including core functionality, analysis, connectors, and reporting.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── test_config.py          # Configuration management tests
├── test_validators.py      # Data validation tests
├── test_loaders.py         # Data loading tests (existing)
├── test_transform.py       # ETL transformation tests (existing)
├── test_metrics.py        # Metrics and KPI calculation tests
├── test_quality.py         # Quality check tests
├── test_patterns.py        # Pattern detection tests
├── test_api.py             # ServiceNow API client tests (REAL API)
├── test_exporters.py       # Export utility tests
├── test_reports.py         # Report generation tests
├── test_integration.py     # End-to-end workflow tests
└── test_rca_generator.py   # RCA generation tests (existing)
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -e ".[dev]"
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=snow_analytics --cov-report=html

# Run specific test file
pytest tests/test_metrics.py

# Run specific test
pytest tests/test_metrics.py::test_calculate_sla_metrics

# Run with verbose output
pytest -v
```

### API Tests

API tests use **REAL ServiceNow API calls** (not mocked). They require valid credentials.

**Setup API Credentials:**

Create a `.env` file in the project root:
```
SNOW_INSTANCE_URL=https://your-instance.service-now.com
SNOW_USERNAME=your_username
SNOW_PASSWORD=your_password
```

Or set environment variables:
```bash
export SNOW_INSTANCE_URL=https://your-instance.service-now.com
export SNOW_USERNAME=your_username
export SNOW_PASSWORD=your_password
```

**Running API Tests:**

```bash
# Run only API tests (requires credentials)
pytest -m api

# Run all tests except API tests (skip if credentials unavailable)
pytest -m "not api"

# Run integration tests excluding API
pytest tests/test_integration.py -m "not api"
```

**Note:** API tests will automatically skip if credentials are not available, so tests can run without API access.

## Test Isolation & Cleanup

All tests are designed to be:
- **Isolated:** Each test is independent and can run in any order
- **Self-contained:** Tests create their own temporary data/files
- **Clean:** All temporary files and directories are deleted after verification

### Cleanup Pattern

Tests follow this pattern:
1. Create temporary files/directories
2. Execute test logic
3. Verify results
4. **Immediately delete** all test artifacts

Example:
```python
def test_export_to_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test.csv"
        export_to_csv(df, output_path)
        
        # Verify file exists and content
        assert output_path.exists()
        df_read = pd.read_csv(output_path)
        assert len(df_read) > 0
        
    # Directory automatically deleted here
```

## Test Coverage

### Unit Tests
- **Core Module:** Config, validators, loaders, transformers
- **Analysis Module:** Metrics, quality checks, pattern detection
- **Connectors Module:** ServiceNow API client (real API)
- **Reporting Module:** Exporters, report generators

### Integration Tests
- End-to-end workflows (Load → Transform → Analyze → Report)
- Module integration (Config + Load + Transform)
- API integration (Real API → Transform → Analyze)
- Cross-module functionality

## Test Data

Tests use:
- **Sample data generation:** `load_incidents('sample')` for consistent test data
- **Real API calls:** Actual ServiceNow API for API tests (with small limits)
- **Temporary files:** All file I/O uses `tempfile` for automatic cleanup

## Troubleshooting

### API Tests Skipping
If API tests are skipped:
- Check that credentials are set in `.env` or environment variables
- Verify credentials are valid
- Check network connectivity to ServiceNow instance

### Import Errors
If you see import errors:
```bash
# Install package in editable mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"
```

### Missing Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -e ".[dev]"
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:
- Non-API tests run without external dependencies
- API tests skip gracefully if credentials unavailable
- All tests clean up after themselves
- Coverage reports generated automatically

## Contributing

When adding new tests:
1. Follow existing test patterns
2. Use `tempfile` for file operations
3. Clean up all temporary files in `tearDown()` or use context managers
4. Mark API-dependent tests with `@pytest.mark.api`
5. Ensure tests are isolated and can run independently
6. Verify cleanup happens even if test fails

