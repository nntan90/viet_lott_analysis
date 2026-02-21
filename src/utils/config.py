"""
src/utils/config.py
Load env vars and model config JSON files.
"""
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ── Project root ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT / "config"

# ── Supabase ──────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "models")

# ── Telegram ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# ── Kaggle ────────────────────────────────────────────────────────
KAGGLE_USERNAME: str = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY: str = os.getenv("KAGGLE_KEY", "")
KAGGLE_DATASET: str = os.getenv("KAGGLE_DATASET", "vietlott-historical-data")
KAGGLE_NOTEBOOK: str = os.getenv("KAGGLE_NOTEBOOK", "vietlott-training-notebook")

# ── Lottery type mapping ──────────────────────────────────────────
LOTTERY_CONFIG_FILES: dict[str, str] = {
    "power_655": "model_params_655.json",
    "mega_645": "model_params_645.json",
    "lottery_635": "model_params_635.json",
}

LOTTERY_LABELS: dict[str, str] = {
    "power_655": "Power 6/55",
    "mega_645": "Mega 6/45",
    "lottery_635": "Lottery 6/35",
}

_model_config_cache: dict[str, Any] = {}


def get_model_config(lottery_type: str) -> dict[str, Any]:
    """Load and cache model config JSON for a given lottery type."""
    if lottery_type in _model_config_cache:
        return _model_config_cache[lottery_type]

    filename = LOTTERY_CONFIG_FILES.get(lottery_type)
    if not filename:
        raise ValueError(f"Unknown lottery type: {lottery_type}")

    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    _model_config_cache[lottery_type] = config
    return config


def get_number_range(lottery_type: str) -> tuple[int, int]:
    """Return (min_num, max_num) for the given lottery type."""
    cfg = get_model_config(lottery_type)
    lo, hi = cfg["number_range"]
    return lo, hi
