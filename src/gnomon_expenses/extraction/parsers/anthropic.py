"""Parser for Anthropic receipts (Claude Max plan via Stripe)."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class AnthropicParser(VendorParser):
    vendor_name = "Anthropic"

    def can_parse(self, text: str) -> bool:
        return "Anthropic" in text and "anthropic.com" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Anthropic"
        r.vendor_country = "US"
        r.currency = "USD"
        r.category_account = 6820
        r.category_name = "Informatik-Dienstleistungen"
        r.vat_rate = Decimal("0")  # US vendor, no Swiss VAT collected by default
        r.vat_amount = Decimal("0")

        # Invoice number
        m = re.search(r"Invoice number\s+(\S+\s+\d+)", text)
        if m:
            r.invoice_number = m.group(1).strip()

        # Receipt number: may span multiple lines
        m = re.search(r"Receipt number\s+([\d\s]+)", text)
        if m:
            r.receipt_number = " ".join(m.group(1).split())

        # Date: "Date paid February 8, 2026"
        m = re.search(r"Date paid\s+(\w+ \d{1,2}, \d{4})", text)
        if m:
            from datetime import datetime
            try:
                dt = datetime.strptime(m.group(1), "%B %d, %Y")
                r.date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Description from first line item: "Max plan - 20x"
        m = re.search(r"(Max plan\s*-\s*\w+)", text)
        if m:
            r.description = f"Claude {m.group(1).strip()}"
        else:
            r.description = "Anthropic API / Claude"

        # Period: "Feb 8 Mar 8, 2026" or similar
        m = re.search(r"(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2},\s+\d{4})", text)
        if m:
            r.period = f"{m.group(1)} - {m.group(2)}"

        # Tax: check if Anthropic charged tax (they do for Swiss customers at 8.1%)
        # Note: pdfplumber sometimes inserts \x00 bytes in the extracted text
        clean = text.replace("\x00", " ")
        m = re.search(r"Tax\s+(\d+\.?\d*)%\s+on\s+\$([0-9,]+\.\d{2})\s+\$([0-9,]+\.\d{2})", clean)
        if m:
            r.vat_rate = Decimal(m.group(1))
            r.vat_amount = Decimal(m.group(3).replace(",", ""))

        # Total: "$216.20 paid on"
        m = re.search(r"\$([0-9,]+\.\d{2})\s+paid on", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))

        # Subtotal (net): "Subtotal $200.00"
        m = re.search(r"Subtotal\s+\$([0-9,]+\.\d{2})", text)
        if m:
            r.amount_net = Decimal(m.group(1).replace(",", ""))
        else:
            r.amount_net = r.amount_gross - r.vat_amount

        return r
