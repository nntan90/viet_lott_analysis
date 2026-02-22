"""
src/pipeline/result_checker.py  — v4.0
Phase 3c: Dò kết quả — compare active prediction vs latest draw.
Supports all 3 lottery types with type-specific prize logic.
"""
from __future__ import annotations

from src.pipeline.cycle_manager import advance_cycle
from src.utils import supabase_client as db
from src.utils.config import LOTTERY_LABELS
from src.utils.logger import get_logger

log = get_logger("pipeline.checker")


# ── Prize level logic ─────────────────────────────────────────────

def _prize_655(matched_count: int, jackpot2_matched: bool) -> str:
    """Power 6/55 prize levels."""
    if matched_count == 6:
        return "JACKPOT_1"
    if matched_count == 5 and jackpot2_matched:
        return "JACKPOT_2"
    if matched_count == 5:
        return "PRIZE_1"
    if matched_count == 4:
        return "PRIZE_2"
    if matched_count == 3:
        return "PRIZE_3"
    return "NO_PRIZE"


def _prize_645(matched_count: int) -> str:
    """Mega 6/45 prize levels."""
    if matched_count == 6:
        return "JACKPOT"
    if matched_count == 5:
        return "PRIZE_1"
    if matched_count == 4:
        return "PRIZE_2"
    if matched_count == 3:
        return "PRIZE_3"
    return "NO_PRIZE"


def _prize_535(matched_count: int, special_matched: bool) -> str:
    """Lotto 5/35 prize levels including special number."""
    if matched_count == 5 and special_matched:
        return "JACKPOT"
    if matched_count == 5:
        return "PRIZE_1"
    if matched_count == 4 and special_matched:
        return "PRIZE_2"
    if matched_count == 4:
        return "PRIZE_3"
    if matched_count == 3 and special_matched:
        return "PRIZE_4"
    if matched_count == 3:
        return "PRIZE_5"
    if matched_count == 2 and special_matched:
        return "PRIZE_KK"     # Giải Khuyến Khích
    return "NO_PRIZE"


_PRIZE_ICONS = {
    "JACKPOT":   "🎰",
    "JACKPOT_1": "🎰",
    "JACKPOT_2": "🎯",
    "PRIZE_1":   "🥇",
    "PRIZE_2":   "🥈",
    "PRIZE_3":   "✨",
    "PRIZE_4":   "✨",
    "PRIZE_5":   "✅",
    "PRIZE_KK":  "🌟",
    "NO_PRIZE":  "❌",
}

def get_prize_icon(prize_level: str) -> str:
    return _PRIZE_ICONS.get(prize_level, "❌")


# ── Main check function ───────────────────────────────────────────

def check_result(
    lottery_type: str,
    draw_id: str,
    draw_session: str | None = None,
) -> dict:
    """
    Full Phase 3c flow:
    1. Load active cycle
    2. Load prediction
    3. Load draw result (with optional session filter for lotto_535)
    4. Compute matched, special_matched, prize_level
    5. Insert match_results row
    6. Advance draws_tracked
    7. Return result dict for Telegram
    """
    log.info(f"[CHECK] {lottery_type} draw={draw_id} session={draw_session}")

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
    result = db.get_result_by_draw_id(lottery_type, draw_id, session=draw_session)
    if not result:
        session_str = f" (session={draw_session})" if draw_session else ""
        msg = f"draw_id={draw_id}{session_str} not found in lottery_results. Run crawl first."
        log.error(msg)
        return {"success": False, "error": msg}

    predicted_nums = prediction["numbers"]
    predicted_special = prediction.get("special_number")
    actual_numbers = result["numbers"]
    actual_special = result.get("jackpot2")           # jackpot2 col = bonus/special
    act_session = result.get("draw_session")

    # Step 4: Compute match
    matched = sorted(set(predicted_nums) & set(actual_numbers))
    matched_count = len(matched)
    special_matched = False
    prize_level = "NO_PRIZE"

    if lottery_type == "power_655":
        j2_matched = (actual_special is not None and actual_special in predicted_nums)
        special_matched = j2_matched
        prize_level = _prize_655(matched_count, j2_matched)

    elif lottery_type == "mega_645":
        prize_level = _prize_645(matched_count)

    elif lottery_type == "lotto_535":
        if predicted_special is not None and actual_special is not None:
            special_matched = (predicted_special == actual_special)
        prize_level = _prize_535(matched_count, special_matched)

    draw_number = cycle["draws_tracked"] + 1   # 1-indexed
    max_draws = cycle.get("max_draws", 5)

    # Step 5: Insert match_results
    db.insert_match_result({
        "cycle_id": cycle["id"],
        "lottery_type": lottery_type,
        "draw_id": draw_id,
        "draw_date": result["draw_date"],
        "draw_session": act_session,
        "draw_number": draw_number,
        "predicted_nums": predicted_nums,
        "predicted_special": predicted_special,
        "actual_numbers": actual_numbers,
        "actual_special": actual_special,
        "matched_numbers": matched,
        "matched_count": matched_count,
        "special_matched": special_matched,
        "prize_level": prize_level,
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
        "draw_session": act_session,
        "draw_number": draw_number,
        "predicted_nums": predicted_nums,
        "predicted_special": predicted_special,
        "actual_numbers": actual_numbers,
        "actual_special": actual_special,
        "matched_numbers": matched,
        "matched_count": matched_count,
        "special_matched": special_matched,
        "prize_level": prize_level,
        "prize_icon": get_prize_icon(prize_level),
        "draws_tracked": updated_cycle["draws_tracked"],
        "max_draws": updated_cycle.get("max_draws", max_draws),
        "cycle_complete": updated_cycle.get("status") == "completed",
    }
    log.info(f"[CHECK] {lottery_type} lần {draw_number}/{max_draws} → {prize_level} | {matched_count} trùng {matched}")
    return result_dict
