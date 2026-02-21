"""
src/crawlers/base_crawler.py
Abstract base crawler with retry logic, rate limiting, and validation.
"""
from __future__ import annotations

import time
import random
from abc import ABC, abstractmethod
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.utils.logger import get_logger

log = get_logger("crawler")


class BaseCrawler(ABC):
    """Abstract base class for all Vietlott crawlers."""

    BASE_URL = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong"
    FALLBACK_URLS: list[str] = []

    def __init__(self, lottery_type: str, delay_min: float = 1.0, delay_max: float = 2.5, max_retries: int = 3):
        self.lottery_type = lottery_type
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    # ── HTTP helpers ──────────────────────────────────────────────

    def _get(self, url: str, params: dict | None = None, timeout: int = 15) -> requests.Response | None:
        """GET with retry + exponential backoff."""
        for attempt in range(1, self.max_retries + 1):
            try:
                log.debug(f"GET {url} params={params} (attempt {attempt})")
                resp = self.session.get(url, params=params, timeout=timeout)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                log.warning(f"Request failed (attempt {attempt}/{self.max_retries}): {exc}")
                if attempt < self.max_retries:
                    sleep_time = 2 ** attempt + random.uniform(0, 1)
                    time.sleep(sleep_time)
        log.error(f"All {self.max_retries} attempts failed for {url}")
        return None

    def _sleep(self) -> None:
        """Polite delay between requests."""
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def _parse_html(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    # ── Validation ────────────────────────────────────────────────

    def validate_draw(self, record: dict[str, Any]) -> bool:
        """Validate a draw record before inserting into DB."""
        required = {"draw_id", "lottery_type", "draw_date", "numbers"}
        if not required.issubset(record.keys()):
            log.error(f"Missing fields: {required - record.keys()}")
            return False

        nums = record["numbers"]
        lo, hi = self.number_range

        if len(nums) != 6:
            log.error(f"Expected 6 numbers, got {len(nums)}: {nums}")
            return False
        if len(set(nums)) != 6:
            log.error(f"Duplicate numbers: {nums}")
            return False
        if not all(lo <= n <= hi for n in nums):
            log.error(f"Numbers out of range [{lo},{hi}]: {nums}")
            return False

        return True

    # ── Abstract interface ────────────────────────────────────────

    @property
    @abstractmethod
    def number_range(self) -> tuple[int, int]:
        """Return (min_num, max_num)."""
        ...

    @abstractmethod
    def fetch_draw(self, draw_id: str) -> dict[str, Any] | None:
        """Fetch a single draw by draw_id."""
        ...

    @abstractmethod
    def fetch_date_range(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """Fetch all draws between from_date and to_date (YYYY-MM-DD)."""
        ...

    @abstractmethod
    def fetch_latest(self) -> dict[str, Any] | None:
        """Fetch the most recent draw."""
        ...
