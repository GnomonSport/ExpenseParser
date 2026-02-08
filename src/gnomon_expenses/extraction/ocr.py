"""Tier 2: OCR fallback using Tesseract for scanned PDFs."""

from pathlib import Path


def extract_text_ocr(path: str | Path) -> str:
    """Extract text from a scanned PDF via Tesseract OCR.

    Requires: pytesseract, Pillow, pdf2image (install with `pip install gnomon-expenses[ocr]`).
    """
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(str(path), dpi=300)
    pages = []
    for img in images:
        text = pytesseract.image_to_string(img, lang="eng+deu")
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)
