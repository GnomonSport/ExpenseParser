"""Pydantic Expense model — the core record for every processed document."""

import datetime as _dt
import hashlib
import uuid
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ExtractionMethod(str, Enum):
    PDF_TEXT = "pdf_text"
    OCR = "ocr"
    AI = "ai"
    MANUAL = "manual"


class ExpenseStatus(str, Enum):
    PROCESSED = "processed"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"


class Expense(BaseModel):
    """A single expense record extracted from a document."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    file_path: str
    file_hash: str
    vendor: str = ""
    vendor_country: str = ""
    invoice_number: str = ""
    receipt_number: str = ""
    date: Optional[_dt.date] = None
    period: str = ""
    description: str = ""
    amount_gross: Decimal
    amount_net: Decimal = Decimal("0")
    currency: str = "USD"
    vat_rate: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    vat_number: str = ""
    category_account: Optional[int] = None
    category_name: str = ""
    labels: list[str] = Field(default_factory=list)
    notes: str = ""
    context_files: list[str] = Field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.PDF_TEXT
    extraction_confidence: float = 1.0
    processed_at: _dt.datetime = Field(default_factory=_dt.datetime.now)
    status: ExpenseStatus = ExpenseStatus.PROCESSED

    model_config = {"json_encoders": {Decimal: str, _dt.date: str, _dt.datetime: str}}


def file_hash(path: str | Path) -> str:
    """SHA-256 hash of a file for deduplication."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
