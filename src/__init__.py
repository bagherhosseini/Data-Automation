"""
SEC EDGAR 10-K Data Automation Package.
"""

from .config import (
    DEFAULT_COMPANIES,
    DEFAULT_OUTPUT_DIR,
    FORM_TYPE,
    KNOWN_CIK_CATALOG,
    RATE_LIMIT_DELAY,
    SEC_USER_AGENT,
)
from .converter import PDFConverter
from .sec_client import SecClient
from .service import SecReportService

__all__ = [
    "DEFAULT_COMPANIES",
    "DEFAULT_OUTPUT_DIR",
    "FORM_TYPE",
    "KNOWN_CIK_CATALOG",
    "RATE_LIMIT_DELAY",
    "SEC_USER_AGENT",
    "PDFConverter",
    "SecClient",
    "SecReportService",
]
