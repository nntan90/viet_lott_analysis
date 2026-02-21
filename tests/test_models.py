"""tests/test_models.py"""
import pytest
from src.models.statistical.frequency_analyzer import FrequencyAnalyzer
from src.models.statistical.gap_analyzer import GapAnalyzer
from src.models.statistical.position_bias import PositionBiasAnalyzer
from src.models.ensemble_predictor import EnsemblePredictor


HISTORY_655 = [
    [5, 14, 22, 33, 41, 52],
    [3, 11, 19, 28, 37, 50],
    [7, 14, 24, 35, 43, 54],
    [2, 9, 22, 30, 41, 49],
    [8, 17, 25, 36, 44, 53],
]


class TestFrequencyAnalyzer:
    def setup_method(self):
        self.fa = FrequencyAnalyzer(number_range=(1, 55))

    def test_returns_all_numbers(self):
        scores = self.fa.get_scores(HISTORY_655)
        assert len(scores) == 55
        assert all(1 <= n <= 55 for n in scores)

    def test_scores_normalized(self):
        scores = self.fa.get_scores(HISTORY_655)
        assert max(scores.values()) <= 1.0
        assert min(scores.values()) >= 0.0

    def test_hot_numbers_are_frequent(self):
        hot = self.fa.get_hot_numbers(HISTORY_655, top_n=5)
        # 14, 22, 41 appear twice in HISTORY_655 → should be hot
        assert any(n in [14, 22, 41] for n in hot)


class TestGapAnalyzer:
    def setup_method(self):
        self.ga = GapAnalyzer(number_range=(1, 55))

    def test_scores_have_all_numbers(self):
        scores = self.ga.get_scores(HISTORY_655)
        assert len(scores) == 55

    def test_unseen_number_has_max_gap(self):
        gaps = self.ga.get_gaps(HISTORY_655)
        # Numbers not in any draw should have gap = window+1
        unseen = [n for n in range(1, 56) if all(n not in d for d in HISTORY_655)]
        if unseen:
            assert gaps[unseen[0]] == self.ga.window + 1


class TestPositionBias:
    def setup_method(self):
        self.pb = PositionBiasAnalyzer(
            number_range=(1, 55),
            position_balance={"low": [1, 18], "mid": [19, 36], "high": [37, 55]}
        )

    def test_all_numbers_have_zone(self):
        for n in range(1, 56):
            assert self.pb.get_zone(n) is not None

    def test_pick_balanced_returns_correct_count(self):
        candidates = list(range(1, 56))
        picked = self.pb.pick_balanced(candidates, n=6)
        assert len(picked) == 6

    def test_pick_balanced_sorted(self):
        candidates = list(range(1, 56))
        picked = self.pb.pick_balanced(candidates, n=6)
        assert picked == sorted(picked)


class TestEnsemblePredictor:
    def setup_method(self):
        import json
        from pathlib import Path
        config_path = Path("config/model_params_655.json")
        with open(config_path) as f:
            self.config = json.load(f)
        self.ensemble = EnsemblePredictor("power_655", self.config)

    def test_weight_sum_to_one(self):
        total = self.ensemble.w_lstm + self.ensemble.w_xgb + self.ensemble.w_stat
        assert abs(total - 1.0) < 0.001

    def test_update_weights_constraints(self):
        self.ensemble.update_weights(0.90, 0.90, 0.90)
        assert self.ensemble.w_lstm <= 0.60
        assert self.ensemble.w_xgb <= 0.60
        total = self.ensemble.w_lstm + self.ensemble.w_xgb + self.ensemble.w_stat
        assert abs(total - 1.0) < 0.001

    def test_predict_returns_6_numbers(self):
        # Extend history so statistical models work
        history = HISTORY_655 * 10
        nums = self.ensemble.predict(history, n_picks=6)
        assert len(nums) == 6

    def test_predict_numbers_in_range(self):
        history = HISTORY_655 * 10
        nums = self.ensemble.predict(history, n_picks=6)
        assert all(1 <= n <= 55 for n in nums)

    def test_predict_no_duplicates(self):
        history = HISTORY_655 * 10
        nums = self.ensemble.predict(history, n_picks=6)
        assert len(set(nums)) == 6
