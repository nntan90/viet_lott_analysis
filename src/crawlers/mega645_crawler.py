"""
src/crawlers/mega645_crawler.py
Crawler for Vietlott Mega 6/45.
Draw schedule: Wednesday, Friday, Sunday at 18:00 ICT.
Numbers: 6 from 1–45. No bonus number.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.mega645")


class Mega645Crawler(BaseCrawler):
    """Scrape Mega 6/45 results from vietlott.vn."""

    API_URL = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/119"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="mega_645", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 45)

    def fetch_latest(self) -> dict[str, Any] | None:
        results = self._fetch_page(page=0)
        return results[0] if results else None

    def fetch_draw(self, draw_id: str) -> dict[str, Any] | None:
        for page in range(10):
            for record in self._fetch_page(page=page):
                if record["draw_id"] == draw_id:
                    return record
            self._sleep()
        return None

    def fetch_date_range(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
        results: list[dict[str, Any]] = []
        page = 0

        while True:
            draws = self._fetch_page(page=page)
            if not draws:
                break

            for record in draws:
                draw_dt = datetime.strptime(record["draw_date"], "%Y-%m-%d").date()
                if from_dt <= draw_dt <= to_dt:
                    results.append(record)
                elif draw_dt < from_dt:
                    return results

            page += 1
            self._sleep()

        return results

    def _fetch_page(self, page: int = 0) -> list[dict[str, Any]]:
        resp = self._get(self.API_URL, params={"page": page})
        if resp is None:
            return []
        soup = self._parse_html(resp.text)
        return self._parse_rows(soup)

    def _parse_rows(self, soup) -> list[dict[str, Any]]:
        draws = []
        rows = soup.select("table.result-table tbody tr, div.result-item")
        for row in rows:
            try:
                record = self._parse_single_row(row)
                if record and self.validate_draw(record):
                    draws.append(record)
            except Exception as exc:
                log.debug(f"Row parse error: {exc}")
        return draws

    def _parse_single_row(self, row) -> dict[str, Any] | None:
        cells = row.find_all("td")
        if len(cells) < 3:
            return None

        draw_id = re.sub(r"\D", "", cells[0].get_text(strip=True))
        if not draw_id:
            return None

        draw_date = self._parse_date(cells[1].get_text(strip=True))
        if not draw_date:
            return None

        numbers = []
        for cell in cells[2:]:
            for n in re.findall(r"\d+", cell.get_text(strip=True)):
                val = int(n)
                if 1 <= val <= 45:
                    numbers.append(val)
        numbers = sorted(numbers[:6])
        if len(numbers) != 6:
            return None

        return {
            "draw_id": draw_id,
            "lottery_type": self.lottery_type,
            "draw_date": draw_date,
            "numbers": numbers,
            "jackpot2": None,
            "jackpot_amount": None,
        }

    @staticmethod
    def _parse_date(text: str) -> str | None:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
