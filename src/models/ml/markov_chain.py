"""
src/models/ml/markov_chain.py
2nd-order Markov chain for transition probability between numbers.
"""
from __future__ import annotations

import pickle
from collections import defaultdict
from typing import Any

from src.utils.logger import get_logger

log = get_logger("model.markov")


class MarkovChain:
    """
    2nd-order Markov Chain: P(next_set | prev_set, prev_prev_set).
    Tracks co-occurrence transitions between consecutive draws.
    Uses Laplace smoothing to avoid zero probabilities.
    """

    def __init__(self, number_range: tuple[int, int], params: dict[str, Any]):
        self.lo, self.hi = number_range
        self.order = params.get("order", 2)
        self.smoothing = params.get("smoothing", 0.01)
        # transition_counts[frozenset_of_prev_nums][num] = count
        self.transition_counts: dict = defaultdict(lambda: defaultdict(float))
        self.total_transitions: dict = defaultdict(float)
        self._trained = False

    def train(self, history: list[list[int]]) -> dict[str, float]:
        """Build transition counts from full history."""
        if len(history) <= self.order:
            log.warning("Not enough history for Markov chain training.")
            return {}

        # Work oldest-first
        chronological = list(reversed(history))

        for i in range(self.order, len(chronological)):
            # Key = frozenset of the previous draw (order=1 for simplicity + speed)
            prev_key = frozenset(chronological[i - 1])
            current = chronological[i]
            for num in current:
                self.transition_counts[prev_key][num] += 1
            self.total_transitions[prev_key] += len(current)

        self._trained = True
        log.info(f"Markov chain trained — {len(self.transition_counts)} transition states")
        return {"states": len(self.transition_counts)}

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """
        Score each number based on P(num | last_draw).
        Uses Laplace smoothing. Falls back to uniform if state unseen.
        """
        if not self._trained:
            raise RuntimeError("Markov chain not trained.")

        last_draw = frozenset(history[0])
        n_numbers = self.hi - self.lo + 1
        smoothing = self.smoothing

        scores: dict[int, float] = {}
        state_total = self.total_transitions.get(last_draw, 0)

        for num in range(self.lo, self.hi + 1):
            count = self.transition_counts.get(last_draw, {}).get(num, 0)
            # Laplace smoothing
            prob = (count + smoothing) / (state_total + smoothing * n_numbers)
            scores[num] = prob

        # Normalize
        total = sum(scores.values())
        return {n: v / total for n, v in scores.items()}

    def save(self, path: str) -> None:
        data = {
            "transition_counts": {str(k): dict(v) for k, v in self.transition_counts.items()},
            "total_transitions": {str(k): v for k, v in self.total_transitions.items()},
            "order": self.order,
            "smoothing": self.smoothing,
            "lo": self.lo,
            "hi": self.hi,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        log.info(f"Markov chain saved to {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.order = data["order"]
        self.smoothing = data["smoothing"]
        self.lo = data["lo"]
        self.hi = data["hi"]

        self.transition_counts = defaultdict(lambda: defaultdict(float))
        for k, v in data["transition_counts"].items():
            self.transition_counts[frozenset(map(int, k.strip("frozenset({})").split(", ")))] = defaultdict(float, v)

        self.total_transitions = defaultdict(float)
        for k, v in data["total_transitions"].items():
            self.total_transitions[frozenset(map(int, k.strip("frozenset({})").split(", ")))] = v

        self._trained = True
        log.info(f"Markov chain loaded from {path}")
