# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
pip install -e .              # install (editable)
pip install -e ".[dev]"       # with pytest
pip install -e ".[ocr]"       # with Tesseract OCR support
gnomon-expenses process . -r  # process all PDFs recursively
gnomon-expenses list-expenses  # list all expenses
pytest tests/                  # run tests
```

## Architecture

**3-tier extraction pipeline** for PDF receipts/invoices:
1. **pdfplumber** text extraction (fast, works on digital PDFs)
2. **Tesseract OCR** fallback (for scanned documents, optional `[ocr]` extra)
3. **Claude API** fallback (requires `ANTHROPIC_API_KEY`)

**Vendor parser pattern**: Each vendor (Anomaly, Anthropic, ElevenLabs, Infomaniak, Hetzner, Twilio, Namecheap) has a dedicated regex parser in `extraction/parsers/`. Parsers are tried in order; `GenericParser` is the last-resort fallback. To add a vendor: create a parser class inheriting `VendorParser`, implement `can_parse()` and `parse()`, then register it in `pipeline.py:PARSERS` list (before `GenericParser`).

**Storage adapter pattern**: `StorageAdapter` ABC in `storage/adapter.py`, currently implemented as `LocalJsonStorage` with fcntl file locking. Every `save()` writes to three places simultaneously: `data/ledger.json` (global), `data/YYYY-MM.json` (monthly), and matching `.csv` mirrors.

**Auto-filing**: `process` moves PDFs into `YY-MM/` subfolders based on extracted expense date.

## Key Gotchas

- **Python 3.11 + Pydantic**: Use `Optional[X]` not `X | None` in Pydantic model fields. The `date` field name shadows the `date` type — use `import datetime as _dt` and `_dt.date`.
- **Null bytes in PDFs**: pdfplumber sometimes produces `\x00` in extracted text (seen in Anthropic/Stripe and ElevenLabs receipts). Clean with `.replace("\x00", " ")` before regex matching.
- **Decimal for money**: All monetary amounts use `Decimal`, never `float`.
- **SHA-256 dedup**: Files are deduplicated by content hash, not filename. Re-downloads and renames are handled automatically.
- **Parser ordering matters**: Specific vendor parsers must come before `GenericParser` in the `PARSERS` list. First `can_parse()` match wins.

## Environment Variables

- `GNOMON_DATA_DIR` — data storage path (default: `./data`)
- `ANTHROPIC_API_KEY` — required only for Tier 3 AI extraction

## Swiss Accounting Context

Expenses are categorized per Swiss OR Kontenrahmen KMU (accounts 6000–6999). Swiss MWST/VAT rates: 8.1% Normalsatz, 2.6% reduziert, 3.8% Sondersatz. Vendors in CH and some foreign vendors (Anthropic, ElevenLabs, Hetzner) charge 8.1% Swiss VAT; US/IE vendors without Swiss presence charge 0%.
