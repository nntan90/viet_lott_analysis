"""
src/pipeline/prediction_generator.py  — v4.0
Generate a new prediction bộ số for a cycle.
Handles both 6-number (655/645) and 5-number + special (535).
"""
from __future__ import annotations

from src.models.model_loader import load_ensemble
from src.pipeline.cycle_manager import get_or_create_cycle
from src.utils import supabase_client as db
from src.utils.config import (
    LOTTERY_LABELS,
    get_model_config,
    get_pick_count,
    get_sessions,
    get_special_range,
    has_special,
)
from src.utils.logger import get_logger

log = get_logger("pipeline.generator")


def _pick_special_number(history: list[list[int]], actual_specials: list[int | None], sp_range: tuple[int, int]) -> int:
    """
    Pick a special number for lotto_535 from [sp_lo, sp_hi] using frequency analysis.
    The special number must NOT be in main_numbers (enforced by caller).
    """
    from collections import Counter
    lo, hi = sp_range
    valid = [n for n in actual_specials if n is not None and lo <= n <= hi]
    if not valid:
        # Fallback: uniform random
        import random
        return random.randint(lo, hi)
    counter = Counter(valid)
    # Return most frequent special (hot), or least frequent (cold) — we pick hot
    return counter.most_common(1)[0][0]


def generate_prediction(lottery_type: str) -> dict:
    """
    Full Phase 3a flow:
    1. Load ensemble model
    2. Fetch recent history
    3. Run ensemble → main numbers (5 or 6)
    4. For lotto_535: also pick 1 special number [1-12]
    5. Insert prediction_cycles + predictions
    6. Return result dict for Telegram
    """
    log.info(f"[GENERATE] Starting for {lottery_type}")

    config = get_model_config(lottery_type)
    model_version = config["version"]
    pick_count = get_pick_count(lottery_type)
    lottery_has_special = has_special(lottery_type)
    sp_range = get_special_range(lottery_type)

    # Step 1: Load models
    ensemble = load_ensemble(lottery_type, version=f"v{model_version}")

    # Step 2: Load history (combine all sessions for lotto_535)
    history_raw = db.get_recent_results(lottery_type, limit=200)
    history = [row["numbers"] for row in history_raw]

    if not history:
        raise RuntimeError(f"No history in DB for {lottery_type}. Run initial crawl first.")

    # Step 3: Predict main numbers
    numbers = ensemble.predict(history, n_picks=pick_count)

    # Step 4: Special number for lotto_535
    special_number: int | None = None
    if lottery_has_special and sp_range:
        actual_specials = [row.get("jackpot2") for row in history_raw]
        candidate = _pick_special_number(history, actual_specials, sp_range)
        # Ensure special not in main numbers
        lo, hi = sp_range
        if candidate in numbers:
            for alt in range(lo, hi + 1):
                if alt not in numbers:
                    candidate = alt
                    break
        special_number = candidate

    # Step 5: Upsert cycle + insert prediction
    cycle = get_or_create_cycle(lottery_type, model_version)
    db.insert_prediction(
        cycle_id=cycle["id"],
        lottery_type=lottery_type,
        numbers=numbers,
        model_version=model_version,
        special_number=special_number,
    )

    result = {
        "lottery_type": lottery_type,
        "lottery_label": LOTTERY_LABELS.get(lottery_type, lottery_type),
        "cycle_number": cycle["cycle_number"],
        "numbers": numbers,
        "special_number": special_number,
        "has_special": lottery_has_special,
        "model_version": model_version,
        "weights": {
            "lstm": ensemble.w_lstm,
            "xgboost": ensemble.w_xgb,
            "statistical": ensemble.w_stat,
        },
        "success": True,
    }
    log.info(f"[GENERATE] {lottery_type} Cycle #{cycle['cycle_number']} → {numbers}" +
             (f" | Special: {special_number}" if special_number else ""))
    return result
