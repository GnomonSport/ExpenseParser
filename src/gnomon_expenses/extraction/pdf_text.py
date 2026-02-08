"""Tier 1: Extract text from PDF using pdfplumber."""

from pathlib import Path

import pdfplumber


def extract_text(path: str | Path) -> str:
    """Extract all text from a PDF file. Returns empty string on failure."""
    try:
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except Exception:
        return ""
