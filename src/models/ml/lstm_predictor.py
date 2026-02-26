"""
src/models/ml/lstm_predictor.py
LSTM model for sequence pattern prediction over lottery history.
Predicts a score for each number based on a sliding window of 50 draws.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from src.utils.logger import get_logger

log = get_logger("model.lstm")


class LSTMPredictor:
    """
    Keras LSTM model that learns sequential patterns from lottery draws.
    Outputs a probability score per number.
    """

    def __init__(self, number_range: tuple[int, int], params: dict[str, Any]):
        self.lo, self.hi = number_range
        self.n_numbers = self.hi - self.lo + 1
        self.params = params
        self.model = None
        self._built = False

    # ── Model building ────────────────────────────────────────────

    def _build_model(self):
        """Lazy-import Keras to avoid loading TF when not training."""
        from tensorflow import keras  # type: ignore
        from tensorflow.keras import layers  # type: ignore

        seq_len = self.params.get("sequence_length", 50)
        hidden = self.params.get("hidden_units", 128)
        dropout = self.params.get("dropout_rate", 0.3)
        lr = self.params.get("learning_rate", 0.001)

        model = keras.Sequential([
            layers.Input(shape=(seq_len, self.n_numbers)),
            layers.LSTM(hidden, return_sequences=True),
            layers.Dropout(dropout),
            layers.LSTM(hidden // 2),
            layers.Dropout(dropout),
            layers.Dense(self.n_numbers, activation="sigmoid"),
        ])

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=lr),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )
        self.model = model
        self._built = True

    # ── Feature engineering ───────────────────────────────────────

    def _encode_draw(self, draw: list[int]) -> np.ndarray:
        """One-hot encode a single draw into vector of shape (n_numbers,)."""
        vec = np.zeros(self.n_numbers, dtype=np.float32)
        for num in draw:
            if self.lo <= num <= self.hi:
                vec[num - self.lo] = 1.0
        return vec

    def _prepare_sequences(self, history: list[list[int]]):
        """
        Build (X, y) sequences for LSTM training.
        X shape: (n_samples, seq_len, n_numbers)
        y shape: (n_samples, n_numbers)
        """
        seq_len = self.params.get("sequence_length", 50)
        encoded = [self._encode_draw(draw) for draw in reversed(history)]  # oldest first
        X, y = [], []
        for i in range(len(encoded) - seq_len):
            X.append(encoded[i: i + seq_len])
            y.append(encoded[i + seq_len])
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    # ── Training ──────────────────────────────────────────────────

    def train(self, history: list[list[int]]) -> dict[str, float]:
        """Train LSTM on full history. Returns final loss and accuracy."""
        if not self._built:
            self._build_model()

        X, y = self._prepare_sequences(history)
        if len(X) == 0:
            log.warning("Not enough data to train LSTM (need > sequence_length draws)")
            return {}

        val_split = 0.2
        epochs = self.params.get("epochs", 100)
        batch_size = self.params.get("batch_size", 32)

        history_obj = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=val_split,
            verbose=0,
        )

        final_loss = history_obj.history["val_loss"][-1]
        final_acc = history_obj.history.get("val_accuracy", [0])[-1]
        log.info(f"LSTM training done — val_loss={final_loss:.4f}, val_acc={final_acc:.4f}")
        return {"val_loss": final_loss, "val_accuracy": final_acc}

    # ── Prediction ────────────────────────────────────────────────

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """
        Get score for each number using the last `seq_len` draws.
        Returns {number: score} normalized to [0, 1].
        """
        if self.model is None:
            raise RuntimeError("LSTM model not loaded. Call train() or load() first.")

        seq_len = self.params.get("sequence_length", 50)
        recent = list(reversed(history[:seq_len]))  # oldest first
        while len(recent) < seq_len:
            recent.insert(0, [])  # pad with empty draws

        encoded = np.array([self._encode_draw(d) for d in recent], dtype=np.float32)
        X = encoded[np.newaxis, :, :]  # shape (1, seq_len, n_numbers)

        probs = self.model.predict(X, verbose=0)[0]  # shape (n_numbers,)
        return {self.lo + i: float(probs[i]) for i in range(self.n_numbers)}

    # ── Save / Load ───────────────────────────────────────────────

    def save(self, path: str) -> None:
        if self.model is None:
            raise RuntimeError("No model to save.")
        self.model.save(path)
        log.info(f"LSTM model saved to {path}")

    def load(self, path: str) -> None:
        from tensorflow import keras  # type: ignore
        self.model = keras.models.load_model(path)
        self._built = True
        log.info(f"LSTM model loaded from {path}")
