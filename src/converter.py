"""
HTML to PDF Conversion Engine.

Renders SEC HTML filing documents into high-fidelity PDF documents using
cross-platform headless Chromium/Edge browser execution.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


class PDFConverter:
    """Converts HTML files to PDF using a headless browser engine."""

    def __init__(self, browser_path: Optional[str] = None) -> None:
        self.browser_path = self._find_browser_executable(browser_path)

    @staticmethod
    def _find_browser_executable(custom_path: Optional[str] = None) -> str:
        """
        Locates a valid Chrome, Edge, or Chromium executable across
        Windows, Linux, macOS, or Docker environments.
        """
        if custom_path and Path(custom_path).is_file():
            return custom_path

        # Check environment variable overrides (common in CI/CD and Docker)
        env_browser = os.getenv("CHROME_BIN") or os.getenv("BROWSER_PATH")
        if env_browser and Path(env_browser).is_file():
            return env_browser

        system = platform.system()
        candidates: List[str] = []

        if system == "Windows":
            candidates = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
        elif system == "Darwin":  # macOS
            candidates = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        else:  # Linux / Docker
            candidates = [
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/msedge",
                "/snap/bin/chromium",
            ]

        # Check PATH
        for bin_name in ["chromium", "chromium-browser", "google-chrome", "chrome", "msedge"]:
            which_path = shutil.which(bin_name)
            if which_path:
                candidates.append(which_path)

        for path in candidates:
            if path and Path(path).is_file():
                return path

        raise RuntimeError(
            "Could not locate Google Chrome, Microsoft Edge, or Chromium on this system. "
            "Please ensure a browser is installed, or set the CHROME_BIN environment variable."
        )

    def convert(self, html_path: Path, pdf_path: Path, timeout: int = 120) -> int:
        """
        Converts an HTML file to PDF via headless browser printing.
        Returns the generated PDF file size in bytes.
        """
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.browser_path,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            f"--print-to-pdf={pdf_path.resolve()}",
            str(html_path.resolve()),
        ]

        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)

        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError(f"PDF creation failed or output file is empty: {pdf_path}")

        return pdf_path.stat().st_size
