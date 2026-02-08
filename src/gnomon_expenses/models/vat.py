"""Swiss MWST/VAT rates and helpers."""

from decimal import Decimal

# Swiss MWST rates (since 1 January 2024)
NORMAL_RATE = Decimal("8.1")       # Normalsatz
REDUCED_RATE = Decimal("2.6")      # Reduzierter Satz (food, medicine, books, etc.)
SPECIAL_RATE = Decimal("3.8")      # Sondersatz (lodging)
ZERO_RATE = Decimal("0")           # Exempt / foreign services

RATE_LABELS = {
    NORMAL_RATE: "Normalsatz (8.1%)",
    REDUCED_RATE: "Reduzierter Satz (2.6%)",
    SPECIAL_RATE: "Sondersatz Beherbergung (3.8%)",
    ZERO_RATE: "Befreit / Ausland",
}


def compute_vat(gross: Decimal, rate: Decimal) -> Decimal:
    """Compute VAT amount from gross and rate percentage."""
    if rate == ZERO_RATE:
        return Decimal("0")
    return (gross * rate / (100 + rate)).quantize(Decimal("0.01"))


def compute_net(gross: Decimal, rate: Decimal) -> Decimal:
    """Compute net amount (excl. VAT) from gross."""
    return gross - compute_vat(gross, rate)
