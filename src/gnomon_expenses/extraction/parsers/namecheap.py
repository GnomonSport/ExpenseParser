"""Parser for Namecheap order receipts."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class NamecheapParser(VendorParser):
    vendor_name = "Namecheap"

    def can_parse(self, text: str) -> bool:
        return "Namecheap" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Namecheap"
        r.vendor_country = "US"
        r.currency = "USD"
        r.category_account = 6840
        r.category_name = "Domänen und Hosting"
        r.vat_rate = Decimal("0")
        r.vat_amount = Decimal("0")

        # Order number
        m = re.search(r"Order\s*#\s*(\d+)", text)
        if m:
            r.invoice_number = m.group(1)

        # Order date: "2/1/2026 10:26:05 AM"
        m = re.search(r"Order Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})", text)
        if m:
            parts = m.group(1).split("/")
            r.date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

        # Domain names registered
        domains = re.findall(r"Domain Registration\s+\d+\s+\d+\s+year\s+\$[\d.]+\s+\$([\d.]+)\s*\n\s*(\S+)", text)
        if not domains:
            # Try alternative: domain names appear after "REGISTER" lines
            domains = re.findall(r"REGISTER\s+Domain Registration\s+\d+\s+\d+\s+year\s+\$[\d.]+\s+\$([\d.]+)\s*\n\s*(\S+\.[\w]+)", text)
        if not domains:
            # Simpler: find domain names
            domain_names = re.findall(r"(\w[\w-]+\.(?:com|pro|net|org|io|ch|dev))", text)
            if domain_names:
                r.description = f"Domain registration: {', '.join(domain_names)}"
            else:
                r.description = "Namecheap domain services"
        else:
            names = [d[1] for d in domains]
            r.description = f"Domain registration: {', '.join(names)}"

        # Total: "TOTAL $15.66" or "Final Cost : $15.66"
        m = re.search(r"TOTAL\s+\$([0-9,]+\.\d{2})", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))
        else:
            m = re.search(r"Final Cost\s*:\s*\$([0-9,]+\.\d{2})", text)
            if m:
                r.amount_gross = Decimal(m.group(1).replace(",", ""))

        r.amount_net = r.amount_gross

        return r
