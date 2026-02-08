"""Click CLI — all user-facing commands."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from gnomon_expenses.config import SUPPORTED_EXTENSIONS
from gnomon_expenses.extraction.pipeline import process_pdf
from gnomon_expenses.models.categories import KMU_ACCOUNTS, list_accounts
from gnomon_expenses.models.expense import Expense, ExpenseStatus, file_hash
from gnomon_expenses.storage.local_json import LocalJsonStorage

console = Console()


def _get_storage() -> LocalJsonStorage:
    return LocalJsonStorage()


def _find_pdfs(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all PDF files in a directory."""
    if recursive:
        return sorted(p for p in directory.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)


def _file_into_month_folder(pdf: Path, expense: Expense, base_dir: Path) -> Path:
    """Move a PDF into its YY-MM/ subfolder based on expense date. Returns new path."""
    import shutil

    if not expense.date:
        return pdf

    folder_name = expense.date.strftime("%y-%m")  # e.g. "26-01"
    month_dir = base_dir / folder_name
    month_dir.mkdir(exist_ok=True)

    # Already in the correct monthly folder? Keep it where it is.
    if pdf.resolve().parent == month_dir.resolve():
        return pdf

    dest = month_dir / pdf.name

    # Handle name collision (different file, same name)
    if dest.exists():
        stem, suffix = pdf.stem, pdf.suffix
        i = 1
        while dest.exists():
            dest = month_dir / f"{stem}_{i}{suffix}"
            i += 1

    shutil.move(str(pdf), str(dest))
    return dest


@click.group()
def cli() -> None:
    """Gnomon Expenses — automated expense tracking for Swiss GmbH."""


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("-r", "--recursive", is_flag=True, help="Scan subdirectories")
@click.option("--force", is_flag=True, help="Re-process even if already in ledger")
@click.option("--no-file", is_flag=True, help="Don't move PDFs into monthly folders")
def process(directory: Path, recursive: bool, force: bool, no_file: bool) -> None:
    """Process all PDFs in a directory and file them into YY-MM/ folders."""
    storage = _get_storage()
    pdfs = _find_pdfs(directory, recursive)

    if not pdfs:
        console.print("[yellow]No PDF files found.[/yellow]")
        return

    new_count = 0
    skip_count = 0
    fail_count = 0

    for pdf in pdfs:
        fhash = file_hash(pdf)
        existing = storage.find_by_hash(fhash)

        if existing and not force:
            console.print(f"  [dim]skip[/dim]  {pdf.name} (already processed)")
            skip_count += 1
            continue

        expense = process_pdf(pdf)
        if expense is None:
            console.print(f"  [red]fail[/red]  {pdf.name} (could not extract data)")
            fail_count += 1
            continue

        if existing and force:
            expense.id = existing.id

        # Move PDF into YY-MM/ folder
        if not no_file:
            new_path = _file_into_month_folder(pdf, expense, directory.resolve())
            expense.file_path = str(new_path)

        storage.save(expense)
        status_color = "green" if expense.status == ExpenseStatus.PROCESSED else "yellow"
        filed_to = ""
        if not no_file and expense.date:
            filed_to = f" -> {expense.date.strftime('%y-%m')}/"
        console.print(
            f"  [{status_color}]  ok[/{status_color}]  {pdf.name} — "
            f"{expense.vendor} {expense.currency} {expense.amount_gross} "
            f"({expense.date}){filed_to}"
        )
        new_count += 1

    console.print(f"\nDone: {new_count} processed, {skip_count} skipped, {fail_count} failed")


@cli.command("list-expenses")
@click.option("-m", "--month", help="Filter by month (YYYY-MM)")
@click.option("-v", "--vendor", help="Filter by vendor name")
@click.option("-l", "--label", help="Filter by label")
@click.option("-c", "--currency", help="Filter by currency")
@click.option("-s", "--status", type=click.Choice(["processed", "needs_review", "verified"]))
def list_expenses(month: str | None, vendor: str | None, label: str | None,
                  currency: str | None, status: str | None) -> None:
    """List all expenses with optional filters."""
    storage = _get_storage()
    expenses = storage.load_all()

    if month:
        expenses = [e for e in expenses if e.date and e.date.strftime("%Y-%m") == month]
    if vendor:
        v_lower = vendor.lower()
        expenses = [e for e in expenses if v_lower in e.vendor.lower()]
    if label:
        expenses = [e for e in expenses if label in e.labels]
    if currency:
        expenses = [e for e in expenses if e.currency.upper() == currency.upper()]
    if status:
        expenses = [e for e in expenses if e.status.value == status]

    if not expenses:
        console.print("[yellow]No expenses found.[/yellow]")
        return

    table = Table(title="Expenses")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Date", width=10)
    table.add_column("Vendor", width=14)
    table.add_column("Description", width=30)
    table.add_column("Amount", justify="right", width=12)
    table.add_column("Cur", width=4)
    table.add_column("VAT", justify="right", width=8)
    table.add_column("Cat", width=5)
    table.add_column("Labels", width=15)
    table.add_column("Status", width=10)

    total_by_currency: dict[str, Decimal] = {}

    for e in sorted(expenses, key=lambda x: x.date or date.min):
        status_style = {
            ExpenseStatus.PROCESSED: "green",
            ExpenseStatus.NEEDS_REVIEW: "yellow",
            ExpenseStatus.VERIFIED: "blue",
        }.get(e.status, "white")

        table.add_row(
            e.id,
            str(e.date) if e.date else "—",
            e.vendor,
            e.description[:30],
            str(e.amount_gross),
            e.currency,
            f"{e.vat_rate}%" if e.vat_rate else "—",
            str(e.category_account) if e.category_account else "—",
            ", ".join(e.labels) if e.labels else "—",
            f"[{status_style}]{e.status.value}[/{status_style}]",
        )
        total_by_currency.setdefault(e.currency, Decimal("0"))
        total_by_currency[e.currency] += e.amount_gross

    console.print(table)
    console.print()
    for cur, total in sorted(total_by_currency.items()):
        console.print(f"  Total {cur}: {total}")
    console.print(f"  ({len(expenses)} expenses)")


@cli.command()
@click.argument("expense_id")
@click.argument("labels", nargs=-1, required=True)
def label(expense_id: str, labels: tuple[str, ...]) -> None:
    """Add labels to an expense."""
    storage = _get_storage()
    expense = storage.find_by_id(expense_id)
    if not expense:
        console.print(f"[red]Expense {expense_id!r} not found.[/red]")
        raise SystemExit(1)

    for lbl in labels:
        if lbl not in expense.labels:
            expense.labels.append(lbl)

    storage.save(expense)
    console.print(f"Labels on {expense.id}: {', '.join(expense.labels)}")


@cli.command()
@click.argument("expense_id")
@click.argument("text")
def note(expense_id: str, text: str) -> None:
    """Attach a note to an expense."""
    storage = _get_storage()
    expense = storage.find_by_id(expense_id)
    if not expense:
        console.print(f"[red]Expense {expense_id!r} not found.[/red]")
        raise SystemExit(1)

    if expense.notes:
        expense.notes += f"\n{text}"
    else:
        expense.notes = text

    storage.save(expense)
    console.print(f"Note added to {expense.id}")


@cli.command("attach-context")
@click.argument("expense_id")
@click.argument("file_path", type=click.Path(exists=True))
def attach_context(expense_id: str, file_path: str) -> None:
    """Link a context file (CSV, screenshot, etc.) to an expense."""
    storage = _get_storage()
    expense = storage.find_by_id(expense_id)
    if not expense:
        console.print(f"[red]Expense {expense_id!r} not found.[/red]")
        raise SystemExit(1)

    abs_path = str(Path(file_path).resolve())
    if abs_path not in expense.context_files:
        expense.context_files.append(abs_path)

    storage.save(expense)
    console.print(f"Context file attached to {expense.id}: {abs_path}")


@cli.command()
@click.argument("expense_id")
@click.argument("account", type=int)
def categorize(expense_id: str, account: int) -> None:
    """Override the category (KMU account number) for an expense."""
    acct = KMU_ACCOUNTS.get(account)
    if not acct:
        console.print(f"[red]Unknown account {account}. Use 'gnomon-expenses categories' to see options.[/red]")
        raise SystemExit(1)

    storage = _get_storage()
    expense = storage.find_by_id(expense_id)
    if not expense:
        console.print(f"[red]Expense {expense_id!r} not found.[/red]")
        raise SystemExit(1)

    expense.category_account = account
    expense.category_name = acct.name
    storage.save(expense)
    console.print(f"Category set: {account} — {acct.name}")


@cli.command()
def categories() -> None:
    """Show all available KMU account categories."""
    table = Table(title="Swiss OR Kontenrahmen KMU — Expense Accounts")
    table.add_column("Account", style="bold", width=8)
    table.add_column("Name", width=30)
    table.add_column("Description", width=40)

    for acct in list_accounts():
        table.add_row(str(acct.number), acct.name, acct.description)

    console.print(table)


@cli.command()
@click.option("-o", "--output", type=click.Path(path_type=Path), default="expenses.csv",
              help="Output CSV file path")
@click.option("-m", "--month", help="Filter by month (YYYY-MM)")
def export(output: Path, month: str | None) -> None:
    """Export all expenses to CSV."""
    import csv

    storage = _get_storage()
    expenses = storage.load_all()
    if month:
        expenses = [e for e in expenses if e.date and e.date.strftime("%Y-%m") == month]

    if not expenses:
        console.print("[yellow]No expenses to export.[/yellow]")
        return

    fields = [
        "id", "date", "vendor", "vendor_country", "description",
        "invoice_number", "receipt_number", "period",
        "amount_gross", "amount_net", "currency",
        "vat_rate", "vat_amount", "vat_number",
        "category_account", "category_name",
        "labels", "notes", "file_path", "status",
    ]

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in sorted(expenses, key=lambda x: x.date or date.min):
            writer.writerow({
                "id": e.id,
                "date": e.date,
                "vendor": e.vendor,
                "vendor_country": e.vendor_country,
                "description": e.description,
                "invoice_number": e.invoice_number,
                "receipt_number": e.receipt_number,
                "period": e.period,
                "amount_gross": e.amount_gross,
                "amount_net": e.amount_net,
                "currency": e.currency,
                "vat_rate": e.vat_rate,
                "vat_amount": e.vat_amount,
                "vat_number": e.vat_number,
                "category_account": e.category_account or "",
                "category_name": e.category_name,
                "labels": "; ".join(e.labels),
                "notes": e.notes,
                "file_path": e.file_path,
                "status": e.status.value,
            })

    console.print(f"Exported {len(expenses)} expenses to {output}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("-r", "--recursive", is_flag=True, help="Watch subdirectories too")
def watch(directory: Path, recursive: bool) -> None:
    """Watch a directory for new PDFs and auto-process them."""
    from gnomon_expenses.watcher.folder_watcher import start_watching

    console.print(f"Watching {directory} for new PDFs... (Ctrl+C to stop)")
    start_watching(directory, recursive=recursive)


@cli.command()
@click.option("-m", "--month", help="Filter by month (YYYY-MM)")
@click.option("-c", "--currency", help="Filter by currency")
def report(month: str | None, currency: str | None) -> None:
    """Generate a summary report grouped by category."""
    from gnomon_expenses.reporting.reports import summary_report
    summary_report(month=month, currency=currency)


@cli.command("vat-report")
@click.option("-m", "--month", help="Filter by month (YYYY-MM)")
def vat_report(month: str | None) -> None:
    """Generate a MWST/VAT report for tax filing."""
    from gnomon_expenses.reporting.reports import vat_report as _vat_report
    _vat_report(month=month)
