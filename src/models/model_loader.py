"""
src/models/model_loader.py
Download model files from Supabase Storage and instantiate predictors.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from src.utils.config import SUPABASE_STORAGE_BUCKET, get_model_config
from src.utils.logger import get_logger
from src.utils.supabase_client import get_client

log = get_logger("model_loader")

LOCAL_CACHE = Path(tempfile.gettempdir()) / "vietlott_models"


def _download_file(remote_path: str, local_path: Path) -> bool:
    """Download a file from Supabase Storage to a local path."""
    try:
        db = get_client()
        data = db.storage.from_(SUPABASE_STORAGE_BUCKET).download(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        log.info(f"Downloaded {remote_path} → {local_path}")
        return True
    except Exception as exc:
        log.error(f"Failed to download {remote_path}: {exc}")
        return False


def load_ensemble(lottery_type: str, version: str = "latest") -> "EnsemblePredictor":  # type: ignore[name-defined]
    """
    Load all model files for a lottery type and return a ready EnsemblePredictor.
    Falls back to statistical-only if ML models are unavailable.
    """
    from src.models.ensemble_predictor import EnsemblePredictor

    config = get_model_config(lottery_type)
    ensemble = EnsemblePredictor(lottery_type=lottery_type, config=config)

    base_remote = f"models/{version}/{lottery_type}"
    base_local = LOCAL_CACHE / version / lottery_type

    # LSTM
    lstm_remote = f"{base_remote}/lstm.h5"
    lstm_local = base_local / "lstm.h5"
    if _download_file(lstm_remote, lstm_local):
        try:
            ensemble.lstm.load(str(lstm_local))
        except Exception as exc:
            log.warning(f"LSTM load failed: {exc} — using statistical fallback")

    # XGBoost
    xgb_remote = f"{base_remote}/xgboost.pkl"
    xgb_local = base_local / "xgboost.pkl"
    if _download_file(xgb_remote, xgb_local):
        try:
            ensemble.xgboost.load(str(xgb_local))
        except Exception as exc:
            log.warning(f"XGBoost load failed: {exc}")

    # Markov Chain
    mc_remote = f"{base_remote}/markov.pkl"
    mc_local = base_local / "markov.pkl"
    if _download_file(mc_remote, mc_local):
        try:
            ensemble.markov.load(str(mc_local))
        except Exception as exc:
            log.warning(f"Markov load failed: {exc}")

    log.info(f"EnsemblePredictor ready for {lottery_type}")
    return ensemble
