"""
src/pipeline/result_checker.py
Phase 3c: Dò kết quả — compare active prediction vs latest draw result.
"""
from __future__ import annotations

from src.pipeline.cycle_manager import advance_cycle
from src.utils import supabase_client as db
from src.utils.config import LOTTERY_LABELS
from src.utils.logger import get_logger

log = get_logger("pipeline.checker")


def check_result(lottery_type: str, draw_id: str) -> dict:
    """
    Full Phase 3c flow:
    1. Load active cycle
    2. Load prediction for that cycle
    3. Load lottery result for draw_id
    4. Compute matched_numbers, matched_count
    5. Insert match_results row
    6. Advance draws_tracked
    7. Return result dict for Telegram
    """
    log.info(f"[CHECK] {lottery_type} draw={draw_id}")

    # Step 1: Active cycle
    cycle = db.get_active_cycle(lottery_type)
    if not cycle:
        msg = f"No active cycle for {lottery_type} — generate prediction first."
        log.warning(msg)
        return {"success": False, "error": msg}

    # Step 2: Prediction
    prediction = db.get_prediction_for_cycle(cycle["id"])
    if not prediction:
        msg = f"No prediction found for cycle {cycle['id']}"
        log.error(msg)
        return {"success": False, "error": msg}

    # Step 3: Lottery result
    result = db.get_result_by_draw_id(lottery_type, draw_id)
    if not result:
        msg = f"draw_id={draw_id} not found in lottery_results. Run crawl first."
        log.error(msg)
        return {"success": False, "error": msg}

    predicted_nums = prediction["numbers"]
    actual_numbers = result["numbers"]
    jackpot2 = result.get("jackpot2")

    # Step 4: Compute match
    matched = sorted(set(predicted_nums) & set(actual_numbers))
    matched_count = len(matched)

    draw_number = cycle["draws_tracked"] + 1  # 1-indexed

    # Step 5: Insert match_results
    match_row = db.insert_match_result({
        "cycle_id": cycle["id"],
        "lottery_type": lottery_type,
        "draw_id": draw_id,
        "draw_date": result["draw_date"],
        "draw_number": draw_number,
        "predicted_nums": predicted_nums,
        "actual_numbers": actual_numbers,
        "jackpot2": jackpot2,
        "matched_numbers": matched,
        "matched_count": matched_count,
    })

    # Step 6: Advance cycle
    updated_cycle = advance_cycle(cycle["id"], lottery_type)

    result_dict = {
        "success": True,
        "lottery_type": lottery_type,
        "lottery_label": LOTTERY_LABELS.get(lottery_type, lottery_type),
        "cycle_number": cycle["cycle_number"],
        "draw_id": draw_id,
        "draw_date": result["draw_date"],
        "draw_number": draw_number,
        "predicted_nums": predicted_nums,
        "actual_numbers": actual_numbers,
        "jackpot2": jackpot2,
        "matched_numbers": matched,
        "matched_count": matched_count,
        "draws_tracked": updated_cycle["draws_tracked"],
        "cycle_complete": updated_cycle.get("status") == "completed",
    }
    log.info(f"[CHECK] {lottery_type} lần {draw_number}/5 → {matched_count}/6 trùng {matched}")
    return result_dict


def _match_icon(matched_count: int) -> str:
    icons = {6: "🎰", 5: "🥇", 4: "🥈", 3: "✨"}
    return icons.get(matched_count, "❌")
