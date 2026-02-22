import asyncio
import os
import json
from curl_cffi import requests
from src.utils import supabase_client as db

def backfill_mega(url, min_draw):
    print(f"[*] Backfilling mega_645 from {url}")
    r = requests.get(url, impersonate='chrome110')
    lines = r.text.strip().split('\n')
    total = 0
    client = db.get_client()
    for line in lines:
        if not line: continue
        data = json.loads(line)
        d_id = int(data.get("id", 0))
        if d_id < min_draw: continue
        
        nums = data.get("result", [])
        if len(nums) >= 6:
            rec = {
                "draw_id": str(d_id),
                "lottery_type": "mega_645",
                "draw_date": data.get("date"),
                "numbers": sorted(nums[:6])
            }
            try:
                db.upsert_lottery_result(rec)
                total += 1
            except Exception as e:
                print("Err:", e)
    print(f"[+] Done mega_645: {total} rows.")


def backfill_power(url, min_draw):
    print(f"[*] Backfilling power_655 from {url}")
    r = requests.get(url, impersonate='chrome110')
    lines = r.text.strip().split('\n')
    total = 0
    client = db.get_client()
    for line in lines:
        if not line: continue
        data = json.loads(line)
        d_id = int(data.get("id", 0))
        if d_id < min_draw: continue
        
        nums = data.get("result", [])
        if len(nums) >= 7:
            rec = {
                "draw_id": str(d_id),
                "lottery_type": "power_655",
                "draw_date": data.get("date"),
                "numbers": sorted(nums[:6]),
                "jackpot2": nums[6]
            }
            try:
                db.upsert_lottery_result(rec)
                total += 1
            except Exception as e:
                print("Err:", e)
    print(f"[+] Done power_655: {total} rows.")

def backfill_lotto(url, min_draw):
    print(f"[*] Backfilling lotto_535 from {url}")
    r = requests.get(url, impersonate='chrome110')
    lines = r.text.strip().split('\n')
    total = 0
    client = db.get_client()
    for line in lines:
        if not line: continue
        data = json.loads(line)
        d_id = int(data.get("id", 0))
        if d_id < min_draw: continue
        
        nums = data.get("result", [])
        if len(nums) >= 6:
            # First odds are AM, evens are PM based on sequential IDs
            session = "AM" if d_id % 2 != 0 else "PM"
            rec = {
                "draw_id": str(d_id),
                "lottery_type": "lotto_535",
                "draw_date": data.get("date"),
                "draw_session": session,
                "numbers": sorted(nums[:5]),
                "jackpot2": nums[5]
            }
            try:
                db.upsert_lottery_result(rec)
                total += 1
            except Exception as e:
                print("Err:", e)
    print(f"[+] Done lotto_535: {total} rows.")

if __name__ == "__main__":
    if os.environ.get('CLEAR_DB', 'true') == 'true':
        print("Clearing DB...")
        client = db.get_client()
        client.table("lottery_results").delete().neq("lottery_type", "dummy").execute()
    
    backfill_mega("https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power645.jsonl", int(os.environ.get('MIN_MEGA', 500)))
    backfill_power("https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl", int(os.environ.get('MIN_POWER', 500)))
    backfill_lotto("https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power535.jsonl", int(os.environ.get('MIN_LOTTO', 1)))
