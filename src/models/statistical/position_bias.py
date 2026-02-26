"""
src/models/statistical/position_bias.py
Score numbers based on their low/mid/high range distribution
compared to historical averages.
"""
from __future__ import annotations

from collections import Counter


class PositionBiasAnalyzer:
    """Analyze low/mid/high range distribution for balanced picks."""

    def __init__(self, number_range: tuple[int, int], position_balance: dict[str, list[int]]):
        """
        position_balance: {"low": [1, 18], "mid": [19, 36], "high": [37, 55]}
        """
        self.lo, self.hi = number_range
        self.bands = {
            zone: (bounds[0], bounds[1])
            for zone, bounds in position_balance.items()
        }

    def get_zone(self, num: int) -> str | None:
        for zone, (lo, hi) in self.bands.items():
            if lo <= num <= hi:
                return zone
        return None

    def get_zone_distribution(self, history: list[list[int]]) -> dict[str, float]:
        """Return fraction of picks in each zone across history."""
        counter: Counter = Counter()
        total = 0
        for draw in history:
            for num in draw:
                zone = self.get_zone(num)
                if zone:
                    counter[zone] += 1
                    total += 1
        if total == 0:
            even = 1.0 / len(self.bands)
            return {z: even for z in self.bands}
        return {z: counter.get(z, 0) / total for z in self.bands}

    def get_scores(self, history: list[list[int]]) -> dict[int, float]:
        """
        Numbers in under-represented zones get higher scores.
        """
        dist = self.get_zone_distribution(history)
        even = 1.0 / len(self.bands)

        # Zones with fewer picks than average are "needed"
        zone_score = {z: max(0.0, even - dist.get(z, 0)) + 0.01 for z in self.bands}

        scores: dict[int, float] = {}
        for num in range(self.lo, self.hi + 1):
            zone = self.get_zone(num)
            scores[num] = zone_score.get(zone, 0.01)

        max_score = max(scores.values()) or 1.0
        return {n: v / max_score for n, v in scores.items()}

    def pick_balanced(self, candidates: list[int], n: int = 6) -> list[int]:
        """
        From candidates, pick n numbers ensuring each zone is represented
        as evenly as possible.
        """
        target_per_zone = n // len(self.bands)
        remainder = n % len(self.bands)

        grouped: dict[str, list[int]] = {z: [] for z in self.bands}
        for num in candidates:
            zone = self.get_zone(num)
            if zone:
                grouped[zone].append(num)

        selected: list[int] = []
        for zone, nums in grouped.items():
            take = target_per_zone + (1 if remainder > 0 else 0)
            remainder = max(0, remainder - 1)
            selected.extend(nums[:take])

        # Fill remaining spots if needed
        while len(selected) < n:
            for num in candidates:
                if num not in selected:
                    selected.append(num)
                    break

        return sorted(selected[:n])
