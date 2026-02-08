"""Swiss OR Kontenrahmen KMU — expense accounts (6000-6999)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KMUAccount:
    number: int
    name: str
    description: str


# Subset relevant for a tech GmbH
KMU_ACCOUNTS: dict[int, KMUAccount] = {
    6000: KMUAccount(6000, "Mietaufwand", "Office rent"),
    6200: KMUAccount(6200, "Reparatur und Unterhalt", "Repairs and maintenance"),
    6300: KMUAccount(6300, "Versicherungen", "Insurance premiums"),
    6400: KMUAccount(6400, "Energie und Entsorgung", "Energy, utilities"),
    6500: KMUAccount(6500, "Verwaltungsaufwand", "General admin expenses"),
    6510: KMUAccount(6510, "Büromaterial", "Office supplies"),
    6520: KMUAccount(6520, "Drucksachen", "Printed materials"),
    6530: KMUAccount(6530, "Fachliteratur", "Professional literature"),
    6540: KMUAccount(6540, "Spesen und Reisen", "Travel expenses"),
    6570: KMUAccount(6570, "Lizenzen und Patente", "Domains, software licenses"),
    6580: KMUAccount(6580, "Beratungsaufwand", "Consulting fees"),
    6600: KMUAccount(6600, "Werbeaufwand", "Marketing and advertising"),
    6700: KMUAccount(6700, "Übriger Betriebsaufwand", "Other operating expenses"),
    6800: KMUAccount(6800, "Informatikaufwand", "IT expenses (general)"),
    6810: KMUAccount(6810, "Informatik-Infrastruktur", "Hosting, servers, hardware"),
    6820: KMUAccount(6820, "Informatik-Dienstleistungen", "API/SaaS/AI credits, dev services"),
    6830: KMUAccount(6830, "Telekommunikation", "SMS, voice, phone, telecom API"),
    6840: KMUAccount(6840, "Domänen und Hosting", "Domain registration, DNS hosting"),
    6850: KMUAccount(6850, "Software-Abonnemente", "SaaS subscriptions, cloud tools"),
}


def get_account(number: int) -> KMUAccount | None:
    return KMU_ACCOUNTS.get(number)


def list_accounts() -> list[KMUAccount]:
    return sorted(KMU_ACCOUNTS.values(), key=lambda a: a.number)
