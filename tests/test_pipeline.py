"""tests/test_pipeline.py"""
import pytest
from unittest.mock import MagicMock, patch


class TestResultChecker:
    """Integration-style tests for result_checker using mocked Supabase."""

    @patch("src.pipeline.result_checker.db")
    def test_no_active_cycle_returns_error(self, mock_db):
        mock_db.get_active_cycle.return_value = None

        from src.pipeline.result_checker import check_result
        result = check_result("power_655", "01234")

        assert result["success"] is False
        assert "No active cycle" in result["error"]

    @patch("src.pipeline.result_checker.db")
    def test_missing_draw_returns_error(self, mock_db):
        mock_db.get_active_cycle.return_value = {
            "id": "cycle-uuid", "cycle_number": 1, "draws_tracked": 0
        }
        mock_db.get_prediction_for_cycle.return_value = {
            "numbers": [5, 14, 22, 33, 41, 52]
        }
        mock_db.get_result_by_draw_id.return_value = None

        from src.pipeline.result_checker import check_result
        result = check_result("power_655", "99999")

        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("src.pipeline.result_checker.advance_cycle")
    @patch("src.pipeline.result_checker.db")
    def test_successful_check(self, mock_db, mock_advance):
        mock_db.get_active_cycle.return_value = {
            "id": "cycle-uuid", "cycle_number": 1, "draws_tracked": 0
        }
        mock_db.get_prediction_for_cycle.return_value = {
            "id": "pred-uuid", "numbers": [5, 14, 22, 33, 41, 52]
        }
        mock_db.get_result_by_draw_id.return_value = {
            "draw_id": "01234",
            "draw_date": "2024-02-21",
            "numbers": [5, 9, 22, 30, 41, 49],
            "jackpot2": None,
        }
        mock_db.insert_match_result.return_value = {}
        mock_advance.return_value = {"draws_tracked": 1, "status": "active"}

        from src.pipeline.result_checker import check_result
        result = check_result("power_655", "01234")

        assert result["success"] is True
        assert result["matched_count"] == 3  # 5, 22, 41 match
        assert set(result["matched_numbers"]) == {5, 22, 41}


class TestCycleManager:
    @patch("src.pipeline.cycle_manager.db")
    def test_get_active_returns_existing(self, mock_db):
        mock_db.get_active_cycle.return_value = {
            "id": "existing-uuid", "cycle_number": 5, "draws_tracked": 2
        }
        from src.pipeline.cycle_manager import get_or_create_cycle
        cycle = get_or_create_cycle("power_655", "3.0")
        assert cycle["cycle_number"] == 5
        mock_db.create_prediction_cycle.assert_not_called()

    @patch("src.pipeline.cycle_manager.db")
    def test_creates_new_cycle_when_none(self, mock_db):
        mock_db.get_active_cycle.return_value = None
        mock_db.get_next_cycle_number.return_value = 1
        mock_db.create_prediction_cycle.return_value = {
            "id": "new-uuid", "cycle_number": 1, "draws_tracked": 0
        }
        from src.pipeline.cycle_manager import get_or_create_cycle
        cycle = get_or_create_cycle("power_655", "3.0")
        assert cycle["cycle_number"] == 1
        mock_db.create_prediction_cycle.assert_called_once()
