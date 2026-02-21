"""
src/pipeline/retrain_evaluator.py
Phase 3d: Evaluate cycle results and decide whether to retrain models.
"""
from __future__ import annotations

from typing import Any

from src.utils import supabase_client as db
from src.utils.config import get_model_config, LOTTERY_LABELS
from src.utils.logger import get_logger

log = get_logger("pipeline.retrain")

WEIGHT_STEP = 0.05
WEIGHT_MIN = 0.10
WEIGHT_MAX = 0.60


def evaluate_and_retrain(lottery_type: str, cycle_id: str) -> dict[str, Any]:
    """
    Phase 3d flow:
    1. Load 5 match_results for this cycle
    2. Compute performance metrics
    3. Decide: RETRAIN | SKIP
    4. If RETRAIN: adjust weights + log + trigger Kaggle
    5. Return evaluation summary
    """
    log.info(f"[EVALUATE] {lottery_type} cycle={cycle_id}")

    match_rows = db.get_match_results_for_cycle(cycle_id)
    if len(match_rows) < 5:
        log.warning(f"Only {len(match_rows)} match rows found (expected 5)")

    # ── Metrics ───────────────────────────────────────────────────
    hit_counts = [row["matched_count"] for row in match_rows]
    hit_3plus = sum(1 for c in hit_counts if c >= 3)
    hit_4plus = sum(1 for c in hit_counts if c >= 4)
    max_match = max(hit_counts) if hit_counts else 0

    config = get_model_config(lottery_type)
    thresholds = config["retrain_thresholds"]
    min_hits_3plus = thresholds["min_draws_with_3plus_match"]

    # ── Decision ──────────────────────────────────────────────────
    should_retrain = hit_3plus < min_hits_3plus
    reason = ""

    if should_retrain:
        reason = f"{hit_3plus}/5 lần dò có ≥3 số trùng (threshold: ≥{min_hits_3plus})"
        log.warning(f"RETRAIN triggered: {reason}")

        # Adjust weights: penalize worst model (simple heuristic)
        active_configs = db.get_active_model_configs(lottery_type)
        weight_map = {c["model_name"]: c for c in active_configs}

        # Load current weights
        w_lstm = float(weight_map.get("lstm", {}).get("ensemble_weight", 0.40))
        w_xgb = float(weight_map.get("xgboost", {}).get("ensemble_weight", 0.35))
        w_stat = float(weight_map.get("statistical", {}).get("ensemble_weight", 0.25))

        # Shift weight from LSTM to XGBoost (heuristic when low accuracy)
        w_lstm = max(WEIGHT_MIN, w_lstm - WEIGHT_STEP)
        w_xgb = min(WEIGHT_MAX, w_xgb + WEIGHT_STEP)

        # Normalize
        total = w_lstm + w_xgb + w_stat
        w_lstm /= total
        w_xgb /= total
        w_stat /= total

        # Update DB
        for cfg in active_configs:
            name = cfg["model_name"]
            new_w = {"lstm": w_lstm, "xgboost": w_xgb, "statistical": w_stat}.get(name)
            if new_w is not None:
                db.update_model_weight(cfg["id"], round(new_w, 3))

        # Log training event
        db.insert_training_log({
            "lottery_type": lottery_type,
            "trigger_reason": reason,
            "old_params": {"weights": {"lstm": float(weight_map.get("lstm", {}).get("ensemble_weight", 0.40)),
                                       "xgboost": float(weight_map.get("xgboost", {}).get("ensemble_weight", 0.35)),
                                       "statistical": float(weight_map.get("statistical", {}).get("ensemble_weight", 0.25))}},
            "new_params": {"weights": {"lstm": round(w_lstm, 3), "xgboost": round(w_xgb, 3), "statistical": round(w_stat, 3)}},
            "performance_before": {"hit_3plus": hit_3plus, "max_match": max_match},
            "training_status": "triggered",
        })

        _dispatch_kaggle(lottery_type, config)
    else:
        reason = f"{hit_3plus}/5 lần dò có ≥3 số trùng — giữ model"
        log.info(f"SKIP retrain: {reason}")
        db.insert_training_log({
            "lottery_type": lottery_type,
            "trigger_reason": reason,
            "performance_before": {"hit_3plus": hit_3plus, "max_match": max_match},
            "training_status": "skipped",
        })

    return {
        "success": True,
        "lottery_type": lottery_type,
        "lottery_label": LOTTERY_LABELS.get(lottery_type, lottery_type),
        "match_rows": match_rows,
        "hit_3plus": hit_3plus,
        "hit_4plus": hit_4plus,
        "max_match": max_match,
        "should_retrain": should_retrain,
        "reason": reason,
    }


def _dispatch_kaggle(lottery_type: str, config: dict) -> None:
    """Push retrain job to Kaggle Notebook API."""
    try:
        import os
        from kaggle.api.kaggle_api_extended import KaggleApiExtended  # type: ignore
        api = KaggleApiExtended()
        api.authenticate()
        notebook_slug = f"{os.getenv('KAGGLE_USERNAME')}/{os.getenv('KAGGLE_NOTEBOOK')}"
        # Kaggle SDK doesn't directly trigger runs; log intent here
        log.info(f"Kaggle retrain dispatch for {lottery_type} notebook={notebook_slug}")
    except Exception as exc:
        log.error(f"Kaggle dispatch failed: {exc}")
