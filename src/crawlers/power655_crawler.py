"""
src/crawlers/power655_crawler.py
Crawler for Vietlott Power 6/55.
Draw schedule: Tuesday, Thursday, Saturday at 18:00 ICT.
Numbers: 6 from 1–55 + 1 bonus (jackpot2) from 1–55.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.power655")

class Power655Crawler(BaseCrawler):
    """Scrape Power 6/55 results from vietvudanh open-source JSONL data."""

    API_URL = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="power_655", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 55)

    def _fetch_all(self) -> list[dict[str, Any]]:
        resp = self._get(self.API_URL)
        if not resp:
            return []
            
        results = []
        for line in resp.text.strip().split('\n'):
            if not line: continue
            
            try:
                data = json.loads(line)
                nums = data.get("result", [])
                
                if len(nums) >= 7:
                    record = {
                        "draw_id": str(int(data.get("id", 0))),
                        "lottery_type": self.lottery_type,
                        "draw_date": data.get("date"),
                        "numbers": sorted(nums[:6]),
                        "jackpot2": nums[6],
                        "jackpot_amount": None,
                    }
                    if self.validate_draw(record):
                        results.append(record)
            except Exception as e:
                log.debug(f"JSONL parse error: {e}")
                
        # Reverse to return newest first
        return results[::-1]

    def fetch_latest(self) -> dict[str, Any] | None:
        results = self._fetch_all()
        return results[0] if results else None

    def fetch_draw(self, draw_id: str) -> dict[str, Any] | None:
        draw_id_str = str(int(draw_id))
        for record in self._fetch_all():
            if record["draw_id"] == draw_id_str:
                return record
        return None

    def fetch_date_range(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
        results: list[dict[str, Any]] = []

        for record in self._fetch_all():
            draw_dt = datetime.strptime(record["draw_date"], "%Y-%m-%d").date()
            if from_dt <= draw_dt <= to_dt:
                results.append(record)
            elif draw_dt < from_dt:
                break

        return results
