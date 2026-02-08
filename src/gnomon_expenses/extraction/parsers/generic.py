"""Generic fallback parser — tries common patterns for unrecognized documents."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class GenericParser(VendorParser):
    vendor_name = "Unknown"

    def can_parse(self, text: str) -> bool:
        # Always returns True as the last-resort parser
        return True

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.confidence = 0.3

        # Try to find an amount (look for currency symbols)
        for pattern, currency in [
            (r"(?:Total|Amount|TOTAL)\s*[:.]?\s*(?:CHF|Fr\.?)\s*([0-9,]+\.\d{2})", "CHF"),
            (r"(?:Total|Amount|TOTAL)\s*[:.]?\s*€\s*([0-9,]+\.\d{2})", "EUR"),
            (r"(?:Total|Amount|TOTAL)\s*[:.]?\s*\$([0-9,]+\.\d{2})", "USD"),
            (r"\$([0-9,]+\.\d{2})\s+paid", "USD"),
            (r"€\s*([0-9,]+\.\d{2})", "EUR"),
            (r"CHF\s*([0-9,]+\.\d{2})", "CHF"),
            (r"\$([0-9,]+\.\d{2})", "USD"),
        ]:
            m = re.search(pattern, text)
            if m:
                r.amount_gross = Decimal(m.group(1).replace(",", ""))
                r.amount_net = r.amount_gross
                r.currency = currency
                break

        if r.amount_gross == Decimal("0"):
            return None

        # Try to find a date
        # DD/MM/YYYY
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
        if m:
            r.date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        else:
            # Month DD, YYYY
            m = re.search(r"(\w+ \d{1,2}, \d{4})", text)
            if m:
                from datetime import datetime
                try:
                    dt = datetime.strptime(m.group(1), "%B %d, %Y")
                    r.date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # Try to find invoice/receipt number
        m = re.search(r"(?:Invoice|Receipt)\s*(?:number|no\.?|#)\s*[:.]?\s*(\S+)", text, re.IGNORECASE)
        if m:
            r.invoice_number = m.group(1)

        r.description = "Unknown document — needs manual review"
        r.vendor = "Unknown"

        return r
