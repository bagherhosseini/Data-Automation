"""
Command Line Interface (CLI) Entrypoint.

Provides a fully parameterizable CLI for the SEC EDGAR Report Fetcher & PDF Converter.
All variables (companies, output directory, form type, rate limits, user agent)
can be changed dynamically via CLI arguments or environment variables without
requiring any source code modifications.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from src.config import (
    DEFAULT_COMPANIES,
    DEFAULT_OUTPUT_DIR,
    FORM_TYPE,
    RATE_LIMIT_DELAY,
    SEC_USER_AGENT,
)
from src.converter import PDFConverter
from src.sec_client import SecClient
from src.service import SecReportService


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments with sensible defaults from config."""
    parser = argparse.ArgumentParser(
        description="Quartr Data Automation - SEC EDGAR Report Fetcher & PDF Converter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--companies",
        nargs="+",
        default=DEFAULT_COMPANIES,
        help="List of company names, stock tickers, or CIK numbers to process.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for downloaded reports and PDFs.",
    )
    parser.add_argument(
        "-f",
        "--form",
        type=str,
        default=FORM_TYPE,
        help="SEC Form type to fetch (e.g., 10-K, 10-Q, 8-K).",
    )
    parser.add_argument(
        "-u",
        "--user-agent",
        type=str,
        default=SEC_USER_AGENT,
        help="SEC EDGAR compliant User-Agent string ('Name Contact@domain.com').",
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=RATE_LIMIT_DELAY,
        help="Pacing delay in seconds between SEC HTTP requests.",
    )
    parser.add_argument(
        "--browser-path",
        type=str,
        default=None,
        help="Optional explicit path to Chrome or Edge executable.",
    )

    return parser.parse_args(args)


def main(argv: Optional[List[str]] = None) -> int:
    """Runs the SEC Report Fetcher CLI."""
    args = parse_args(argv)

    client = SecClient(
        user_agent=args.user_agent,
        rate_limit_delay=args.rate_limit_delay,
    )
    converter = PDFConverter(browser_path=args.browser_path)

    service = SecReportService(client=client, converter=converter)

    try:
        results = service.process_all(
            companies=args.companies,
            output_dir=args.output_dir,
            form_type=args.form,
        )
        failures = sum(1 for r in results if not r.get("success"))
        return 1 if failures > 0 else 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
