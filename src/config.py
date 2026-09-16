"""
Configuration and Environment Settings.

Defines default parameters, SEC EDGAR endpoints, and allows dynamic overrides
via environment variables or command-line arguments so that code never needs to be
modified when variables change.
"""

import os
from pathlib import Path
from typing import Dict, List

# SEC EDGAR requires a specific User-Agent format:
# Format: Sample Company Name AdminContact@<sample company domain>.com
SEC_USER_AGENT: str = os.getenv(
    "SEC_USER_AGENT",
    "QuartrDataAutomation applicant@quartr.com"
)

# Target companies list - can be overridden via TARGET_COMPANIES env var (comma-separated)
_env_companies = os.getenv("TARGET_COMPANIES")
DEFAULT_COMPANIES: List[str] = (
    [c.strip() for c in _env_companies.split(",") if c.strip()]
    if _env_companies
    else ["Apple", "Meta", "Alphabet", "Amazon", "Netflix", "Goldman Sachs"]
)

# Known CIK Fallback Catalog (Guarantees zero-network resilience for core target companies)
KNOWN_CIK_CATALOG: Dict[str, str] = {
    "APPLE": "0000320193",
    "AAPL": "0000320193",
    "META": "0001326801",
    "FACEBOOK": "0001326801",
    "ALPHABET": "0001652044",
    "GOOGLE": "0001652044",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "AMAZON": "0001018724",
    "AMZN": "0001018724",
    "NETFLIX": "0001065280",
    "NFLX": "0001065280",
    "GOLDMAN SACHS": "0000886982",
    "GOLDMAN": "0000886982",
    "GS": "0000886982",
}

# Default Output directory
DEFAULT_OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "output"))

# Default Form Type (e.g., 10-K annual report, 10-Q quarterly report)
FORM_TYPE: str = os.getenv("FORM_TYPE", "10-K")

# SEC Rate limit delay in seconds (SEC limit is 10 req/s, 0.15s gives safe ~6.6 req/s)
RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "0.15"))

# SEC EDGAR Endpoints
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
