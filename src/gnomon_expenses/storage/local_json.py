"""Local JSON file storage with file locking for concurrent access."""

import csv
import fcntl
import json
from collections import defaultdict
from pathlib import Path

from gnomon_expenses.config import DATA_DIR, LEDGER_PATH
from gnomon_expenses.models.expense import Expense
from gnomon_expenses.storage.adapter import StorageAdapter

CSV_FIELDS = [
    "id", "date", "vendor", "vendor_country", "description",
    "invoice_number", "receipt_number", "period",
    "amount_gross", "amount_net", "currency",
    "vat_rate", "vat_amount", "vat_number",
    "category_account", "category_name",
    "labels", "notes", "file_path", "status",
]


def _read_json_locked(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return data


def _write_json_locked(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(records, f, indent=2, default=str)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _month_key(expense_dict: dict) -> str | None:
    """Return 'YYYY-MM' for an expense dict, or None if no date."""
    d = expense_dict.get("date")
    if d and isinstance(d, str) and len(d) >= 7:
        return d[:7]
    return None


def _month_ledger_path(month: str) -> Path:
    """Path for a monthly ledger, e.g. data/2026-01.json."""
    return DATA_DIR / f"{month}.json"


def _rebuild_monthly(records: list[dict]) -> None:
    """Rebuild all monthly ledger files from the global records."""
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        mk = _month_key(r)
        if mk:
            by_month[mk].append(r)
    # Write each month
    for month, month_records in by_month.items():
        _write_json_locked(_month_ledger_path(month), month_records)


def _write_csv(records: list[dict], path: Path) -> None:
    """Write records to a CSV file, sorted by date."""
    sorted_records = sorted(records, key=lambda r: r.get("date") or "")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in sorted_records:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            row["labels"] = "; ".join(r.get("labels", []))
            row["category_account"] = r.get("category_account") or ""
            writer.writerow(row)


def _sync_csv(records: list[dict]) -> None:
    """Rebuild data/ledger.csv and all monthly CSVs from records."""
    # Global CSV
    _write_csv(records, DATA_DIR / "ledger.csv")
    # Monthly CSVs
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        mk = _month_key(r)
        if mk:
            by_month[mk].append(r)
    for month, month_records in by_month.items():
        _write_csv(month_records, DATA_DIR / f"{month}.csv")


def _update_monthly_single(expense_dict: dict) -> None:
    """Upsert a single expense into its monthly ledger."""
    mk = _month_key(expense_dict)
    if not mk:
        return
    path = _month_ledger_path(mk)
    records = _read_json_locked(path)
    eid = expense_dict.get("id")
    for i, r in enumerate(records):
        if r.get("id") == eid:
            records[i] = expense_dict
            _write_json_locked(path, records)
            return
    records.append(expense_dict)
    _write_json_locked(path, records)


class LocalJsonStorage(StorageAdapter):
    def __init__(self, path: Path | None = None):
        self.path = path or LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> list[Expense]:
        return [Expense.model_validate(r) for r in _read_json_locked(self.path)]

    def save(self, expense: Expense) -> None:
        records = _read_json_locked(self.path)
        dump = json.loads(expense.model_dump_json())
        # Upsert by id in global ledger
        for i, r in enumerate(records):
            if r.get("id") == expense.id:
                records[i] = dump
                _write_json_locked(self.path, records)
                _update_monthly_single(dump)
                _sync_csv(records)
                return
        records.append(dump)
        _write_json_locked(self.path, records)
        _update_monthly_single(dump)
        _sync_csv(records)

    def save_all(self, expenses: list[Expense]) -> None:
        records = [json.loads(e.model_dump_json()) for e in expenses]
        _write_json_locked(self.path, records)
        _rebuild_monthly(records)
        _sync_csv(records)

    def find_by_id(self, expense_id: str) -> Expense | None:
        for r in _read_json_locked(self.path):
            if r.get("id", "").startswith(expense_id):
                return Expense.model_validate(r)
        return None

    def find_by_hash(self, file_hash: str) -> Expense | None:
        for r in _read_json_locked(self.path):
            if r.get("file_hash") == file_hash:
                return Expense.model_validate(r)
        return None

    def delete(self, expense_id: str) -> bool:
        records = _read_json_locked(self.path)
        new_records = [r for r in records if not r.get("id", "").startswith(expense_id)]
        if len(new_records) < len(records):
            _write_json_locked(self.path, new_records)
            _rebuild_monthly(new_records)
            _sync_csv(new_records)
            return True
        return False
