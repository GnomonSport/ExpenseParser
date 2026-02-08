"""Parser for Infomaniak invoices."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class InfomaniakParser(VendorParser):
    vendor_name = "Infomaniak"

    def can_parse(self, text: str) -> bool:
        return "Infomaniak" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Infomaniak"
        r.vendor_country = "CH"
        r.currency = "CHF"
        r.category_account = 6850
        r.category_name = "Software-Abonnemente"

        # VAT number
        m = re.search(r"VAT number:\s*(CHE[\s\-\d.]+)", text)
        if m:
            r.vat_number = m.group(1).strip()

        # Invoice number: "Invoice NNNNNNN"
        m = re.search(r"Invoice\s+(\d+)", text)
        if m:
            r.invoice_number = m.group(1)

        # Date: "Date 01/02/2026" (DD/MM/YYYY)
        m = re.search(r"Date\s+(\d{2}/\d{2}/\d{4})", text)
        if m:
            parts = m.group(1).split("/")
            r.date = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Period from order line: "from DD/MM/YYYY ... to DD/MM/YYYY"
        m = re.search(r"from\s+(\d{2}/\d{2}/\d{4})\s+.*?to\s+(\d{2}/\d{2}/\d{4})", text)
        if m:
            r.period = f"{m.group(1)} - {m.group(2)}"

        # Description from order line: "kSuite" etc.
        m = re.search(r"kSuite\s*:\s*(\S+)", text)
        if m:
            r.description = f"kSuite ({m.group(1)})"
        else:
            r.description = "Infomaniak services"

        # VAT rate
        m = re.search(r"VAT\s+(\d+\.?\d*)%", text)
        if m:
            r.vat_rate = Decimal(m.group(1))

        # Total incl. VAT: "Total CHF incl. VAT 7.60"
        m = re.search(r"Total\s+CHF\s+incl\.\s+VAT\s+([0-9,]+\.\d{2})", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))

        # Net: "Price CHF ex. VAT 7.04"
        m = re.search(r"Price\s+CHF\s+ex\.\s+VAT\s+([0-9,]+\.\d{2})", text)
        if m:
            r.amount_net = Decimal(m.group(1).replace(",", ""))

        # VAT amount: "VAT 8.1% 0.56"
        m = re.search(r"VAT\s+\d+\.?\d*%\s+([0-9,]+\.\d{2})", text)
        if m:
            r.vat_amount = Decimal(m.group(1).replace(",", ""))

        return r
