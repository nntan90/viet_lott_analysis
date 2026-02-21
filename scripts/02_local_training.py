"""
scripts/02_local_training.py
Phase 2: Train 3 models × 3 lottery types = 9 models locally.
Run after 01_initial_crawl.py has populated the DB.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.ml.lstm_predictor import LSTMPredictor
from src.models.ml.markov_chain import MarkovChain
from src.models.ml.xgboost_predictor import XGBoostPredictor
from src.utils import supabase_client as db
from src.utils.config import get_model_config
from src.utils.logger import get_logger

log = get_logger("local_training")

LOTTERY_TYPES = ["power_655", "mega_645", "lottery_635"]


def train_lottery(lottery_type: str, output_dir: Path) -> None:
    log.info(f"\n{'='*60}\nTraining models for {lottery_type}\n{'='*60}")

    config = get_model_config(lottery_type)
    number_range = tuple(config["number_range"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load history from Supabase
    log.info(f"Loading history for {lottery_type}...")
    rows = db.get_recent_results(lottery_type, limit=2000)
    history = [row["numbers"] for row in rows]
    log.info(f"Loaded {len(history)} draws")

    if len(history) < 60:
        log.warning(f"Not enough data ({len(history)} draws) for {lottery_type}. Skipping.")
        return

    # ── LSTM ──────────────────────────────────────────────────────
    log.info("Training LSTM...")
    lstm = LSTMPredictor(number_range=number_range, params=config["lstm"])
    lstm_metrics = lstm.train(history)
    lstm_path = str(output_dir / "lstm.h5")
    lstm.save(lstm_path)

    # ── XGBoost ───────────────────────────────────────────────────
    log.info("Training XGBoost...")
    xgb = XGBoostPredictor(number_range=number_range, params=config["xgboost"])
    xgb_metrics = xgb.train(history)
    xgb_path = str(output_dir / "xgboost.pkl")
    xgb.save(xgb_path)

    # ── Markov Chain ──────────────────────────────────────────────
    log.info("Training Markov Chain...")
    mc = MarkovChain(number_range=number_range, params=config["markov_chain"])
    mc_metrics = mc.train(history)
    mc_path = str(output_dir / "markov.pkl")
    mc.save(mc_path)

    log.info(
        f"[DONE] {lottery_type}\n"
        f"  LSTM:   {lstm_metrics}\n"
        f"  XGBoost: {xgb_metrics}\n"
        f"  Markov:  {mc_metrics}"
    )


def main():
    parser = argparse.ArgumentParser(description="Local model training")
    parser.add_argument("--lottery", choices=LOTTERY_TYPES + ["all"], default="all")
    parser.add_argument("--version", default="3.0", help="Model version tag")
    parser.add_argument("--output", default="models", help="Local output directory")
    args = parser.parse_args()

    output_base = Path(args.output)
    targets = LOTTERY_TYPES if args.lottery == "all" else [args.lottery]

    for lt in targets:
        output_dir = output_base / f"v{args.version}" / lt
        train_lottery(lt, output_dir)

    log.info("Training complete. Next: run 03_upload_models.py")


if __name__ == "__main__":
    main()
