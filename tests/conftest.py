"""
Shared pytest fixtures and utilities for test suite.
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
import os
from datetime import datetime, timedelta

from snow_analytics.core.loaders import generate_sample_data, load_incidents
from snow_analytics.core.transform import transform_incidents
from snow_analytics.core.config import Config
from snow_analytics.connectors.api import ServiceNowAPI


@pytest.fixture
def sample_incidents_df():
    """Basic sample incident DataFrame (in-memory, no cleanup needed)."""
    return generate_sample_data(num_records=20, template='network')


@pytest.fixture
def transformed_incidents_df(sample_incidents_df):
    """Pre-transformed DataFrame with all columns (in-memory)."""
    return transform_incidents(sample_incidents_df)


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs (auto-deletes after test)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
    # Directory automatically deleted here


@pytest.fixture
def api_credentials():
    """Load API credentials from env/config (returns None if unavailable)."""
    config = Config()
    
    instance_url = (
        config.get('servicenow.instance_url') or 
        os.getenv('SNOW_INSTANCE_URL')
    )
    username = (
        config.get('servicenow.username') or 
        os.getenv('SNOW_USERNAME')
    )
    password = (
        config.get('servicenow.password') or 
        os.getenv('SNOW_PASSWORD')
    )
    
    if all([instance_url, username, password]):
        return {
            'instance_url': instance_url,
            'username': username,
            'password': password
        }
    return None


@pytest.fixture
def servicenow_api(api_credentials):
    """Real ServiceNow API client (skips if credentials unavailable)."""
    if api_credentials is None:
        pytest.skip("ServiceNow credentials not available")
    
    api = ServiceNowAPI(
        instance_url=api_credentials['instance_url'],
        username=api_credentials['username'],
        password=api_credentials['password']
    )
    
    if not api.connect():
        pytest.skip("Failed to connect to ServiceNow API")
    
    return api


def verify_and_cleanup(file_path):
    """
    Helper function to verify file exists and then delete it.
    
    Args:
        file_path: Path to file to verify and delete
    """
    path = Path(file_path)
    if path.exists():
        # Verify it's a file (not directory)
        assert path.is_file(), f"Expected file but got directory: {file_path}"
        # Delete it
        path.unlink()
        assert not path.exists(), f"File still exists after deletion: {file_path}"

