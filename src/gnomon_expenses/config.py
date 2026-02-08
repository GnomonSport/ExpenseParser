"""Configuration: paths, API keys, defaults."""

import os
from pathlib import Path

# Base directory for data storage
DATA_DIR = Path(os.environ.get("GNOMON_DATA_DIR", Path.cwd() / "data"))
LEDGER_PATH = DATA_DIR / "ledger.json"

# Anthropic API key for AI extraction (Tier 3)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Default currency for Swiss company
DEFAULT_CURRENCY = "CHF"

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf"}
