"""
src/models/ml/xgboost_predictor.py
XGBoost predictor using frequency, recency, and gap features per number.
"""
from __future__ import annotations

import pickle
from typing import Any

import numpy as np

from src.utils.logger import get_logger

log = get_logger("model.xgboost")


class XGBoostPredictor:
    """
    XGBoost model that scores each number based on engineered features:
    - frequency in last N draws
    - recency (draws ago since last seen)
    - gap delta (current gap vs average gap)
    - position in range (normalized)
    """

    def __init__(self, number_range: tuple[int, int], params: dict[str, Any]):
        self.lo, self.hi = number_range
        self.params = params
        self.model = None

    def _build_features(self, history: list[list[int]], number: int) -> list[float]:
        """Build feature vector for a single number given history."""
        window = self.params.get("feature_window", 20)
        recent = history[:window]

        # Frequency in window
        freq = sum(1 for draw in recent if number in draw) / (len(recent) or 1)

        # Recency: draws since last seen (0 = in last draw)
        recency = window + 1
        for idx, draw in enumerate(history):
            if number in draw:
                recency = idx
                break
        recency_norm = recency / (window + 1)

        # Gap delta: compared to average gap
        gaps = []
        last_seen = None
        for idx, draw in enumerate(history[:100]):
            if number in draw:
                if last_seen is not None:
                    gaps.append(idx - last_seen)
                last_seen = idx
        avg_gap = np.mean(gaps) if gaps else window
        current_gap = recency
        gap_delta = (current_gap - avg_gap) / (avg_gap or 1)

        # Position in range
        pos_norm = (number - self.lo) / (self.hi - self.lo)

        return [freq, recency_norm, gap_delta, pos_norm]

    def _build_training_data(self, history: list[list[int]]):
        """Build X (features) and y (labels) for training."""
        X, y = [], []
        # Use each draw as a label: numbers in it = 1, others = 0
        for i, draw in enumerate(history[1:], start=1):
            context = history[i:]  # history before this draw
            for num in range(self.lo, self.hi + 1):
                feats = self._build_features(context, num)
                label = 1 if num in draw else 0
                X.append(feats)
                y.append(label)
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.int8)

    def train(self, history: list[list[int]]) -> dict[str, float]:
        """Train XGBoost. Returns basic metrics."""
        from xgboost import XGBClassifier  # type: ignore
        from sklearn.model_selection import train_test_split  # type: ignore
        from sklearn.metrics import roc_auc_score  # type: ignore

        X, y = self._build_training_data(history)
        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = XGBClassifier(
            n_estimators=self.params.get("n_estimators", 200),
            max_depth=self.params.get("max_depth", 6),
            learning_rate=self.params.get("learning_rate", 0.05),
            subsample=self.params.get("subsample", 0.8),
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
        )
        self.model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

        y_pred = self.model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_pred)
        log.info(f"XGBoost training done — val_auc={auc:.4f}")
        return {"val_auc": auc}

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """Return {number: probability} for all numbers in range."""
        if self.model is None:
            raise RuntimeError("XGBoost model not loaded.")

        feature_matrix = [
            self._build_features(history, num)
            for num in range(self.lo, self.hi + 1)
        ]
        X = np.array(feature_matrix, dtype=np.float32)
        probs = self.model.predict_proba(X)[:, 1]
        return {self.lo + i: float(probs[i]) for i in range(len(probs))}

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        log.info(f"XGBoost model saved to {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        log.info(f"XGBoost model loaded from {path}")
