"""Parser for ElevenLabs receipts (Stripe)."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class ElevenLabsParser(VendorParser):
    vendor_name = "ElevenLabs"

    def can_parse(self, text: str) -> bool:
        return "Eleven Labs" in text or "elevenlabs.io" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "ElevenLabs"
        r.vendor_country = "US"
        r.currency = "USD"
        r.category_account = 6820
        r.category_name = "Informatik-Dienstleistungen"

        # Invoice number
        m = re.search(r"Invoice number\s+(\S+\s+\d+)", text)
        if m:
            r.invoice_number = m.group(1).strip()

        # Receipt number
        m = re.search(r"Receipt number\s+([\d\s]+)", text)
        if m:
            r.receipt_number = " ".join(m.group(1).split())

        # Date
        m = re.search(r"Date paid\s+(\w+ \d{1,2}, \d{4})", text)
        if m:
            from datetime import datetime
            try:
                dt = datetime.strptime(m.group(1), "%B %d, %Y")
                r.date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Swiss VAT number
        m = re.search(r"CH VAT\s+(CHE[\s\d.]+\w+)", text)
        if m:
            r.vat_number = m.group(1).strip()

        # Description: plan name
        m = re.search(r"(Creator|Starter|Scale|Enterprise)[^\n]*\(per subscription\)", text)
        if m:
            r.description = f"ElevenLabs {m.group(1)} plan"
        else:
            r.description = "ElevenLabs subscription"

        # Period
        m = re.search(r"(\w{3}\s+\d{1,2})\s+.?\s*(\w{3}\s+\d{1,2},\s+\d{4})", text)
        if m:
            r.period = f"{m.group(1)} - {m.group(2)}"

        # Tax — clean null bytes first
        clean = text.replace("\x00", " ")
        m = re.search(r"VAT\s*-\s*Switzerland\s+(\d+\.?\d*)%\s+on\s+\$([0-9,]+\.\d{2})\s+\$([0-9,]+\.\d{2})", clean)
        if m:
            r.vat_rate = Decimal(m.group(1))
            r.vat_amount = Decimal(m.group(3).replace(",", ""))

        # Total paid
        m = re.search(r"\$([0-9,]+\.\d{2})\s+paid on", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))

        # Net (subtotal after discounts): "Total excluding tax $11.00"
        m = re.search(r"Total excluding tax\s+\$([0-9,]+\.\d{2})", text)
        if m:
            r.amount_net = Decimal(m.group(1).replace(",", ""))
        else:
            r.amount_net = r.amount_gross - r.vat_amount

        return r
