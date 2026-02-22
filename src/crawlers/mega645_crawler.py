"""
src/crawlers/mega645_crawler.py
Crawler for Vietlott Mega 6/45.
Draw schedule: Wednesday, Friday, Sunday at 18:00 ICT.
Numbers: 6 from 1–45. No bonus number.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.mega645")

class Mega645Crawler(BaseCrawler):
    """Scrape Mega 6/45 results from vietvudanh open-source JSONL data."""

    API_URL = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power645.jsonl"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="mega_645", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 45)

    def _fetch_all(self) -> list[dict[str, Any]]:
        """Download and parse the entire JSONL dataset."""
        resp = self._get(self.API_URL)
        if not resp:
            return []
            
        results = []
        for line in resp.text.strip().split('\n'):
            if not line: continue
            
            try:
                data = json.loads(line)
                nums = data.get("result", [])
                
                if len(nums) >= 6:
                    record = {
                        "draw_id": str(int(data.get("id", 0))),
                        "lottery_type": self.lottery_type,
                        "draw_date": data.get("date"),
                        "numbers": sorted(nums[:6]),
                        "jackpot2": None,
                        "jackpot_amount": None,
                    }
                    if self.validate_draw(record):
                        results.append(record)
            except Exception as e:
                log.debug(f"JSONL parse error: {e}")
                
        # The file is ordered oldest to newest, so we reversed it
        return results[::-1]

    def fetch_latest(self) -> dict[str, Any] | None:
        results = self._fetch_all()
        return results[0] if results else None

    def fetch_draw(self, draw_id: str) -> dict[str, Any] | None:
        draw_id_str = str(int(draw_id)) # normalize
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
                # Since results are newest to oldest, stop when we pass from_dt
                break

        return results
