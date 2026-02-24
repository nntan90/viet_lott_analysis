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
    API_URL = "https://www.minhchinh.com/truc-tiep-xo-so-tu-chon-mega-645.html"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="mega_645", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 45)

    def _fetch_all(self) -> list[dict[str, Any]]:
        """Scrape latest rows from Minh Chinh. Not efficient for deep history."""
        resp = self._get(self.API_URL)
        if not resp:
            return []
            
        soup = self._parse_html(resp.text)
        results = []
        
        # Find the table containing 'Ngày Mở Thưởng' and 'Kết Quả'
        target_table = None
        for table in soup.find_all('table'):
            if 'Ngày Mở Thưởng' in table.text and 'Kết Quả' in table.text:
                target_table = table
                break
                
        if not target_table:
            log.error("Could not find results table on Minh Chinh")
            return []

        rows = target_table.find_all('tr')
        # Skip header row
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 3:
                continue
                
            # Date + Link
            date_col = cols[0]
            link_tag = date_col.find('a')
            if not link_tag:
                continue
                
            raw_date = link_tag.get_text(strip=True)  # DD/MM/YYYY
            try:
                draw_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue
                
            detail_url = "https://www.minhchinh.com" + link_tag['href']
            
            # Numbers
            ball_container = cols[1]
            balls = ball_container.find_all('span', class_='mini-ball')
            nums = []
            for b in balls:
                try:
                    val = int(b.get_text(strip=True))
                    nums.append(val)
                except ValueError:
                    pass
                    
            if len(nums) < 6:
                continue
                
            # Find Draw ID via 2-step request
            draw_id = self._fetch_draw_id_from_detail(detail_url)
            if not draw_id:
                continue
                
            record = {
                "draw_id": draw_id,
                "lottery_type": self.lottery_type,
                "draw_date": draw_date,
                "numbers": sorted(nums[:6]),
                "jackpot2": None,
                "jackpot_amount": None,
            }
            if self.validate_draw(record):
                results.append(record)
                
        # The site orders newest -> oldest. We reverse it so it's oldest -> newest.
        return results[::-1]

    def _fetch_draw_id_from_detail(self, detail_url: str) -> str | None:
        """Ping the detail page to extract the #1234 draw ID."""
        self._sleep() # Polite crawling
        resp = self._get(detail_url)
        if not resp:
            return None
            
        soup = self._parse_html(resp.text)
        # Look for the # marker
        for block in soup.find_all(string=lambda t: '#' in t if t else False):
            text = block.strip()
            if text.startswith('#') and text[1:].isdigit():
                return text[1:]
        return None

    def fetch_latest(self) -> dict[str, Any] | None:
        results = self._fetch_all()
        return results[-1] if results else None

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
