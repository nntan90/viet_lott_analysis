"""
src/crawlers/lotto535_crawler.py  — v4.0
Crawler for Vietlott Lotto 5/35.
Schedule: Every day, 2 sessions — AM (13:00 ICT) and PM (21:00 ICT).
Numbers: 5 main from [1-35] + 1 special from [1-12].
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.lotto535")

class Lotto535Crawler(BaseCrawler):
    """Scrape Lotto 5/35 results from vietvudanh open-source JSONL data."""

    API_URL = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power535.jsonl"

    SESSION_AM = "AM"
    SESSION_PM = "PM"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="lotto_535", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 35)

    @property
    def special_range(self) -> tuple[int, int]:
        return (1, 12)

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
                
                if len(nums) >= 6:
                    d_id = int(data.get("id", 0))
                    session = self.SESSION_AM if d_id % 2 != 0 else self.SESSION_PM
                    
                    record = {
                        "draw_id": str(d_id),
                        "lottery_type": self.lottery_type,
                        "draw_date": data.get("date"),
                        "draw_time": "13:00" if session == "AM" else "21:00",
                        "draw_session": session,
                        "numbers": sorted(nums[:5]),
                        "jackpot2": nums[5],
                        "jackpot_amount": None,
                    }
                    if self._validate_535(record):
                        results.append(record)
            except Exception as e:
                log.debug(f"JSONL parse error: {e}")
                
        # Reverse to return newest first
        return results[::-1]

    def _validate_535(self, record: dict[str, Any]) -> bool:
        nums = record.get("numbers", [])
        special = record.get("jackpot2")
        lo, hi = self.number_range
        sp_lo, sp_hi = self.special_range

        if len(nums) != 5: return False
        if len(set(nums)) != 5: return False
        if not all(lo <= n <= hi for n in nums): return False
        
        if special is not None:
            if not (sp_lo <= special <= sp_hi): return False
            if special in nums: return False
            
        return True

    def fetch_latest(self, session: str | None = None) -> dict[str, Any] | None:
        for r in self._fetch_all():
            if session is None or r.get("draw_session") == session:
                return r
        return None

    def fetch_draw(self, draw_id: str, session: str | None = None) -> dict[str, Any] | None:
        draw_id_str = str(int(draw_id))
        for record in self._fetch_all():
            if record["draw_id"] == draw_id_str:
                if session is None or record.get("draw_session") == session:
                    return record
        return None

    def fetch_date_range(self, from_date: str, to_date: str, session: str | None = None) -> list[dict[str, Any]]:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
        results: list[dict[str, Any]] = []

        for record in self._fetch_all():
            draw_dt = datetime.strptime(record["draw_date"], "%Y-%m-%d").date()
            if from_dt <= draw_dt <= to_dt:
                if session is None or record.get("draw_session") == session:
                    results.append(record)
            elif draw_dt < from_dt:
                break

        return results

    def fetch_session(self, date_str: str, session: str) -> dict[str, Any] | None:
        results = self.fetch_date_range(date_str, date_str, session=session)
        return results[0] if results else None
