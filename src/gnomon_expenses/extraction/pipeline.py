"""3-tier extraction pipeline: pdfplumber text -> OCR -> AI."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from gnomon_expenses.extraction.parsers.anomaly import AnomalyParser
from gnomon_expenses.extraction.parsers.anthropic import AnthropicParser
from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser
from gnomon_expenses.extraction.parsers.elevenlabs import ElevenLabsParser
from gnomon_expenses.extraction.parsers.generic import GenericParser
from gnomon_expenses.extraction.parsers.hetzner import HetznerParser
from gnomon_expenses.extraction.parsers.infomaniak import InfomaniakParser
from gnomon_expenses.extraction.parsers.namecheap import NamecheapParser
from gnomon_expenses.extraction.parsers.twilio import TwilioParser
from gnomon_expenses.extraction.pdf_text import extract_text
from gnomon_expenses.models.expense import (
    Expense,
    ExtractionMethod,
    ExpenseStatus,
    file_hash,
)

# Ordered list of parsers — specific vendors first, generic last
PARSERS: list[VendorParser] = [
    AnomalyParser(),
    AnthropicParser(),
    ElevenLabsParser(),
    InfomaniakParser(),
    HetznerParser(),
    TwilioParser(),
    NamecheapParser(),
    GenericParser(),  # fallback
]


def _parse_text(text: str) -> tuple[ParseResult | None, VendorParser | None]:
    """Try each parser in order until one succeeds."""
    for parser in PARSERS:
        if parser.can_parse(text):
            result = parser.parse(text)
            if result and result.amount_gross > 0:
                return result, parser
    return None, None


def process_pdf(path: str | Path) -> Expense | None:
    """Run the extraction pipeline on a single PDF. Returns an Expense or None."""
    path = Path(path)
    fhash = file_hash(path)

    # Tier 1: pdfplumber text extraction
    text = extract_text(path)
    extraction_method = ExtractionMethod.PDF_TEXT

    if not text.strip():
        # Tier 2: OCR fallback
        try:
            from gnomon_expenses.extraction.ocr import extract_text_ocr
            text = extract_text_ocr(path)
            extraction_method = ExtractionMethod.OCR
        except (ImportError, Exception):
            pass

    if not text.strip():
        # Tier 3: AI extraction
        try:
            from gnomon_expenses.extraction.ai_extract import extract_with_ai
            return extract_with_ai(path, fhash)
        except (ImportError, Exception):
            return None

    result, parser = _parse_text(text)
    if result is None:
        return None

    expense_date = None
    if result.date:
        try:
            expense_date = date.fromisoformat(result.date)
        except ValueError:
            pass

    return Expense(
        file_path=str(path),
        file_hash=fhash,
        vendor=result.vendor,
        vendor_country=result.vendor_country,
        invoice_number=result.invoice_number,
        receipt_number=result.receipt_number,
        date=expense_date,
        period=result.period,
        description=result.description,
        amount_gross=result.amount_gross,
        amount_net=result.amount_net,
        currency=result.currency,
        vat_rate=result.vat_rate,
        vat_amount=result.vat_amount,
        vat_number=result.vat_number,
        category_account=result.category_account,
        category_name=result.category_name,
        extraction_method=extraction_method,
        extraction_confidence=result.confidence,
        status=(
            ExpenseStatus.PROCESSED
            if result.confidence >= 0.7
            else ExpenseStatus.NEEDS_REVIEW
        ),
    )
