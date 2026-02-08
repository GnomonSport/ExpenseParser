"""Parser for Anomaly (opencode) receipts via Stripe."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class AnomalyParser(VendorParser):
    vendor_name = "Anomaly"

    def can_parse(self, text: str) -> bool:
        return "Anomaly" in text and "anoma.ly" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Anomaly"
        r.vendor_country = "US"
        r.currency = "USD"
        r.category_account = 6820
        r.category_name = "Informatik-Dienstleistungen"
        r.description = "opencode credits"
        r.vat_rate = Decimal("0")
        r.vat_amount = Decimal("0")

        # Invoice number: e.g. "XXXXXXXX 0001"
        m = re.search(r"Invoice number\s+(\S+\s+\d+)", text)
        if m:
            r.invoice_number = m.group(1).strip()

        # Receipt number: e.g. "0000 0000"
        m = re.search(r"Receipt number\s+([\d\s]+)", text)
        if m:
            r.receipt_number = m.group(1).strip()

        # Date: "Date paid January 22, 2026"
        m = re.search(r"Date paid\s+(\w+ \d{1,2}, \d{4})", text)
        if m:
            from datetime import datetime
            try:
                dt = datetime.strptime(m.group(1), "%B %d, %Y")
                r.date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Total amount: "$21.23 paid on ..."
        m = re.search(r"\$([0-9,]+\.\d{2})\s+paid on", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))
            r.amount_net = r.amount_gross  # No VAT for foreign service

        return r
