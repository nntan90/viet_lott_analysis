"""
src/crawlers/power655_crawler.py
Crawler for Vietlott Power 6/55.
Draw schedule: Tuesday, Thursday, Saturday at 18:00 ICT.
Numbers: 6 from 1–55 + 1 bonus (jackpot2) from 1–55.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.power655")

# Vietlott page IDs used in the API
_PAGE_ID = "120"   # Power 6/55 page


class Power655Crawler(BaseCrawler):
    """Scrape Power 6/55 results from vietlott.vn."""

    API_URL = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/120"
    FALLBACK_API = "https://ketquaxoso.com/xo-so-vietlott-power-655"

    def __init__(self, **kwargs):
        super().__init__(lottery_type="power_655", **kwargs)

    @property
    def number_range(self) -> tuple[int, int]:
        return (1, 55)

    # ── Core fetch ────────────────────────────────────────────────

    def fetch_latest(self) -> dict[str, Any] | None:
        """Fetch the most recent Power 6/55 draw."""
        results = self._fetch_page(page=0)
        return results[0] if results else None

    def fetch_draw(self, draw_id: str) -> dict[str, Any] | None:
        """Fetch a single draw by draw_id (tries recent pages first)."""
        for page in range(10):
            for record in self._fetch_page(page=page):
                if record["draw_id"] == draw_id:
                    return record
            self._sleep()
        return None

    def fetch_date_range(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """
        Fetch all draws between from_date and to_date.
        Paginates through vietlott.vn until we exceed from_date.
        """
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
        results: list[dict[str, Any]] = []
        page = 0

        while True:
            draws = self._fetch_page(page=page)
            if not draws:
                log.warning(f"No draws on page {page}, stopping.")
                break

            for record in draws:
                draw_dt = datetime.strptime(record["draw_date"], "%Y-%m-%d").date()
                if from_dt <= draw_dt <= to_dt:
                    results.append(record)
                elif draw_dt < from_dt:
                    log.info(f"Reached from_date boundary at {draw_dt}. Done.")
                    return results

            page += 1
            self._sleep()

        return results

    # ── Internal page scraping ────────────────────────────────────

    def _fetch_page(self, page: int = 0) -> list[dict[str, Any]]:
        """Scrape one result page from vietlott.vn Power 6/55."""
        params = {"page": page}
        resp = self._get(self.API_URL, params=params)
        if resp is None:
            return []

        soup = self._parse_html(resp.text)
        return self._parse_rows(soup)

    def _parse_rows(self, soup) -> list[dict[str, Any]]:
        """Parse draw rows from the result table HTML."""
        draws = []
        rows = soup.select("table.result-table tbody tr, div.result-item")

        for row in rows:
            try:
                record = self._parse_single_row(row)
                if record and self.validate_draw(record):
                    draws.append(record)
            except Exception as exc:
                log.debug(f"Row parse error: {exc}")

        # Fallback: parse JSON embedded in script tags
        if not draws:
            draws = self._parse_json_embedded(soup)

        return draws

    def _parse_single_row(self, row) -> dict[str, Any] | None:
        """Parse a single table row into a draw record."""
        cells = row.find_all("td")
        if len(cells) < 3:
            return None

        # Draw ID
        draw_id_text = cells[0].get_text(strip=True)
        draw_id = re.sub(r"\D", "", draw_id_text)
        if not draw_id:
            return None

        # Date — format: dd/mm/yyyy or dd-mm-yyyy
        date_text = cells[1].get_text(strip=True)
        draw_date = self._parse_date(date_text)
        if not draw_date:
            return None

        # Numbers — look for number balls or comma-separated
        number_cells = cells[2:]
        numbers = []
        jackpot2 = None

        for i, cell in enumerate(number_cells):
            txt = cell.get_text(strip=True)
            nums = re.findall(r"\d+", txt)
            for n in nums:
                val = int(n)
                if 1 <= val <= 55:
                    numbers.append(val)

        # Power 6/55: first 6 = main numbers, 7th = jackpot2
        if len(numbers) >= 7:
            jackpot2 = numbers[6]
            numbers = numbers[:6]
        elif len(numbers) > 6:
            numbers = numbers[:6]

        if len(numbers) != 6:
            return None

        numbers.sort()

        # Jackpot amount (optional)
        jackpot_amount = None
        amount_tag = row.find(class_=re.compile(r"jackpot|prize|amount"))
        if amount_tag:
            amt_text = amount_tag.get_text(strip=True).replace(",", "").replace(".", "").replace("đ", "")
            amt_nums = re.findall(r"\d+", amt_text)
            if amt_nums:
                jackpot_amount = int(amt_nums[0])

        return {
            "draw_id": draw_id,
            "lottery_type": self.lottery_type,
            "draw_date": draw_date,
            "numbers": numbers,
            "jackpot2": jackpot2,
            "jackpot_amount": jackpot_amount,
        }

    def _parse_json_embedded(self, soup) -> list[dict[str, Any]]:
        """Try to extract JSON data embedded in page scripts as fallback."""
        import json as json_lib
        draws = []
        for script in soup.find_all("script"):
            text = script.string or ""
            # Look for JSON arrays with draw data
            matches = re.findall(r'\{"draw_id"\s*:\s*"(\d+)"[^}]+\}', text)
            for m in matches:
                try:
                    obj = json_lib.loads(m)
                    if "numbers" in obj:
                        draws.append(obj)
                except Exception:
                    pass
        return draws

    @staticmethod
    def _parse_date(text: str) -> str | None:
        """Parse various date string formats → 'YYYY-MM-DD'."""
        text = text.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
