"""
src/crawlers/lotto535_crawler.py  — v4.0
Crawler for Vietlott Lotto 5/35.
Schedule: Every day, 2 sessions — AM (13:00 ICT) and PM (21:00 ICT).
Numbers: 5 main from [1-35] + 1 special from [1-12].
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.crawlers.base_crawler import BaseCrawler
from src.utils.logger import get_logger

log = get_logger("crawler.lotto535")


class Lotto535Crawler(BaseCrawler):
    """Scrape Lotto 5/35 results from vietlott.vn (both AM and PM sessions)."""

    API_URL = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/123"

    # Session constants
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

    # ── Core fetch ────────────────────────────────────────────────

    def fetch_latest(self, session: str | None = None) -> dict[str, Any] | None:
        """Fetch the most recent draw. If session given, filter to that session."""
        results = self._fetch_page(page=0)
        for r in results:
            if session is None or r.get("draw_session") == session:
                return r
        return results[0] if results else None

    def fetch_draw(self, draw_id: str, session: str | None = None) -> dict[str, Any] | None:
        for page in range(15):
            for record in self._fetch_page(page=page):
                if record["draw_id"] == draw_id:
                    if session is None or record.get("draw_session") == session:
                        return record
            self._sleep()
        return None

    def fetch_date_range(self, from_date: str, to_date: str, session: str | None = None) -> list[dict[str, Any]]:
        """Fetch all draws in [from_date, to_date]. Optionally filter by session."""
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
                    if session is None or record.get("draw_session") == session:
                        results.append(record)
                elif draw_dt < from_dt:
                    return results
            page += 1
            self._sleep()

        return results

    def fetch_session(self, date_str: str, session: str) -> dict[str, Any] | None:
        """Fetch draw for a specific date and session (AM or PM)."""
        results = self.fetch_date_range(date_str, date_str, session=session)
        return results[0] if results else None

    # ── Internal page scraping ────────────────────────────────────

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
                if record and self._validate_535(record):
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

        # Determine session from draw_time embedded in row, or from time column
        draw_time_raw = ""
        session = None
        for cell in cells:
            txt = cell.get_text(strip=True)
            if "13:" in txt or "13h" in txt.lower():
                draw_time_raw = "13:00"
                session = self.SESSION_AM
                break
            elif "21:" in txt or "21h" in txt.lower():
                draw_time_raw = "21:00"
                session = self.SESSION_PM
                break

        # Extract main numbers [1-35]
        main_numbers = []
        special_number = None
        for cell in cells[2:]:
            txt = cell.get_text(strip=True)
            # Look for special marker
            is_special_cell = "special" in cell.get("class", []) or \
                              bool(cell.find(class_=re.compile(r"special|bonus|extra")))
            for n_txt in re.findall(r"\d+", txt):
                val = int(n_txt)
                if is_special_cell and 1 <= val <= 12:
                    special_number = val
                elif 1 <= val <= 35 and val not in main_numbers:
                    main_numbers.append(val)

        # If no special cell detected, assume last number ≤ 12 is special
        if special_number is None and main_numbers:
            candidates = [n for n in main_numbers if 1 <= n <= 12]
            if candidates:
                special_number = candidates[-1]
                main_numbers = [n for n in main_numbers if n != special_number]

        main_numbers = sorted(main_numbers[:5])
        if len(main_numbers) != 5:
            return None

        return {
            "draw_id": draw_id,
            "lottery_type": self.lottery_type,
            "draw_date": draw_date,
            "draw_time": draw_time_raw or None,
            "draw_session": session,
            "numbers": main_numbers,
            "jackpot2": special_number,   # stored in jackpot2 column for lotto_535
            "jackpot_amount": None,
        }

    def _validate_535(self, record: dict[str, Any]) -> bool:
        """Full validation for 5/35 record."""
        nums = record.get("numbers", [])
        special = record.get("jackpot2")
        lo, hi = self.number_range
        sp_lo, sp_hi = self.special_range

        if len(nums) != 5:
            log.error(f"Expected 5 main numbers, got {len(nums)}: {nums}")
            return False
        if len(set(nums)) != 5:
            log.error(f"Duplicate main numbers: {nums}")
            return False
        if not all(lo <= n <= hi for n in nums):
            log.error(f"Main numbers out of range [{lo},{hi}]: {nums}")
            return False
        if special is not None:
            if not (sp_lo <= special <= sp_hi):
                log.error(f"Special number out of range [{sp_lo},{sp_hi}]: {special}")
                return False
            if special in nums:
                log.error(f"Special number {special} conflicts with main numbers {nums}")
                return False

        required = {"draw_id", "lottery_type", "draw_date", "numbers"}
        if not required.issubset(record.keys()):
            return False
        return True

    @staticmethod
    def _parse_date(text: str) -> str | None:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
