"""Parser for Hetzner Online invoices."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class HetznerParser(VendorParser):
    vendor_name = "Hetzner"

    def can_parse(self, text: str) -> bool:
        return "Hetzner" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Hetzner"
        r.vendor_country = "DE"
        r.currency = "EUR"
        r.category_account = 6810
        r.category_name = "Informatik-Infrastruktur"

        # Swiss VAT number
        m = re.search(r"(CHE[\-\d.]+\s*MWST)", text)
        if m:
            r.vat_number = m.group(1).strip()

        # Invoice number: "Invoice no.: XXXXXXXXXXXX"
        m = re.search(r"Invoice no\.:\s*(\S+)", text)
        if m:
            r.invoice_number = m.group(1)

        # Invoice date: "Invoice date: 01/01/2026" (DD/MM/YYYY)
        m = re.search(r"Invoice date:\s*(\d{2}/\d{2}/\d{4})", text)
        if m:
            parts = m.group(1).split("/")
            r.date = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Service period: "12/2025"
        m = re.search(r"Period\s+Total.*?\n.*?(\d{2}/\d{4})", text, re.DOTALL)
        if m:
            r.period = m.group(1)

        # Project name for description
        m = re.search(r'Project\s+"([^"]+)"', text)
        if m:
            r.description = f"Hetzner Cloud - Project \"{m.group(1)}\""
        else:
            r.description = "Hetzner Cloud services"

        # Total (incl VAT): last "Total" line with €
        # Look for "Amount due: € 8.11" which is the final gross
        m = re.search(r"Amount due:\s*€\s*([0-9,]+\.\d{2})", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))

        # Net: "Total (excl. VAT)" from summary — first occurrence in the tax table
        # Tax rate line: "8.1 % € 7.50 € 0.61 € 8.11"
        m = re.search(r"(\d+\.?\d*)\s*%\s*€\s*([0-9,]+\.\d{2})\s*€\s*([0-9,]+\.\d{2})\s*€\s*([0-9,]+\.\d{2})", text)
        if m:
            r.vat_rate = Decimal(m.group(1))
            r.amount_net = Decimal(m.group(2).replace(",", ""))
            r.vat_amount = Decimal(m.group(3).replace(",", ""))

        return r
