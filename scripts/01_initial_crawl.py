"""
scripts/01_initial_crawl.py
Phase 1: One-time historical crawl — run locally.
Crawls 3 years of data for all lottery types and bulk-inserts into Supabase.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.lottery635_crawler import Lottery635Crawler
from src.crawlers.mega645_crawler import Mega645Crawler
from src.crawlers.power655_crawler import Power655Crawler
from src.utils import supabase_client as db
from src.utils.logger import get_logger

log = get_logger("initial_crawl")

CRAWLERS = {
    "power_655": Power655Crawler,
    "mega_645": Mega645Crawler,
    "lottery_635": Lottery635Crawler,
}


def run_crawl(
    lottery_type: str,
    from_date: str,
    to_date: str,
    dry_run: bool = False,
    backup_csv: bool = True,
) -> dict:
    log.info(f"[CRAWL] {lottery_type}: {from_date} → {to_date} | dry_run={dry_run}")

    CrawlerClass = CRAWLERS[lottery_type]
    crawler = CrawlerClass()

    draws = crawler.fetch_date_range(from_date, to_date)
    log.info(f"Fetched {len(draws)} draws for {lottery_type}")

    if not draws:
        return {"lottery_type": lottery_type, "fetched": 0, "inserted": 0}

    # ── Backup CSV ────────────────────────────────────────────────
    if backup_csv:
        Path("data").mkdir(exist_ok=True)
        csv_path = f"data/{lottery_type}_{from_date}_{to_date}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["draw_id", "lottery_type", "draw_date", "numbers", "jackpot2", "jackpot_amount"],
            )
            writer.writeheader()
            for row in draws:
                writer.writerow({**row, "numbers": str(row["numbers"])})
        log.info(f"CSV backup saved to {csv_path}")

    # ── Insert into Supabase ──────────────────────────────────────
    inserted = 0
    skipped = 0
    missing: list[str] = []

    for draw in draws:
        if dry_run:
            log.info(f"[DRY RUN] Would insert: {draw}")
            inserted += 1
            continue

        try:
            result = db.upsert_lottery_result(draw)
            if result:
                inserted += 1
            else:
                skipped += 1
        except Exception as exc:
            log.error(f"Insert failed draw_id={draw.get('draw_id')}: {exc}")
            missing.append(draw.get("draw_id", "?"))

    if missing:
        with open("missing_draws.txt", "a") as f:
            for m in missing:
                f.write(f"{lottery_type},{m}\n")
        log.warning(f"{len(missing)} draws failed — logged to missing_draws.txt")

    log.info(f"[DONE] {lottery_type}: fetched={len(draws)}, inserted={inserted}, skipped={skipped}")
    return {
        "lottery_type": lottery_type,
        "fetched": len(draws),
        "inserted": inserted,
        "skipped": skipped,
        "failed": len(missing),
    }


def main():
    parser = argparse.ArgumentParser(description="Vietlott Initial Historical Crawl")
    parser.add_argument("--lottery", choices=list(CRAWLERS.keys()) + ["all"], default="all")
    parser.add_argument("--days", type=int, default=1095, help="Days back from today (default: 3 years)")
    parser.add_argument("--from-date", default=None, help="Override from_date (YYYY-MM-DD)")
    parser.add_argument("--to-date", default=None, help="Override to_date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only, no DB writes")
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV backup")
    args = parser.parse_args()

    to_dt = date.today()
    from_dt = to_dt - timedelta(days=args.days)

    from_date = args.from_date or from_dt.strftime("%Y-%m-%d")
    to_date = args.to_date or to_dt.strftime("%Y-%m-%d")

    log.info(f"Initial crawl: {from_date} → {to_date}")

    targets = list(CRAWLERS.keys()) if args.lottery == "all" else [args.lottery]

    results = []
    for lt in targets:
        result = run_crawl(
            lottery_type=lt,
            from_date=from_date,
            to_date=to_date,
            dry_run=args.dry_run,
            backup_csv=not args.no_csv,
        )
        results.append(result)

    print("\n" + "=" * 60)
    print("INITIAL CRAWL SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r['lottery_type']:15s} | fetched={r['fetched']:4d} | inserted={r['inserted']:4d} | failed={r.get('failed', 0):2d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
