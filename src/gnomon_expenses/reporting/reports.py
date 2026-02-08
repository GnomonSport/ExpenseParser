"""Summary and VAT reports."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from rich.console import Console
from rich.table import Table

from gnomon_expenses.models.categories import KMU_ACCOUNTS
from gnomon_expenses.models.expense import Expense
from gnomon_expenses.models.vat import RATE_LABELS
from gnomon_expenses.storage.local_json import LocalJsonStorage

console = Console()


def _filter(expenses: list[Expense], month: str | None = None,
            currency: str | None = None) -> list[Expense]:
    if month:
        expenses = [e for e in expenses if e.date and e.date.strftime("%Y-%m") == month]
    if currency:
        expenses = [e for e in expenses if e.currency.upper() == currency.upper()]
    return expenses


def summary_report(month: str | None = None, currency: str | None = None) -> None:
    """Print a summary report grouped by KMU category."""
    storage = LocalJsonStorage()
    expenses = _filter(storage.load_all(), month, currency)

    if not expenses:
        console.print("[yellow]No expenses for the given filters.[/yellow]")
        return

    # Group by (currency, category_account)
    by_cat: dict[str, dict[int | None, list[Expense]]] = defaultdict(lambda: defaultdict(list))
    for e in expenses:
        by_cat[e.currency][e.category_account].append(e)

    for cur in sorted(by_cat):
        title = f"Expense Summary — {cur}"
        if month:
            title += f" ({month})"
        table = Table(title=title)
        table.add_column("Account", width=8)
        table.add_column("Category", width=30)
        table.add_column("Count", justify="right", width=6)
        table.add_column("Gross", justify="right", width=12)
        table.add_column("Net", justify="right", width=12)
        table.add_column("VAT", justify="right", width=10)

        total_gross = Decimal("0")
        total_net = Decimal("0")
        total_vat = Decimal("0")

        for acct_num in sorted(by_cat[cur], key=lambda x: x or 0):
            items = by_cat[cur][acct_num]
            gross = sum(e.amount_gross for e in items)
            net = sum(e.amount_net for e in items)
            vat = sum(e.vat_amount for e in items)

            acct = KMU_ACCOUNTS.get(acct_num) if acct_num else None
            cat_name = acct.name if acct else "Uncategorized"

            table.add_row(
                str(acct_num) if acct_num else "—",
                cat_name,
                str(len(items)),
                str(gross),
                str(net),
                str(vat),
            )
            total_gross += gross
            total_net += net
            total_vat += vat

        table.add_section()
        table.add_row("", "[bold]Total[/bold]", str(len(by_cat[cur])), str(total_gross), str(total_net), str(total_vat))
        console.print(table)
        console.print()


def vat_report(month: str | None = None) -> None:
    """Print a MWST/VAT report for tax filing."""
    storage = LocalJsonStorage()
    expenses = _filter(storage.load_all(), month)

    if not expenses:
        console.print("[yellow]No expenses for the given filters.[/yellow]")
        return

    # Group by (currency, vat_rate)
    by_rate: dict[str, dict[Decimal, list[Expense]]] = defaultdict(lambda: defaultdict(list))
    for e in expenses:
        by_rate[e.currency][e.vat_rate].append(e)

    for cur in sorted(by_rate):
        title = f"MWST/VAT Report — {cur}"
        if month:
            title += f" ({month})"
        table = Table(title=title)
        table.add_column("VAT Rate", width=35)
        table.add_column("Count", justify="right", width=6)
        table.add_column("Gross", justify="right", width=12)
        table.add_column("Net", justify="right", width=12)
        table.add_column("VAT Amount", justify="right", width=12)

        total_gross = Decimal("0")
        total_vat = Decimal("0")

        for rate in sorted(by_rate[cur]):
            items = by_rate[cur][rate]
            gross = sum(e.amount_gross for e in items)
            net = sum(e.amount_net for e in items)
            vat = sum(e.vat_amount for e in items)

            rate_label = RATE_LABELS.get(rate, f"{rate}%")

            table.add_row(rate_label, str(len(items)), str(gross), str(net), str(vat))
            total_gross += gross
            total_vat += vat

        table.add_section()
        table.add_row("[bold]Total[/bold]", str(sum(len(v) for v in by_rate[cur].values())),
                      str(total_gross), "", str(total_vat))
        console.print(table)
        console.print()
