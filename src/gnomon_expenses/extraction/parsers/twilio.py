"""Parser for Twilio receipts."""

import re
from decimal import Decimal

from gnomon_expenses.extraction.parsers.base import ParseResult, VendorParser


class TwilioParser(VendorParser):
    vendor_name = "Twilio"

    def can_parse(self, text: str) -> bool:
        return "Twilio" in text and "RECEIPT" in text

    def parse(self, text: str) -> ParseResult | None:
        r = ParseResult()
        r.vendor = "Twilio"
        r.vendor_country = "IE"  # Twilio Ireland Limited
        r.currency = "USD"
        r.category_account = 6830
        r.category_name = "Telekommunikation"
        r.description = "Twilio API Services"
        r.vat_rate = Decimal("0")  # Foreign service, no Swiss VAT
        r.vat_amount = Decimal("0")

        # VAT number
        m = re.search(r"VAT Registration Number:\s*(\S+)", text)
        if m:
            r.vat_number = m.group(1)

        # Period: "Date 01 January - 31 January, 2026"
        m = re.search(r"Date\s+(\d{1,2}\s+\w+)\s*-\s*(\d{1,2}\s+\w+,\s+\d{4})", text)
        if m:
            r.period = f"{m.group(1)} - {m.group(2)}"
            # Parse end date as the invoice date
            from datetime import datetime
            try:
                dt = datetime.strptime(m.group(2).strip(), "%d %B, %Y")
                r.date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Total Paid: "Total Paid $450.00"
        m = re.search(r"Total Paid\s+\$([0-9,]+\.\d{2})", text)
        if m:
            r.amount_gross = Decimal(m.group(1).replace(",", ""))
            r.amount_net = r.amount_gross

        # Account SID for reference
        m = re.search(r"Account SID\s+(\S+)", text)
        if m:
            r.receipt_number = m.group(1)

        return r
