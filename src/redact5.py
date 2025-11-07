"""
PII Redaction Utility
===================

Provides functions for redacting personally identifiable information (PII)
from text data and hashing sensitive identifiers.
"""

import re
import hashlib
import pandas as pd
import logging
from typing import Union, List

logger = logging.getLogger(__name__)

# Common PII patterns
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
SSN_PATTERN = r'\b\d{3}-?\d{2}-?\d{4}\b'
IP_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
NAME_PATTERN = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'  # Simple name pattern

def redact_text(text_series: Union[pd.Series, str], redaction_char: str = 'X') -> Union[pd.Series, str]:
    """
    Redact PII from text data
    
    Args:
        text_series: Pandas Series or string containing text to redact
        redaction_char: Character to use for redaction
        
    Returns:
        Redacted text with PII replaced
    """
    if isinstance(text_series, str):
        return _redact_single_text(text_series, redaction_char)
    elif isinstance(text_series, pd.Series):
        return text_series.apply(lambda x: _redact_single_text(str(x), redaction_char))
    else:
        raise ValueError("Input must be string or pandas Series")

def _redact_single_text(text: str, redaction_char: str = 'X') -> str:
    """
    Redact PII from a single text string
    
    Args:
        text: Text to redact
        redaction_char: Character to use for redaction
        
    Returns:
        Redacted text
    """
    if not isinstance(text, str) or text.lower() in ['nan', 'none', '']:
        return text
    
    redacted = text
    
    # Redact email addresses
    redacted = re.sub(EMAIL_PATTERN, '[EMAIL_REDACTED]', redacted)
    
    # Redact phone numbers
    redacted = re.sub(PHONE_PATTERN, '[PHONE_REDACTED]', redacted)
    
    # Redact SSNs
    redacted = re.sub(SSN_PATTERN, '[SSN_REDACTED]', redacted)
    
    # Redact IP addresses (but keep network context)
    redacted = re.sub(IP_PATTERN, '[IP_ADDRESS]', redacted)
    
    # Redact potential names (basic pattern - may need refinement)
    # This is conservative to avoid false positives
    redacted = re.sub(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', '[NAME_REDACTED]', redacted)
    
    # Redact specific building/floor details while keeping general location
    redacted = re.sub(r'-Floor-\d+', '-[FLOOR_REDACTED]', redacted)
    redacted = re.sub(r'Room\s+\d+', 'Room [REDACTED]', redacted)
    
    return redacted

def hash_id(identifier: Union[str, pd.Series], salt: str = "snow_extract_2025") -> Union[str, pd.Series]:
    """
    Hash sensitive identifiers for anonymization
    
    Args:
        identifier: ID(s) to hash
        salt: Salt to add to hash for security
        
    Returns:
        Hashed identifier(s)
    """
    if isinstance(identifier, str):
        return _hash_single_id(identifier, salt)
    elif isinstance(identifier, pd.Series):
        return identifier.apply(lambda x: _hash_single_id(str(x), salt))
    else:
        raise ValueError("Input must be string or pandas Series")

def _hash_single_id(identifier: str, salt: str) -> str:
    """
    Hash a single identifier
    
    Args:
        identifier: ID to hash
        salt: Salt for hashing
        
    Returns:
        Hashed ID
    """
    if not isinstance(identifier, str) or identifier.lower() in ['nan', 'none', '']:
        return identifier
    
    # Create SHA-256 hash with salt
    hash_input = f"{salt}_{identifier}".encode('utf-8')
    hash_object = hashlib.sha256(hash_input)
    
    # Return first 12 characters of hex digest for readability
    return f"HASH_{hash_object.hexdigest()[:12].upper()}"

def redact_dataframe_columns(df: pd.DataFrame, 
                           text_columns: List[str] = None,
                           id_columns: List[str] = None,
                           drop_columns: List[str] = None) -> pd.DataFrame:
    """
    Comprehensively redact PII from a DataFrame
    
    Args:
        df: DataFrame to redact
        text_columns: Columns containing text to redact
        id_columns: Columns containing IDs to hash
        drop_columns: Columns to completely remove
        
    Returns:
        Redacted DataFrame
    """
    df_redacted = df.copy()
    
    # Default column lists if not provided
    if text_columns is None:
        text_columns = ['short_description', 'description', 'work_notes', 'comments']
    
    if id_columns is None:
        id_columns = ['number', 'sys_id', 'caller_id']
    
    if drop_columns is None:
        drop_columns = ['caller_id', 'opened_by', 'resolved_by', 'assigned_to']
    
    # Redact text columns
    for col in text_columns:
        if col in df_redacted.columns:
            logger.info(f"Redacting text in column: {col}")
            df_redacted[col] = redact_text(df_redacted[col])
    
    # Hash ID columns
    for col in id_columns:
        if col in df_redacted.columns and col not in drop_columns:
            logger.info(f"Hashing IDs in column: {col}")
            df_redacted[f"{col}_hash"] = hash_id(df_redacted[col])
    
    # Drop sensitive columns
    columns_to_drop = [col for col in drop_columns if col in df_redacted.columns]
    if columns_to_drop:
        logger.info(f"Dropping columns: {columns_to_drop}")
        df_redacted.drop(columns=columns_to_drop, inplace=True)
    
    logger.info(f"PII redaction complete. Processed {len(df_redacted)} rows.")
    return df_redacted

def validate_redaction(df_original: pd.DataFrame, df_redacted: pd.DataFrame) -> dict:
    """
    Validate that redaction was successful
    
    Args:
        df_original: Original DataFrame before redaction
        df_redacted: DataFrame after redaction
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'email_count_original': 0,
        'email_count_redacted': 0,
        'phone_count_original': 0,
        'phone_count_redacted': 0,
        'redaction_successful': False
    }
    
    # Count emails in original vs redacted
    for col in df_original.select_dtypes(include=['object']).columns:
        if col in df_original.columns:
            original_text = ' '.join(df_original[col].astype(str))
            validation_results['email_count_original'] += len(re.findall(EMAIL_PATTERN, original_text))
            validation_results['phone_count_original'] += len(re.findall(PHONE_PATTERN, original_text))
    
    for col in df_redacted.select_dtypes(include=['object']).columns:
        if col in df_redacted.columns:
            redacted_text = ' '.join(df_redacted[col].astype(str))
            validation_results['email_count_redacted'] += len(re.findall(EMAIL_PATTERN, redacted_text))
            validation_results['phone_count_redacted'] += len(re.findall(PHONE_PATTERN, redacted_text))
    
    # Check if redaction was successful
    validation_results['redaction_successful'] = (
        validation_results['email_count_redacted'] == 0 and
        validation_results['phone_count_redacted'] == 0
    )
    
    logger.info(f"Redaction validation: {validation_results}")
    return validation_results
