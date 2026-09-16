# AI Prompt Log

This document logs the AI-assisted research and development prompts used during the design and implementation of the SEC EDGAR 10-K Data Automation and PDF Generation Service.

---

## Prompt 1: SEC EDGAR API Mechanics & Regulatory Constraints
**Prompt**:
> "I'm building an automated ingestion pipeline in Python to pull the latest 10-K annual reports from the SEC EDGAR API. What are the strict technical constraints regarding the User-Agent header, rate-limiting rules, CIK formatting, and how do SEC archive URLs map accession numbers to primary documents?"

**Key Takeaways & Implementation**:
- **User-Agent Header**: SEC enforces a custom header format: `Sample Company Name AdminContact@<sample company domain>.com`. Failure to provide this results in immediate HTTP 403 Forbidden.
- **Rate-Limiting**: Capped at 10 requests per second. Implemented a 0.15s pacing delay (~6.6 req/s) with exponential backoff on HTTP 429 (`Retry-After`).
- **CIK & Archive Schema**: Submissions JSON requires 10-digit zero-padded CIK (`CIK0000320193.json`), while archive URLs use unpadded CIKs and strip hyphens from accession numbers (`/Archives/edgar/data/{cik}/{accession_clean}/{primary_doc}`).
- **Form Filtering**: Targeted `form == "10-K"` specifically to ignore `10-K/A` (amendments).

---

## Prompt 2: iXBRL Rendering & Relative Asset Resolution
**Prompt**:
> "Modern SEC 10-K filings are Inline XBRL (iXBRL) HTML documents with embedded financial tables and relative links to images, charts, and stylesheets. When saving the HTML locally, these relative assets break. How can we ensure all assets resolve properly during HTML-to-PDF conversion, and what is the best rendering engine in Python for complex financial tables?"

**Key Takeaways & Implementation**:
- **Base URL Injection**: Dynamically injected a `<base href="{archive_base_url}">` tag into the HTML `<head>`. When rendered, the browser engine automatically resolves all relative asset paths against the SEC archive server.
- **Rendering Engine Evaluation**: Pure Python libraries (`xhtml2pdf`, `reportlab`) fail to properly parse modern CSS3/iXBRL tables. Headless Chromium/Microsoft Edge (`--headless=new`, `--print-to-pdf`, `--run-all-compositor-stages-before-draw`) was selected for 100% standard-compliant, pixel-perfect financial report rendering.

---

## Prompt 3: Modular Architecture & Dynamic Parameterization
**Prompt**:
> "I want to structure this into a clean, modular package under `src/` with a root entrypoint `main.py`. The design must be fully parameterizable so that no code changes are required when target companies or variables change. How should we implement dynamic CIK resolution across all public companies using SEC's `company_tickers.json` alongside CLI and environment variable overrides?"

**Key Takeaways & Implementation**:
- **Separation of Concerns**:
  - `src/config.py`: Centralized configuration, endpoints, and environment variable fallbacks.
  - `src/sec_client.py`: Network client with session pooling, pacing delay, and HTTP 429 retries.
  - `src/converter.py`: Cross-platform headless browser discovery and execution.
  - `src/service.py`: Business logic (dynamic CIK lookup, filing manifest extraction, base href injection).
  - `main.py`: Root runner with `argparse` CLI.
- **Dynamic Resolution**: Implemented `resolve_cik()` querying SEC's live index of 10,000+ public companies, allowing any company or ticker (e.g. `NVDA`, `TSLA`, `MSFT`) to be processed on the fly without code changes.

---

## Prompt 4: Headless Containerization (Docker)
**Prompt**:
> "How should we write a production Dockerfile based on `python:3.11-slim` that installs headless Chromium and standard system fonts so the PDF conversion runs reproducibly without requiring a display server (X11)?"

**Key Takeaways & Implementation**:
- Created a multi-stage `Dockerfile` installing `chromium`, `fonts-liberation`, and `fonts-dejavu-core` for accurate typography rendering.
- Configured CLI flags (`--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`) to prevent memory and permission issues in containerized environments.
- Added volume mounting to `/app/output` so generated PDFs persist directly to the host filesystem.
