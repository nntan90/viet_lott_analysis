"""
src/notifications/telegram_notifier.py  — v4.0
All Telegram push notification templates for the pipeline.
Supports session (AM/PM) display for lotto_535 and prize level icons.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from src.utils.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.utils.logger import get_logger

log = get_logger("telegram")


def _send(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.error(f"Telegram send failed: {exc}")
        return False


def _now_str() -> str:
    return datetime.now().strftime("%H:%M %d/%m/%Y")


def _fmt_numbers(nums: list[int]) -> str:
    return " - ".join(f"{n:02d}" for n in sorted(nums))


def _session_tag(session: str | None) -> str:
    return f" [{session}]" if session else ""


# ── Phase 3a — Generate Prediction ───────────────────────────────

def notify_generate(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    cycle = result.get("cycle_number", "?")
    version = result.get("model_version", "?")
    numbers_list = result.get("numbers", [])
    numbers = _fmt_numbers(numbers_list)
    special = result.get("special_number")
    has_sp = result.get("has_special", False)
    next_draw_id = result.get("next_draw_id", "00000")
    w = result.get("weights", {})
    lstm_pct = int(w.get("lstm", 0.4) * 100)
    xgb_pct = int(w.get("xgboost", 0.35) * 100)
    stat_pct = int(w.get("statistical", 0.25) * 100)
    max_draws = result.get("max_draws", 5)
    success = result.get("success", True)

    if success:
        special_line = f"Số đặc biệt: `{special:02d}`\n" if has_sp and special else ""
        
        # Format SMS string
        sms_type = "535" if "535" in lottery else "645" if "645" in lottery else "655"
        sms_nums = " ".join(f"{n:02d}" for n in sorted(numbers_list))
        if has_sp and special is not None:
            sms_text = f"DK {sms_type} C5 {next_draw_id} S {sms_nums}-{special:02d}"
        else:
            sms_text = f"DK {sms_type} C5 {next_draw_id} S {sms_nums}"

        msg = (
            f"🎯 *[GENERATE] {lottery} — Cycle #{cycle}*\n"
            f"📅 {_now_str()} | Model v{version}\n"
            f"──────────────────────────────────────\n"
            f"Số chính  : `{numbers}`\n"
            f"{special_line}"
            f"Dò với {max_draws} kỳ tiếp theo\n"
            f"LSTM {lstm_pct}% | XGB {xgb_pct}% | Stat {stat_pct}%\n"
            f"✅ SUCCESS | {_now_str()}\n\n"
            f"📱 *Tap để Copy SMS mua vé:*\n"
            f"`{sms_text}`"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[GENERATE] {lottery} — FAILED*\n"
            f"⚠ {error}\n🔁 Manual check required"
        )
    _send(msg)


# ── Phase 3b — Crawl Result ───────────────────────────────────────

def notify_crawl(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    session = result.get("draw_session")
    success = result.get("success", True)

    if success:
        draw_id = result.get("draw_id", "?")
        draw_date = result.get("draw_date", "?")
        numbers = _fmt_numbers(result.get("numbers", []))
        jackpot2 = result.get("jackpot2")
        jackpot_amount = result.get("jackpot_amount")
        session_str = _session_tag(session)

        # Adapt label for special fields
        if result.get("lottery_type") == "lotto_535":
            special_line = f"🎯 Số đặc biệt: `{jackpot2:02d}`\n" if jackpot2 else ""
            nums_label = "🔢 Số chính"
        else:
            special_line = f"🎯 Jackpot2: `{jackpot2:02d}`\n" if jackpot2 else ""
            nums_label = "🔢 Kết quả"

        amount_line = f"💰 Pool: {jackpot_amount:,} đ\n" if jackpot_amount else ""

        msg = (
            f"✅ *[CRAWL] {lottery}{session_str} — Kỳ #{draw_id}*\n"
            f"📅 {draw_date} | {_now_str()}\n"
            f"📥 Nguồn: `vietvudanh/vietlott-data` (JSONL)\n"
            f"{nums_label}: `{numbers}`\n"
            f"{special_line}"
            f"{amount_line}"
            f"✅ SUCCESS"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[CRAWL] {lottery}{_session_tag(session)} — FAILED*\n"
            f"⚠ {error}\n🔁 Manual check required"
        )
    _send(msg)


# ── Phase 3c — Dò Kết Quả ────────────────────────────────────────

def notify_check(result: dict[str, Any], history_rows: list[dict] | None = None) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    session = result.get("draw_session")
    success = result.get("success", True)

    if success:
        cycle = result.get("cycle_number", "?")
        draw_num = result.get("draw_number", "?")
        draw_date = result.get("draw_date", "?")
        predicted = _fmt_numbers(result.get("predicted_nums", []))
        actual = _fmt_numbers(result.get("actual_numbers", []))
        pred_special = result.get("predicted_special")
        actual_special = result.get("actual_special")
        matched = result.get("matched_numbers", [])
        matched_count = result.get("matched_count", 0)
        special_matched = result.get("special_matched", False)
        prize_level = result.get("prize_level", "NO_PRIZE")
        prize_icon = result.get("prize_icon", "❌")
        max_draws = result.get("max_draws", 5)
        draws_left = max_draws - int(result.get("draws_tracked", draw_num))
        session_str = _session_tag(session)

        matched_str = " | ".join(f"{n:02d} ✅" for n in matched) if matched else "Không có"

        # 5/35 specific lines
        if result.get("lottery_type") == "lotto_535":
            j2_suffix = f" | Đặc biệt: {actual_special:02d}" if actual_special else ""
            sp_match_str = f"Đặc biệt: `{pred_special:02d}` {'✅' if special_matched else '≠ ' + (f'{actual_special:02d}' if actual_special else '?') + ' ❌'}\n"
        else:
            j2_suffix = f" | J2: {actual_special:02d}" if actual_special else ""
            sp_match_str = ""

        # History section
        hist_lines = ""
        if history_rows:
            icons = {"JACKPOT": "🎰", "JACKPOT_1": "🎰", "JACKPOT_2": "🎯",
                     "PRIZE_1": "🥇", "PRIZE_2": "🥈", "PRIZE_3": "✨",
                     "PRIZE_4": "✨", "PRIZE_5": "✅", "PRIZE_KK": "🌟", "NO_PRIZE": "❌"}
            for row in history_rows:
                row_icon = icons.get(row.get("prize_level", "NO_PRIZE"), "❌")
                row_sess = _session_tag(row.get("draw_session"))
                marker = "  ← Hôm nay" if row["draw_number"] == draw_num else ""
                hist_lines += f"  Lần {row['draw_number']} ({row['draw_date'][5:]}{row_sess}): {row_icon} {row['matched_count']}/{5 if 'lotto' in row['lottery_type'] else 6}{marker}\n"

        msg = (
            f"✅ *[DÒ] {lottery}{session_str} — Lần dò {draw_num}/{max_draws} (Cycle #{cycle})*\n"
            f"📅 {draw_date} | {_now_str()}\n"
            f"──────────────────────────────────────────────\n"
            f"Bộ số AI  : `{predicted}`\n"
            f"Kết quả   : `{actual}`{j2_suffix}\n"
            f"──────────────────────────────────────────────\n"
            f"Trùng     : {matched_str} → {prize_icon} {matched_count}/{'5' if 'lotto' in lottery.lower() else '6'}\n"
            f"{sp_match_str}"
            f"──────────────────────────────────────────────\n"
            f"Lịch sử Cycle #{cycle}:\n{hist_lines}"
            f"Còn {draws_left} lần dò nữa"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[DÒ] {lottery} — FAILED*\n"
            f"⚠ {error}\n🔁 Crawl chưa chạy hoặc failed"
        )
    _send(msg)


# ── Phase 3d — Evaluate & Retrain ────────────────────────────────

def notify_evaluate(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    is_535 = "535" in lottery
    pick_total = 5 if is_535 else 6
    success = result.get("success", True)

    if success:
        match_rows = result.get("match_rows", [])
        cycle_number = result.get("cycle_number", "?")
        max_draws = result.get("max_draws", 5)
        hit_3plus = result.get("hit_3plus", 0)
        max_match = result.get("max_match", 0)
        should_retrain = result.get("should_retrain", False)
        reason = result.get("reason", "")

        icons = {"JACKPOT": "🎰", "JACKPOT_1": "🎰", "JACKPOT_2": "🎯",
                 "PRIZE_1": "🥇", "PRIZE_2": "🥈", "PRIZE_3": "✨",
                 "PRIZE_4": "✨", "PRIZE_5": "✅", "PRIZE_KK": "🌟", "NO_PRIZE": "❌"}

        rows_section = ""
        for row in match_rows:
            icon = icons.get(row.get("prize_level", "NO_PRIZE"), "❌")
            actual_str = _fmt_numbers(row["actual_numbers"])
            sess_tag = _session_tag(row.get("draw_session"))
            rows_section += f"  Lần {row['draw_number']} ({row['draw_date'][5:]}{sess_tag}): {icon} {row['matched_count']}/{pick_total} | {actual_str}\n"

        bộ_số = _fmt_numbers(match_rows[0]["predicted_nums"]) if match_rows else "?"
        retrain_section = (
            f"⚠️ *RETRAIN TRIGGERED*\nLý do: {reason}\n🔄 Kaggle dispatched (~25 phút)\n→ Cycle mới generate sau"
            if should_retrain else
            f"✅ *SKIP retrain*\nLý do: {reason}"
        )

        msg = (
            f"📊 *[EVALUATE] {lottery} — Cycle #{cycle_number} Done*\n"
            f"══════════════════════════════════════════\n"
            f"Bộ số: `{bộ_số}`\n"
            f"──────────────────────────────────────────\n"
            f"{rows_section}"
            f"──────────────────────────────────────────\n"
            f"Hits ≥3: {hit_3plus}/{max_draws} | Best: {max_match}/{pick_total}\n"
            f"══════════════════════════════════════════\n"
            f"{retrain_section}"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[EVALUATE] {lottery} — FAILED*\n"
            f"⚠ {error}\n🔁 Retry in 60 phút"
        )
    _send(msg)
