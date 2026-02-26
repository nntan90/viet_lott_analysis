"""
src/models/statistical/frequency_analyzer.py
Hot/cold number scoring based on frequency in the last N draws.
"""
from __future__ import annotations

import numpy as np


class FrequencyAnalyzer:
    """Score each number by how often it appears in recent draws."""

    def __init__(self, number_range: tuple[int, int], window: int = 100, weight_recency: float = 0.6):
        self.lo, self.hi = number_range
        self.window = window
        self.weight_recency = weight_recency  # recency decay factor

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """
        Returns a score dict {number: score} for all numbers in range.
        Higher score = more frequent recently (hot).
        """
        recent = history[: self.window]
        n_draws = len(recent)
        if n_draws == 0:
            return {n: 1.0 for n in range(self.lo, self.hi + 1)}

        scores: dict[int, float] = {n: 0.0 for n in range(self.lo, self.hi + 1)}

        for draw_idx, draw in enumerate(recent):
            # More recent draws get higher weight
            recency_weight = self.weight_recency ** draw_idx
            for num in draw:
                if self.lo <= num <= self.hi:
                    scores[num] += recency_weight

        # Normalize to [0, 1]
        max_score = max(scores.values()) or 1.0
        return {n: v / max_score for n, v in scores.items()}

    def get_hot_numbers(self, history: list[list[int]], top_n: int = 15) -> list[int]:
        scores = self.get_scores(history)
        return sorted(scores, key=lambda n: scores[n], reverse=True)[:top_n]

    def get_cold_numbers(self, history: list[list[int]], bottom_n: int = 15) -> list[int]:
        scores = self.get_scores(history)
        return sorted(scores, key=lambda n: scores[n])[:bottom_n]
