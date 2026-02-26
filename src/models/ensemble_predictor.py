"""
src/models/ensemble_predictor.py
Weighted voting ensemble: LSTM + XGBoost + Statistical → 6 numbers.
"""
from __future__ import annotations

from typing import Any

from src.models.ml.lstm_predictor import LSTMPredictor
from src.models.ml.markov_chain import MarkovChain
from src.models.ml.xgboost_predictor import XGBoostPredictor
from src.models.statistical.frequency_analyzer import FrequencyAnalyzer
from src.models.statistical.gap_analyzer import GapAnalyzer
from src.models.statistical.position_bias import PositionBiasAnalyzer
from src.utils.logger import get_logger

log = get_logger("ensemble")

WEIGHT_MIN = 0.10
WEIGHT_MAX = 0.60


class EnsemblePredictor:
    """
    Combines LSTM, XGBoost, Markov Chain, and Statistical analyzers
    via weighted voting to select the best 6 numbers.
    """

    def __init__(self, lottery_type: str, config: dict[str, Any]):
        self.lottery_type = lottery_type
        self.config = config
        number_range = tuple(config["number_range"])

        # Weights from config
        w = config["ensemble"]["weights"]
        self.w_lstm = w["lstm"]
        self.w_xgb = w["xgboost"]
        self.w_stat = w["statistical"]

        # Validate weights sum ~1.0
        total = self.w_lstm + self.w_xgb + self.w_stat
        if abs(total - 1.0) > 0.01:
            log.warning(f"Ensemble weights sum to {total:.3f}, normalizing.")
            self.w_lstm /= total
            self.w_xgb /= total
            self.w_stat /= total

        # Statistical models (no ML, always available)
        self.freq_analyzer = FrequencyAnalyzer(
            number_range=number_range,
            window=config["statistical"]["frequency_window"],
            weight_recency=config["statistical"]["weight_recency"],
        )
        self.gap_analyzer = GapAnalyzer(
            number_range=number_range,
            window=config["statistical"]["gap_window"],
        )
        self.position_bias = PositionBiasAnalyzer(
            number_range=number_range,
            position_balance=config["ensemble"]["position_balance"],
        )

        # ML models (must be loaded before predict)
        self.lstm = LSTMPredictor(number_range=number_range, params=config["lstm"])
        self.xgboost = XGBoostPredictor(number_range=number_range, params=config["xgboost"])
        self.markov = MarkovChain(number_range=number_range, params=config["markov_chain"])

        self.lo, self.hi = number_range

    # ── Weights ───────────────────────────────────────────────────

    def update_weights(self, lstm_w: float, xgb_w: float, stat_w: float) -> None:
        """Adjust ensemble weights with min/max constraints."""
        self.w_lstm = max(WEIGHT_MIN, min(WEIGHT_MAX, lstm_w))
        self.w_xgb = max(WEIGHT_MIN, min(WEIGHT_MAX, xgb_w))
        self.w_stat = max(WEIGHT_MIN, min(WEIGHT_MAX, stat_w))
        # Normalize
        total = self.w_lstm + self.w_xgb + self.w_stat
        self.w_lstm /= total
        self.w_xgb /= total
        self.w_stat /= total
        log.info(f"Weights updated: LSTM={self.w_lstm:.3f} XGB={self.w_xgb:.3f} STAT={self.w_stat:.3f}")

    # ── Prediction ────────────────────────────────────────────────

    def predict(self, history: list[list[int]], n_picks: int = 6) -> list[int]:
        """
        Run all models, combine scores, return top n_picks balanced numbers.
        """
        if len(history) == 0:
            raise ValueError("No history provided to predict.")

        # Statistical scores
        freq_scores = self.freq_analyzer.get_scores(history)
        gap_scores = self.gap_analyzer.get_scores(history)
        pos_scores = self.position_bias.get_scores(history)
        stat_scores = {
            n: (freq_scores[n] + gap_scores[n] + pos_scores[n]) / 3
            for n in range(self.lo, self.hi + 1)
        }

        # ML scores (gracefully degrade if model not loaded)
        try:
            lstm_scores = self.lstm.get_scores(history)
        except RuntimeError:
            log.warning("LSTM not loaded — using statistical fallback.")
            lstm_scores = stat_scores

        try:
            xgb_scores = self.xgboost.get_scores(history)
        except RuntimeError:
            log.warning("XGBoost not loaded — using statistical fallback.")
            xgb_scores = stat_scores

        try:
            markov_scores = self.markov.get_scores(history)
        except RuntimeError:
            log.warning("Markov not loaded — using uniform.")
            markov_scores = {n: 1.0 / (self.hi - self.lo + 1) for n in range(self.lo, self.hi + 1)}

        # Blend XGBoost and Markov into "xgb" slot (50/50)
        xgb_blended = {
            n: (xgb_scores[n] + markov_scores[n]) / 2
            for n in range(self.lo, self.hi + 1)
        }

        # Final weighted score
        final_scores: dict[int, float] = {}
        for num in range(self.lo, self.hi + 1):
            final_scores[num] = (
                self.w_lstm * lstm_scores.get(num, 0)
                + self.w_xgb * xgb_blended.get(num, 0)
                + self.w_stat * stat_scores.get(num, 0)
            )

        # Sort by score, take top candidates
        top_candidates = sorted(final_scores, key=lambda n: final_scores[n], reverse=True)

        # Apply position balance enforcement
        balanced = self.position_bias.pick_balanced(top_candidates, n=n_picks)
        log.info(f"Ensemble prediction: {balanced}")
        return balanced

    def get_model_version(self) -> str:
        return self.config.get("version", "3.0")
