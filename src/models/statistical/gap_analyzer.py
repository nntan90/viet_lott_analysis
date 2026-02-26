"""
src/models/statistical/gap_analyzer.py
Score numbers by their gap (draws since last appearance).
Numbers with larger-than-average gaps are "overdue".
"""
from __future__ import annotations


class GapAnalyzer:
    """Score each number based on draws since last appearance."""

    def __init__(self, number_range: tuple[int, int], window: int = 50):
        self.lo, self.hi = number_range
        self.window = window

    def get_gaps(self, history: list[list[int]]) -> dict[int, int]:
        """
        Returns {number: draws_since_last_appearance}.
        If never seen in window, gap = window + 1 (extremely overdue).
        """
        recent = history[: self.window]
        gaps: dict[int, int] = {}

        for num in range(self.lo, self.hi + 1):
            gap = None
            for idx, draw in enumerate(recent):
                if num in draw:
                    gap = idx
                    break
            gaps[num] = gap if gap is not None else self.window + 1

        return gaps

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """
        Numbers with above-average gap → higher score (overdue).
        Normalized to [0, 1].
        """
        gaps = self.get_gaps(history)
        avg_gap = sum(gaps.values()) / len(gaps) if gaps else 1

        scores = {n: g / avg_gap for n, g in gaps.items()}
        max_score = max(scores.values()) or 1.0
        return {n: v / max_score for n, v in scores.items()}

    def get_overdue_numbers(self, history: list[list[int]], top_n: int = 15) -> list[int]:
        scores = self.get_scores(history)
        return sorted(scores, key=lambda n: scores[n], reverse=True)[:top_n]
