"""
scripts/01_initial_crawl.py  — v4.0
Phase 1: One-time historical crawl — run locally.
Crawls 3 years of data for all lottery types and bulk-inserts into Supabase.
Lotto 5/35: crawls both AM and PM sessions per day.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.lotto535_crawler import Lotto535Crawler
from src.crawlers.mega645_crawler import Mega645Crawler
from src.crawlers.power655_crawler import Power655Crawler
from src.utils import supabase_client as db
from src.utils.logger import get_logger

log = get_logger("initial_crawl")

CRAWLERS = {
    "power_655": Power655Crawler,
    "mega_645": Mega645Crawler,
    "lotto_535": Lotto535Crawler,   # v4.0: was lottery_635
}


def run_crawl(lottery_type: str, from_date: str, to_date: str,
              dry_run: bool = False, backup_csv: bool = True) -> dict:
    log.info(f"[CRAWL] {lottery_type}: {from_date} → {to_date} | dry_run={dry_run}")

    CrawlerClass = CRAWLERS[lottery_type]
    crawler = CrawlerClass()

    # lotto_535: crawl both AM and PM sessions
    if lottery_type == "lotto_535":
        draws: list[dict] = []
        for session in ["AM", "PM"]:
            session_draws = crawler.fetch_date_range(from_date, to_date, session=session)
            log.info(f"  {session}: {len(session_draws)} draws")
            draws.extend(session_draws)
    else:
        draws = crawler.fetch_date_range(from_date, to_date)

    log.info(f"Fetched {len(draws)} total draws for {lottery_type}")
    if not draws:
        return {"lottery_type": lottery_type, "fetched": 0, "inserted": 0}

    # CSV backup
    if backup_csv:
        Path("data").mkdir(exist_ok=True)
        csv_path = f"data/{lottery_type}_{from_date}_{to_date}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["draw_id", "lottery_type", "draw_date", "draw_time",
                                "draw_session", "numbers", "jackpot2", "jackpot_amount"],
            )
            writer.writeheader()
            for row in draws:
                writer.writerow({**row, "numbers": str(row.get("numbers", []))})
        log.info(f"CSV backup → {csv_path}")

    # Insert into Supabase
    inserted, skipped, missing = 0, 0, []
    for draw in draws:
        if dry_run:
            log.info(f"[DRY RUN] {draw}")
            inserted += 1
            continue
        try:
            result = db.upsert_lottery_result(draw)
            if result:
                inserted += 1
            else:
                skipped += 1
        except Exception as exc:
            log.error(f"Insert failed draw_id={draw.get('draw_id')} session={draw.get('draw_session')}: {exc}")
            missing.append(f"{draw.get('draw_id')}/{draw.get('draw_session', '')}")

    if missing:
        with open("missing_draws.txt", "a") as f:
            for m in missing:
                f.write(f"{lottery_type},{m}\n")
        log.warning(f"{len(missing)} draws failed → missing_draws.txt")

    log.info(f"[DONE] {lottery_type}: fetched={len(draws)}, inserted={inserted}, skipped={skipped}")
    return {"lottery_type": lottery_type, "fetched": len(draws),
            "inserted": inserted, "skipped": skipped, "failed": len(missing)}


def main():
    parser = argparse.ArgumentParser(description="Vietlott Initial Historical Crawl v4.0")
    parser.add_argument("--lottery", choices=list(CRAWLERS.keys()) + ["all"], default="all")
    parser.add_argument("--days", type=int, default=1095, help="Days back from today (default 3 years)")
    parser.add_argument("--from-date", default=None)
    parser.add_argument("--to-date", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    to_dt = date.today()
    from_dt = to_dt - timedelta(days=args.days)
    from_date = args.from_date or from_dt.strftime("%Y-%m-%d")
    to_date = args.to_date or to_dt.strftime("%Y-%m-%d")

    log.info(f"Initial crawl v4.0: {from_date} → {to_date}")
    targets = list(CRAWLERS.keys()) if args.lottery == "all" else [args.lottery]

    results = []
    for lt in targets:
        result = run_crawl(lt, from_date, to_date, dry_run=args.dry_run, backup_csv=not args.no_csv)
        results.append(result)

    print("\n" + "=" * 65)
    print("INITIAL CRAWL v4.0 SUMMARY")
    print("=" * 65)
    for r in results:
        print(f"  {r['lottery_type']:12s} | fetched={r['fetched']:4d} | inserted={r['inserted']:4d} | failed={r.get('failed',0):2d}")
    print("=" * 65)


if __name__ == "__main__":
    main()
