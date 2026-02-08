# Gnomon Expenses

Automated expense tracking for Swiss GmbH -- PDF extraction, KMU categorization, MWST reporting.

## Status

**v0.1.0** -- functional core. The CLI can process PDF receipts and invoices from 7 vendors, extract amounts/dates/VAT via regex parsers, categorize per Swiss OR Kontenrahmen KMU, and store results as JSON + CSV. Auto-filing moves PDFs into `YY-MM/` folders. A directory watcher processes new files on arrival.

## Quick start

```bash
pip install -e .
gnomon-expenses process . -r      # extract all PDFs recursively
gnomon-expenses list-expenses      # view what was captured
gnomon-expenses report             # summary grouped by category
gnomon-expenses vat-report         # MWST report for tax filing
```

Optional extras:

```bash
pip install -e ".[ocr]"   # Tesseract OCR for scanned documents
pip install -e ".[dev]"   # pytest
```

Tier 3 AI extraction requires `ANTHROPIC_API_KEY` in the environment.

## CLI reference

| Command | Description |
|---|---|
| `process <dir>` | Extract expenses from PDFs. `-r` for recursive, `--force` to re-process, `--no-file` to skip auto-filing |
| `list-expenses` | List all expenses. Filter by `--month`, `--vendor`, `--label`, `--currency`, `--status` |
| `label <id> <labels...>` | Add labels to an expense |
| `note <id> <text>` | Attach a note to an expense |
| `attach-context <id> <file>` | Link a context file (CSV, screenshot, etc.) to an expense |
| `categorize <id> <account>` | Override the KMU category account number |
| `categories` | Show all available KMU account categories |
| `export` | Export expenses to CSV. `--month` to filter, `-o` for output path |
| `watch <dir>` | Watch a directory for new PDFs and auto-process them |
| `report` | Summary report grouped by category. `--month`, `--currency` filters |
| `vat-report` | MWST/VAT report for tax filing. `--month` filter |

## Architecture

Three-tier extraction pipeline with fallback:

```
PDF --> pdfplumber text --> vendor regex parser --> Expense
         |                    (no match)
         v                       |
      Tesseract OCR              v
         |                  GenericParser
         v                       |
      Claude API                 v
         |                    Expense
         v
      Expense
```

Each vendor has a dedicated regex parser (`extraction/parsers/`). Parsers are tried in registration order; `GenericParser` is the fallback. To add a vendor: subclass `VendorParser`, implement `can_parse()` and `parse()`, register in `pipeline.py` before `GenericParser`.

Storage uses an adapter pattern (`StorageAdapter` ABC). The current `LocalJsonStorage` implementation writes to three places on every save: `data/ledger.json` (global), `data/YYYY-MM.json` (monthly), and matching `.csv` mirrors. File locking via `fcntl` prevents corruption from concurrent writes.

## Supported vendors

| Vendor | Country | Currency | Swiss VAT | KMU Account | Notes |
|---|---|---|---|---|---|
| Anomaly | US | USD | -- | 6820 | Stripe receipts, opencode credits |
| Anthropic | US | USD | 8.1% | 6820 | Stripe receipts, Claude API |
| ElevenLabs | US | USD | 8.1% | 6820 | Stripe receipts, TTS API |
| Hetzner | DE | EUR | 8.1% | 6810 | Cloud infrastructure |
| Infomaniak | CH | CHF | 8.1% | 6850 | kSuite, hosting |
| Namecheap | US | USD | -- | 6840 | Domain registrations |
| Twilio | IE | USD | -- | 6830 | Telecom, messaging |

KMU accounts follow the Swiss OR Kontenrahmen (6000-6999 range). Swiss MWST rates: 8.1% Normalsatz, 2.6% reduziert, 3.8% Sondersatz.

## Roadmap

**v0.2 -- Multi-currency and cloud storage**
- Cloud storage adapters (S3, GCS) alongside local JSON
- Multi-currency support with automatic FX rate lookup
- Expense attachments stored in cloud

**v0.3 -- Reporting and export**
- Web dashboard for browsing and reviewing expenses
- Abacus / bexio export for Swiss accounting software
- Period-over-period comparison reports

**v0.4 -- Automation**
- Automated bank statement matching (CSV/MT940 import, fuzzy match to invoices)
- CI/CD pipeline with security auditing
- Scheduled processing via cron / cloud functions

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GNOMON_DATA_DIR` | No | Data storage path (default: `./data`) |
| `ANTHROPIC_API_KEY` | No | Required only for Tier 3 AI extraction |

## License

See [LICENSE](LICENSE).
