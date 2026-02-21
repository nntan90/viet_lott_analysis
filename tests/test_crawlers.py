"""tests/test_crawlers.py"""
import pytest
from src.crawlers.power655_crawler import Power655Crawler
from src.crawlers.mega645_crawler import Mega645Crawler


class TestBaseCrawlerValidation:
    def setup_method(self):
        self.c655 = Power655Crawler()
        self.c645 = Mega645Crawler()

    def test_valid_power655_draw(self):
        record = {
            "draw_id": "01234",
            "lottery_type": "power_655",
            "draw_date": "2024-02-21",
            "numbers": [5, 14, 22, 33, 41, 52],
            "jackpot2": 44,
        }
        assert self.c655.validate_draw(record) is True

    def test_wrong_count(self):
        record = {
            "draw_id": "01234", "lottery_type": "power_655",
            "draw_date": "2024-02-21", "numbers": [5, 14, 22, 33],
        }
        assert self.c655.validate_draw(record) is False

    def test_duplicate_numbers(self):
        record = {
            "draw_id": "01234", "lottery_type": "power_655",
            "draw_date": "2024-02-21", "numbers": [5, 5, 22, 33, 41, 52],
        }
        assert self.c655.validate_draw(record) is False

    def test_out_of_range_655(self):
        record = {
            "draw_id": "01234", "lottery_type": "power_655",
            "draw_date": "2024-02-21", "numbers": [0, 14, 22, 33, 41, 56],
        }
        assert self.c655.validate_draw(record) is False

    def test_out_of_range_645(self):
        record = {
            "draw_id": "01234", "lottery_type": "mega_645",
            "draw_date": "2024-02-21", "numbers": [1, 14, 22, 33, 41, 46],  # 46 > 45
        }
        assert self.c645.validate_draw(record) is False

    def test_valid_mega645(self):
        record = {
            "draw_id": "5678", "lottery_type": "mega_645",
            "draw_date": "2024-02-21", "numbers": [3, 15, 22, 31, 40, 45],
        }
        assert self.c645.validate_draw(record) is True

    def test_missing_required_field(self):
        record = {"draw_id": "01234", "lottery_type": "power_655", "numbers": [1, 2, 3, 4, 5, 6]}
        assert self.c655.validate_draw(record) is False
