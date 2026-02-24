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
    API_URL = "https://www.minhchinh.com/truc-tiep-xo-so-tu-chon-lotto-535.html"

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
        """Scrape latest rows from Minh Chinh. Not efficient for deep history."""
        resp = self._get(self.API_URL)
        if not resp:
            return []
            
        soup = self._parse_html(resp.text)
        results = []
        
        target_table = None
        for table in soup.find_all('table'):
            if 'Ngày Mở Thưởng' in table.text and 'Kết Quả' in table.text:
                target_table = table
                break
                
        if not target_table:
            log.error("Could not find results table on Minh Chinh")
            return []

        rows = target_table.find_all('tr')
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 3:
                continue
                
            date_col = cols[0]
            link_tag = date_col.find('a')
            if not link_tag:
                continue
                
            raw_text = link_tag.get_text(strip=True) # e.g., "22/02/26 21h"
            parts = raw_text.split()
            if len(parts) < 2:
                continue
                
            # Date part: "22/02/26" -> need 2026
            date_str = parts[0]
            try:
                draw_date = datetime.strptime(date_str, "%d/%m/%y").strftime("%Y-%m-%d")
            except ValueError:
                continue
                
            # Session part: "21h" or "13h"
            session_str = parts[1].lower()
            if "13h" in session_str:
                session = self.SESSION_AM
            elif "21h" in session_str:
                session = self.SESSION_PM
            else:
                continue
                
            detail_url = "https://www.minhchinh.com" + link_tag['href']
            
            ball_container = cols[1]
            balls = ball_container.find_all('span', class_='mini-ball')
            nums = []
            jackpot2 = None
            for b in balls:
                try:
                    val = int(b.get_text(strip=True))
                    # Check if it has 'pw' class indicating the bonus box
                    if 'pw' in b.get('class', []):
                        jackpot2 = val
                    else:
                        nums.append(val)
                except ValueError:
                    pass
                    
            if len(nums) < 5:
                continue
                
            draw_id = self._fetch_draw_id_from_detail(detail_url)
            if not draw_id:
                continue
                
            record = {
                "draw_id": draw_id,
                "lottery_type": self.lottery_type,
                "draw_date": draw_date,
                "draw_time": "13:00" if session == "AM" else "21:00",
                "draw_session": session,
                "numbers": sorted(nums[:5]),
                "jackpot2": jackpot2,
                "jackpot_amount": None,
            }
            if self._validate_535(record):
                results.append(record)
                
        # Return oldest first
        return results[::-1]

    def _fetch_draw_id_from_detail(self, detail_url: str) -> str | None:
        self._sleep()
        resp = self._get(detail_url)
        if not resp:
            return None
            
        soup = self._parse_html(resp.text)
        for block in soup.find_all(string=lambda t: '#' in t if t else False):
            text = block.strip()
            if text.startswith('#') and text[1:].isdigit():
                return text[1:]
        return None

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
