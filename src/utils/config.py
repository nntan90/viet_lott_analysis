"""
src/utils/config.py  — v4.0
Load env vars and model config JSON files.
"""
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

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

# ── Lottery types ─────────────────────────────────────────────────
LOTTERY_CONFIG_FILES: dict[str, str] = {
    "power_655": "model_params_655.json",
    "mega_645":  "model_params_645.json",
    "lotto_535": "model_params_535.json",     # v4.0: was lottery_635
}

LOTTERY_LABELS: dict[str, str] = {
    "power_655": "Power 6/55",
    "mega_645":  "Mega 6/45",
    "lotto_535": "Lotto 5/35",               # v4.0
}

# Lotto 5/35 runs AM (13:00) and PM (21:00) every day
LOTTERY_SESSIONS: dict[str, list[str]] = {
    "power_655": [],        # no session concept
    "mega_645":  [],
    "lotto_535": ["AM", "PM"],
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
    cfg = get_model_config(lottery_type)
    lo, hi = cfg["number_range"]
    return lo, hi


def has_special(lottery_type: str) -> bool:
    """Return True if this lottery type uses a special/bonus number (lotto_535, power_655)."""
    cfg = get_model_config(lottery_type)
    return bool(cfg.get("has_special", False))


def get_special_range(lottery_type: str) -> tuple[int, int] | None:
    """Return (lo, hi) of the special number range, or None if no special."""
    cfg = get_model_config(lottery_type)
    sr = cfg.get("special_range")
    if sr:
        return tuple(sr)
    return None


def get_pick_count(lottery_type: str) -> int:
    """Return how many main numbers to pick (5 for 535, 6 for others)."""
    cfg = get_model_config(lottery_type)
    return cfg.get("pick_count", 6)


def get_sessions(lottery_type: str) -> list[str]:
    """Return draw sessions: [] for 655/645, ['AM','PM'] for 535."""
    return LOTTERY_SESSIONS.get(lottery_type, [])
