"""Tier 3: AI extraction using Claude API for documents that resist text/OCR parsing."""

from __future__ import annotations

import base64
from datetime import date
from decimal import Decimal
from pathlib import Path

from gnomon_expenses.config import ANTHROPIC_API_KEY
from gnomon_expenses.models.expense import (
    Expense,
    ExtractionMethod,
    ExpenseStatus,
)

SYSTEM_PROMPT = """\
You are an expense data extraction assistant. Extract structured data from the
provided invoice/receipt document. Return ONLY valid JSON with these fields:
vendor, vendor_country (ISO 2-letter), invoice_number, receipt_number,
date (YYYY-MM-DD), period, description, amount_gross, amount_net, currency (ISO),
vat_rate, vat_amount, vat_number, category_account (Swiss KMU: 6570=licenses,
6810=hosting/servers, 6820=API/SaaS/AI, 6830=telecom, 6840=domains, 6850=SaaS subscriptions),
category_name.
"""


def extract_with_ai(path: str | Path, fhash: str) -> Expense | None:
    """Use Claude API to extract expense data from a PDF."""
    if not ANTHROPIC_API_KEY:
        return None

    import anthropic
    import json

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    pdf_bytes = Path(path).read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract expense data from this document as JSON.",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    data = json.loads(response_text)

    expense_date = None
    if data.get("date"):
        try:
            expense_date = date.fromisoformat(data["date"])
        except ValueError:
            pass

    return Expense(
        file_path=str(path),
        file_hash=fhash,
        vendor=data.get("vendor", ""),
        vendor_country=data.get("vendor_country", ""),
        invoice_number=data.get("invoice_number", ""),
        receipt_number=data.get("receipt_number", ""),
        date=expense_date,
        period=data.get("period", ""),
        description=data.get("description", ""),
        amount_gross=Decimal(str(data.get("amount_gross", 0))),
        amount_net=Decimal(str(data.get("amount_net", 0))),
        currency=data.get("currency", "USD"),
        vat_rate=Decimal(str(data.get("vat_rate", 0))),
        vat_amount=Decimal(str(data.get("vat_amount", 0))),
        vat_number=data.get("vat_number", ""),
        category_account=data.get("category_account"),
        category_name=data.get("category_name", ""),
        extraction_method=ExtractionMethod.AI,
        extraction_confidence=0.8,
        status=ExpenseStatus.NEEDS_REVIEW,
    )
