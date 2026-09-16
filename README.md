# SEC EDGAR 10-K Report Fetcher & PDF Converter

A production-grade Python service developed for Quartr's Data Automation team. It automatically discovers and fetches the latest **Form 10-K annual report** from the **U.S. Securities and Exchange Commission (SEC) EDGAR API** and transforms it into a high-fidelity **PDF document**.

### Default Target Companies
- Apple (`AAPL`)
- Meta (`META`)
- Alphabet (`GOOGL`)
- Amazon (`AMZN`)
- Netflix (`NFLX`)
- Goldman Sachs (`GS`)

---

## 1. Project Structure

The project uses a clean package structure with a root runner script:

```
quartr test/
├── main.py             # Root runner & fully parameterized Command-Line Interface (CLI)
├── requirements.txt    # Project dependencies (requests>=2.31.0)
├── Dockerfile          # Containerized runtime with Chromium pre-installed
├── .dockerignore       # Docker build exclusions
├── .gitignore          # Git exclusions for outputs and caches
├── README.md           # Instructions on how to run and configure the service
├── AI_PROMPT_LOG.md    # Required prompt log documenting AI usage
├── src/                # Core Python package
│   ├── __init__.py     # Package exports
│   ├── config.py       # Centralized settings, endpoints, and environment variables
│   ├── sec_client.py   # SEC HTTP client (rate-limiting, HTTP 429 retries, headers)
│   ├── converter.py    # Headless browser HTML-to-PDF rendering engine
│   └── service.py      # Core business logic (dynamic CIK resolution, 10-K discovery, base href injection)
└── output/             # Output folder for generated HTML, PDF, and metadata
    ├── Apple/
    ├── Meta/
    ├── Alphabet/
    ├── Amazon/
    ├── Netflix/
    └── Goldman_Sachs/
```

---

## 2. Dynamic Parameterization: Zero Code Changes Needed

The service is built so that **no code modifications are required** when parameters or target companies change:

- **Adding or changing companies**: Any public company (e.g. `Microsoft`, `Nvidia`, `Tesla`, `NVDA`, `TSLA`) is resolved dynamically via SEC EDGAR's live `company_tickers.json` directory.
- **Custom Output Directory**: Target destination can be set via `--output-dir` or the `OUTPUT_DIR` environment variable.
- **Alternative SEC Forms**: Change `--form` from `10-K` to `10-Q` (quarterly reports) or `8-K` without modifying code.
- **Configurable SEC User-Agent & Rate Limits**: Customizable via CLI arguments or environment variables.

---

## 3. Installation & Setup

### Prerequisites
- **Python**: 3.9+
- **Browser Engine**: Microsoft Edge or Google Chrome / Chromium (pre-installed on Windows 10/11, macOS, and standard Linux distributions).
- Alternatively, run via **Docker** (see Section 5) which requires no local Python or browser installation.

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. How to Run (Local Python)

Run the entrypoint script located in the root directory:

### A. Run Default Batch (All 6 Assignment Companies)
```bash
python main.py
```

### B. Run with Different Companies or Tickers
Pass company names, tickers, or raw CIK numbers via `-c` or `--companies`:
```bash
python main.py --companies Apple Meta Amazon
python main.py --companies NVDA MSFT TSLA
```

### C. Run with Custom Output Directory
```bash
python main.py --output-dir ./my_reports
```

### D. Fetch Alternative Forms (e.g. Quarterly 10-Q)
```bash
python main.py --form 10-Q --companies Apple Netflix
```

### E. Run with Environment Variables
All parameters can also be controlled through environment variables:
```bash
export TARGET_COMPANIES="Apple,Meta,Alphabet"
export OUTPUT_DIR="./filings"
export FORM_TYPE="10-K"
python main.py
```

### CLI Arguments Reference

| Flag | Short | Default | Description |
| :--- | :---: | :---: | :--- |
| `--companies` | `-c` | 6 target companies | Space-separated company names, tickers, or CIKs |
| `--output-dir` | `-o` | `output` | Destination directory for HTML, PDF, and metadata |
| `--form` | `-f` | `10-K` | SEC Form type (e.g., `10-K`, `10-Q`, `8-K`) |
| `--user-agent` | `-u` | `QuartrDataAutomation applicant@quartr.com` | Compliant SEC EDGAR User-Agent string |
| `--rate-limit-delay` | | `0.15` | Pacing delay between HTTP calls (seconds) |
| `--browser-path` | | Auto-detected | Explicit path to Chrome or Edge binary |

---

## 5. Running with Docker

A production `Dockerfile` is included that packages Python and headless Chromium with all necessary font packages.

### Build Docker Image
```bash
docker build -t quartr-sec-automation .
```

### Run Default Batch in Docker
Mount the local `output` directory so the generated PDFs are saved to your host machine:

**Windows (PowerShell):**
```powershell
docker run --rm -v ${PWD}/output:/app/output quartr-sec-automation
```

**Linux / macOS:**
```bash
docker run --rm -v $(pwd)/output:/app/output quartr-sec-automation
```

### Run Docker with Custom Parameters
```bash
docker run --rm -v ${PWD}/output:/app/output quartr-sec-automation --companies NVDA TSLA MSFT
```

---

## 6. Programmatic Python API (For Other Quartr Teams)

Internal Quartr services, Airflow DAGs, or background workers can import and invoke the service directly:

```python
from src.service import SecReportService
from pathlib import Path

# Initialize service
service = SecReportService()

# 1. Process a single company
result = service.process_company("Apple", output_dir=Path("output"), form_type="10-K")
print("PDF generated at:", result["pdf_path"])

# 2. Process a batch of companies
batch_results = service.process_all(["Apple", "Meta", "Amazon"], output_dir=Path("output"))
for res in batch_results:
    print(res["company"], res["pdf_path"])
```

---

## 7. SEC EDGAR Compliance & Technical Decisions

1. **Mandatory User-Agent**: The SEC requires a custom User-Agent in the format `Sample Company Name AdminContact@<sample company domain>.com`. Unidentified requests return **HTTP 403 Forbidden**. The service enforces this automatically.
2. **Rate Limiting**: SEC caps traffic at **10 requests per second**. The client paces calls with a 0.15s delay (~6.6 req/s) and implements exponential backoff if an **HTTP 429** is encountered.
3. **iXBRL Asset Resolution**: SEC 10-K filings contain relative links to logos, charts, and stylesheets. The service injects `<base href="...">` into the HTML `<head>` before rendering, ensuring all external assets load accurately.
4. **Headless Browser Rendering**: Headless Chromium/Edge (`--headless=new`, `--print-to-pdf`) guarantees pixel-perfect layout and table rendering for complex financial disclosures.
