"""
scripts/04_custom_backfill.py
Drops (truncates) all lottery results and backfills:
- Mega 6/45 from draw 500 to present
- Power 6/55 from draw 500 to present
- Lotto 5/35 from draw 1 to present
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.lotto535_crawler import Lotto535Crawler
from src.crawlers.mega645_crawler import Mega645Crawler
from src.crawlers.power655_crawler import Power655Crawler
from src.utils import supabase_client as db
from src.utils.logger import get_logger

log = get_logger("backfill")

TARGETS = [
    ("mega_645", Mega645Crawler, 500),
    ("power_655", Power655Crawler, 500),
    ("lotto_535", Lotto535Crawler, 1),
]

def clear_database():
    log.info("Clearing existing lottery_results table...")
    client = db.get_client()
    # Delete everything by matching not null
    try:
        # Supabase Python client requires a filter for deletes.
        # This deletes where lottery_type is not some dummy value.
        client.table("lottery_results").delete().neq("lottery_type", "dummy_fake_type").execute()
        log.info("Database cleared.")
    except Exception as e:
        log.error(f"Failed to clear database: {e}")
        # Note: If it hits a timeout or constraint, we might need manual SQL

def run_backfill(lottery_type: str, CrawlerClass, min_draw_id: int):
    log.info(f"Starting backfill for {lottery_type} (Target min_draw_id >= {min_draw_id})")
    crawler = CrawlerClass()
    
    # We will fetch page by page until we see a draw_id < min_draw_id
    page = 0
    total_inserted = 0
    done = False
    
    while not done:
        draws = crawler._fetch_page(page=page)
        if not draws:
            log.warning(f"No draws returned on page {page}, stopping.")
            break
            
        for draw in draws:
            d_id = int(draw["draw_id"])
            if d_id < min_draw_id:
                log.info(f"Reached draw_id {d_id} < {min_draw_id}. Stopping pagination.")
                done = True
                continue
                
            if not done:
                try:
                    res = db.upsert_lottery_result(draw)
                    if res:
                        total_inserted += 1
                except Exception as e:
                    log.error(f"Failed to insert draw {d_id}: {e}")
                    
        log.info(f"  Processed page {page} ({len(draws)} items). Total inserted so far: {total_inserted}")
        page += 1
        crawler._sleep()

    log.info(f"[DONE] {lottery_type}: Inserted {total_inserted} rows.")

def main():
    clear_database()
    for lt_type, cls, min_id in TARGETS:
        run_backfill(lt_type, cls, min_id)

if __name__ == "__main__":
    main()
