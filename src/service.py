"""
SEC Filing & Report Automation Service.

Provides domain logic for dynamic company CIK resolution, 10-K/filing metadata extraction,
HTML downloading with asset resolution, and PDF generation orchestration.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    DEFAULT_COMPANIES,
    DEFAULT_OUTPUT_DIR,
    FORM_TYPE,
    KNOWN_CIK_CATALOG,
    SEC_ARCHIVES_URL,
    SEC_SUBMISSIONS_URL,
    SEC_TICKERS_URL,
)
from .converter import PDFConverter
from .sec_client import SecClient


class SecReportService:
    """Core service for fetching SEC reports and converting them to PDF."""

    def __init__(
        self,
        client: Optional[SecClient] = None,
        converter: Optional[PDFConverter] = None,
    ) -> None:
        self.client = client or SecClient()
        self.converter = converter or PDFConverter()
        self._ticker_cache: Optional[Dict[str, Any]] = None

    def resolve_cik(self, company_identifier: str) -> str:
        """
        Resolves a company name, ticker, or numeric CIK to a 10-digit zero-padded CIK.
        
        Resolution Strategy:
        1. Known CIK catalog (guarantees instant, zero-network resolution for core targets).
        2. Direct numeric CIK (pads to 10 digits).
        3. Dynamic query against SEC's live company_tickers index (~10,000+ public companies),
           allowing ANY public company (e.g. NVDA, TSLA, MSFT) to be resolved with zero code changes.
        """
        clean = company_identifier.strip()
        if not clean:
            raise ValueError("Company identifier cannot be empty.")

        # 1. Check known catalog
        upper_key = clean.upper()
        if upper_key in KNOWN_CIK_CATALOG:
            return KNOWN_CIK_CATALOG[upper_key]

        # 2. Check if already a numeric CIK
        if clean.isdigit():
            return clean.zfill(10)

        # 3. Dynamic lookup against SEC company_tickers dataset
        if self._ticker_cache is None:
            data = self.client.get(SEC_TICKERS_URL, is_json=True)
            self._ticker_cache = data

        # Check ticker first, then check company title
        for entry in self._ticker_cache.values():
            if entry.get("ticker", "").upper() == upper_key:
                return str(entry["cik_str"]).zfill(10)

        for entry in self._ticker_cache.values():
            if upper_key in entry.get("title", "").upper():
                return str(entry["cik_str"]).zfill(10)

        raise ValueError(
            f"Could not resolve company identifier: '{company_identifier}'. "
            f"Please verify the company name or provide a stock ticker."
        )

    def get_latest_filing_metadata(
        self,
        cik: str,
        form_type: str = FORM_TYPE,
    ) -> Dict[str, str]:
        """
        Queries SEC EDGAR submissions API to find the latest filing of the specified form type.
        (Defaults to '10-K', but can be parameterized to '10-Q', '8-K', etc.)
        """
        cik_padded = cik.zfill(10)
        url = f"{SEC_SUBMISSIONS_URL}/CIK{cik_padded}.json"
        data = self.client.get(url, is_json=True)

        recent = data.get("filings", {}).get("recent", {})
        forms: List[str] = recent.get("form", [])

        target_idx: Optional[int] = None
        target_form = form_type.strip().upper()

        for idx, form in enumerate(forms):
            if form.strip().upper() == target_form:
                target_idx = idx
                break

        if target_idx is None:
            raise ValueError(f"No Form '{form_type}' report found for CIK {cik}.")

        accession_number = recent["accessionNumber"][target_idx]
        filing_date = recent["filingDate"][target_idx]
        report_date = recent["reportDate"][target_idx]
        primary_doc = recent["primaryDocument"][target_idx]

        # Construct SEC Archive URL:
        # SEC archive directories use unpadded CIKs and remove all hyphens from accession numbers
        cik_unpadded = str(int(cik))
        acc_clean = accession_number.replace("-", "")
        archive_base_url = f"{SEC_ARCHIVES_URL}/{cik_unpadded}/{acc_clean}/"
        document_url = f"{archive_base_url}{primary_doc}"

        return {
            "form": form_type,
            "accession_number": accession_number,
            "filing_date": filing_date,
            "report_date": report_date,
            "primary_document": primary_doc,
            "archive_base_url": archive_base_url,
            "document_url": document_url,
        }

    def download_filing_html(
        self,
        doc_url: str,
        archive_base_url: str,
        output_path: Path,
    ) -> int:
        """
        Downloads the primary filing HTML document and injects a <base href="...">
        tag so that relative image links, stylesheets, and charts resolve correctly.
        """
        raw_html = self.client.get(doc_url, is_json=False)

        # Inject base tag into <head> for asset resolution
        base_tag = f'<base href="{archive_base_url}">'
        head_match = re.search(r"<head[^>]*>", raw_html, re.IGNORECASE)
        if head_match:
            pos = head_match.end()
            modified_html = raw_html[:pos] + base_tag + raw_html[pos:]
        else:
            modified_html = f"<head>{base_tag}</head>" + raw_html

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(modified_html, encoding="utf-8")
        return output_path.stat().st_size

    def process_company(
        self,
        company: str,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        form_type: str = FORM_TYPE,
    ) -> Dict[str, Any]:
        """
        Processes a single company end-to-end:
        Resolves CIK -> Queries latest filing metadata -> Downloads HTML -> Converts to PDF.
        """
        print(f"\nProcessing {company}...")
        start_time = time.time()

        # 1. Resolve CIK dynamically
        cik = self.resolve_cik(company)
        print(f"  CIK: {cik}")

        # 2. Extract latest filing metadata
        meta = self.get_latest_filing_metadata(cik, form_type=form_type)
        print(f"  Latest {form_type}: Filing Date: {meta['filing_date']}, Period: {meta['report_date']}")
        print(f"  Document URL: {meta['document_url']}")

        # 3. Construct clean local file paths
        safe_name = re.sub(r"[^\w\-]", "_", company)
        company_folder = output_dir / safe_name
        clean_date = meta["report_date"].replace("-", "")
        html_file = company_folder / f"{safe_name}_{form_type}_{clean_date}.html"
        pdf_file = company_folder / f"{safe_name}_{form_type}_{clean_date}.pdf"

        # 4. Download HTML document
        print("  Downloading HTML...")
        html_size = self.download_filing_html(
            doc_url=meta["document_url"],
            archive_base_url=meta["archive_base_url"],
            output_path=html_file,
        )
        print(f"  Saved HTML: {html_file.name} ({html_size / (1024 * 1024):.2f} MB)")

        # 5. Convert HTML to PDF
        print("  Converting to PDF...")
        t_conv = time.time()
        pdf_size = self.converter.convert(html_path=html_file, pdf_path=pdf_file)
        conv_elapsed = time.time() - t_conv
        print(f"  Generated PDF: {pdf_file.name} ({pdf_size / (1024 * 1024):.2f} MB in {conv_elapsed:.1f}s)")

        total_elapsed = time.time() - start_time
        result = {
            "company": company,
            "cik": cik,
            "form": form_type,
            "filing_date": meta["filing_date"],
            "report_date": meta["report_date"],
            "document_url": meta["document_url"],
            "html_path": str(html_file),
            "pdf_path": str(pdf_file),
            "html_size_mb": round(html_size / (1024 * 1024), 2),
            "pdf_size_mb": round(pdf_size / (1024 * 1024), 2),
            "total_time_seconds": round(total_elapsed, 2),
            "success": True,
        }

        # Write per-company metadata JSON
        (company_folder / "metadata.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    def process_all(
        self,
        companies: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        form_type: str = FORM_TYPE,
    ) -> List[Dict[str, Any]]:
        """
        Executes the ingestion and PDF conversion pipeline for a list of companies.
        """
        targets = companies or DEFAULT_COMPANIES
        dest_dir = output_dir or DEFAULT_OUTPUT_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"SEC EDGAR {form_type} REPORT INGESTION & PDF CONVERSION")
        print(f"Companies: {', '.join(targets)}")
        print(f"Output Directory: {dest_dir.resolve()}")
        print("=" * 60)

        results: List[Dict[str, Any]] = []
        start_total = time.time()

        for comp in targets:
            try:
                res = self.process_company(comp, output_dir=dest_dir, form_type=form_type)
                results.append(res)
            except Exception as e:
                print(f"  [ERROR] Failed to process {comp}: {e}")
                results.append({
                    "company": comp,
                    "success": False,
                    "error": str(e),
                })

        success_count = sum(1 for r in results if r.get("success"))
        print("\n" + "=" * 60)
        print(f"COMPLETED: {success_count}/{len(targets)} succeeded in {time.time() - start_total:.1f}s")
        print(f"Output saved in: {dest_dir.resolve()}")
        print("=" * 60)

        return results
