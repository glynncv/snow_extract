"""
PII Redaction Patterns
=====================

Regular expression patterns for detecting PII.
"""

# Common PII patterns
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
SSN_PATTERN = r'\b\d{3}-?\d{2}-?\d{4}\b'
IP_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
NAME_PATTERN = r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b'  # Simple name pattern
