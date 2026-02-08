"""Base class for vendor-specific receipt/invoice parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from gnomon_expenses.models.expense import Expense


class ParseResult:
    """Intermediate parse result before creating an Expense."""

    def __init__(self) -> None:
        self.vendor: str = ""
        self.vendor_country: str = ""
        self.invoice_number: str = ""
        self.receipt_number: str = ""
        self.date: str = ""  # ISO format YYYY-MM-DD
        self.period: str = ""
        self.description: str = ""
        self.amount_gross: Decimal = Decimal("0")
        self.amount_net: Decimal = Decimal("0")
        self.currency: str = "USD"
        self.vat_rate: Decimal = Decimal("0")
        self.vat_amount: Decimal = Decimal("0")
        self.vat_number: str = ""
        self.category_account: int | None = None
        self.category_name: str = ""
        self.confidence: float = 1.0


class VendorParser(ABC):
    """Base class all vendor parsers inherit from."""

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Return True if this parser recognizes the document text."""

    @abstractmethod
    def parse(self, text: str) -> ParseResult | None:
        """Extract structured data from recognized document text."""

    @property
    @abstractmethod
    def vendor_name(self) -> str:
        """Human-readable vendor name."""
