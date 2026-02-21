"""
src/pipeline/prediction_generator.py
Generate a new prediction bộ số for a cycle.
Phase 3a of the pipeline.
"""
from __future__ import annotations

from src.models.model_loader import load_ensemble
from src.pipeline.cycle_manager import get_or_create_cycle
from src.utils import supabase_client as db
from src.utils.config import get_model_config, LOTTERY_LABELS
from src.utils.logger import get_logger

log = get_logger("pipeline.generator")


def generate_prediction(lottery_type: str) -> dict:
    """
    Full Phase 3a flow:
    1. Load ensemble model
    2. Fetch recent 50 draws
    3. Run ensemble → 6 numbers
    4. Insert prediction_cycles + predictions
    5. Return result dict for Telegram notification
    """
    log.info(f"[GENERATE] Starting for {lottery_type}")

    config = get_model_config(lottery_type)
    model_version = config["version"]

    # Step 1: Load models
    ensemble = load_ensemble(lottery_type, version=f"v{model_version}")

    # Step 2: Load history
    history_raw = db.get_recent_results(lottery_type, limit=200)
    history = [row["numbers"] for row in history_raw]

    if not history:
        raise RuntimeError(f"No history in DB for {lottery_type}. Run initial crawl first.")

    # Step 3: Predict
    numbers = ensemble.predict(history, n_picks=6)

    # Step 4: Upsert cycle + insert prediction
    cycle = get_or_create_cycle(lottery_type, model_version)
    prediction = db.insert_prediction(
        cycle_id=cycle["id"],
        lottery_type=lottery_type,
        numbers=numbers,
        model_version=model_version,
    )

    result = {
        "lottery_type": lottery_type,
        "lottery_label": LOTTERY_LABELS.get(lottery_type, lottery_type),
        "cycle_number": cycle["cycle_number"],
        "numbers": numbers,
        "model_version": model_version,
        "weights": {
            "lstm": ensemble.w_lstm,
            "xgboost": ensemble.w_xgb,
            "statistical": ensemble.w_stat,
        },
        "success": True,
    }
    log.info(f"[GENERATE] {lottery_type} Cycle #{cycle['cycle_number']} → {numbers}")
    return result
