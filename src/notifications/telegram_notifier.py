"""
src/notifications/telegram_notifier.py
All Telegram push notification templates for the pipeline.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

from src.utils.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.utils.logger import get_logger

log = get_logger("telegram")


def _send(text: str) -> bool:
    """Send a Markdown message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
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


# ── Phase 3a — Generate Prediction ───────────────────────────────

def notify_generate(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    cycle = result.get("cycle_number", "?")
    version = result.get("model_version", "?")
    numbers = _fmt_numbers(result.get("numbers", []))
    w = result.get("weights", {})
    lstm_pct = int(w.get("lstm", 0.4) * 100)
    xgb_pct = int(w.get("xgboost", 0.35) * 100)
    stat_pct = int(w.get("statistical", 0.25) * 100)
    success = result.get("success", True)

    if success:
        msg = (
            f"🎯 *[GENERATE] {lottery} — Cycle #{cycle}*\n"
            f"📅 {_now_str()} | Model v{version}\n"
            f"──────────────────────────────────────\n"
            f"Bộ số dự đoán: `{numbers}`\n"
            f"Sẽ dò với 5 kỳ xổ tiếp theo\n"
            f"──────────────────────────────────────\n"
            f"Ensemble: LSTM {lstm_pct}% | XGBoost {xgb_pct}% | Stat {stat_pct}%\n"
            f"✅ SUCCESS | {_now_str()}"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[GENERATE] {lottery} — FAILED*\n"
            f"⚠ Lý do: {error}\n"
            f"🔁 Manual check required"
        )
    _send(msg)


# ── Phase 3b — Crawl Result ───────────────────────────────────────

def notify_crawl(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    success = result.get("success", True)

    if success:
        draw_id = result.get("draw_id", "?")
        draw_date = result.get("draw_date", "?")
        numbers = _fmt_numbers(result.get("numbers", []))
        jackpot2 = result.get("jackpot2")
        jackpot_amount = result.get("jackpot_amount")

        j2_line = f"🎯 Jackpot2: {jackpot2:02d}\n" if jackpot2 else ""
        amount_line = f"💰 Pool: {jackpot_amount:,} đ\n" if jackpot_amount else ""

        msg = (
            f"✅ *[CRAWL] {lottery} — Kỳ #{draw_id}*\n"
            f"📅 {draw_date} | {_now_str()}\n"
            f"🔢 Kết quả: `{numbers}`\n"
            f"{j2_line}"
            f"{amount_line}"
            f"✅ SUCCESS"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[CRAWL] {lottery} — FAILED*\n"
            f"⚠ Lý do: {error}\n"
            f"🔁 Manual check required"
        )
    _send(msg)


# ── Phase 3c — Dò Kết Quả (each draw) ────────────────────────────

def notify_check(result: dict[str, Any], history_rows: list[dict] | None = None) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    success = result.get("success", True)

    if success:
        cycle = result.get("cycle_number", "?")
        draw_num = result.get("draw_number", "?")
        draw_date = result.get("draw_date", "?")
        predicted = _fmt_numbers(result.get("predicted_nums", []))
        actual = _fmt_numbers(result.get("actual_numbers", []))
        jackpot2 = result.get("jackpot2")
        matched = result.get("matched_numbers", [])
        matched_count = result.get("matched_count", 0)
        draws_left = 5 - int(result.get("draws_tracked", draw_num))

        j2_str = f" | J2: {jackpot2:02d}" if jackpot2 else ""
        matched_str = " | ".join(f"{n:02d} ✅" for n in matched) if matched else "Không có"
        icon = {6: "🎰", 5: "🥇", 4: "🥈", 3: "✨"}.get(matched_count, "❌")

        # History section
        hist_lines = ""
        if history_rows:
            for row in history_rows:
                row_icon = {6: "🎰", 5: "🥇", 4: "🥈", 3: "✨"}.get(row["matched_count"], "❌")
                marker = "  ← Hôm nay" if row["draw_number"] == draw_num else ""
                hist_lines += f"  Lần dò {row['draw_number']} ({row['draw_date'][5:]}): {row_icon} {row['matched_count']}/6{marker}\n"

        msg = (
            f"✅ *[DÒ KẾT QUẢ] {lottery} — Lần dò {draw_num}/5 (Cycle #{cycle})*\n"
            f"📅 {draw_date} | {_now_str()}\n"
            f"──────────────────────────────────────────────────────\n"
            f"Bộ số AI  : `{predicted}`\n"
            f"Kết quả   : `{actual}`{j2_str}\n"
            f"──────────────────────────────────────────────────────\n"
            f"Trùng khớp: {matched_str}\n"
            f"Kết quả   : {icon} {matched_count}/6\n"
            f"──────────────────────────────────────────────────────\n"
            f"Lịch sử Cycle #{cycle}:\n{hist_lines}"
            f"Còn {draws_left} lần dò nữa"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[DÒ KẾT QUẢ] {lottery} — FAILED*\n"
            f"⚠ Lý do: {error}\n"
            f"🔁 Crawl chưa chạy hoặc failed"
        )
    _send(msg)


# ── Phase 3d — Evaluate & Retrain ────────────────────────────────

def notify_evaluate(result: dict[str, Any]) -> None:
    lottery = result.get("lottery_label", result.get("lottery_type", "?"))
    success = result.get("success", True)

    if success:
        match_rows = result.get("match_rows", [])
        cycle_number = result.get("cycle_number", "?")
        hit_3plus = result.get("hit_3plus", 0)
        max_match = result.get("max_match", 0)
        should_retrain = result.get("should_retrain", False)
        reason = result.get("reason", "")

        rows_section = ""
        for row in match_rows:
            icon = {6: "🎰", 5: "🥇", 4: "🥈", 3: "✨"}.get(row["matched_count"], "❌")
            actual_str = _fmt_numbers(row["actual_numbers"])
            rows_section += f"  Lần dò {row['draw_number']}  ({row['draw_date'][5:]}): {icon} {row['matched_count']}/6 | Kết quả: {actual_str}\n"

        retrain_section = (
            f"⚠️ *RETRAIN TRIGGERED*\n"
            f"Lý do: {reason}\n"
            f"🔄 Kaggle training dispatched (~25 phút)\n"
            f"Cycle mới sẽ generate sau khi training xong"
            if should_retrain else
            f"✅ *SKIP retrain*\n"
            f"Lý do: {reason}"
        )

        bộ_số = _fmt_numbers(match_rows[0]["predicted_nums"]) if match_rows else "?"
        msg = (
            f"📊 *[EVALUATE] {lottery} — Cycle #{cycle_number} Hoàn thành*\n"
            f"══════════════════════════════════════════════════\n"
            f"Bộ số đã dùng: `{bộ_số}`\n"
            f"──────────────────────────────────────────────────\n"
            f"{rows_section}"
            f"──────────────────────────────────────────────────\n"
            f"Lần trùng ≥3 số: {hit_3plus}/5 | Cao nhất: {max_match}/6\n"
            f"══════════════════════════════════════════════════\n"
            f"{retrain_section}"
        )
    else:
        error = result.get("error", "Unknown error")
        msg = (
            f"❌ *[EVALUATE] {lottery} — FAILED*\n"
            f"⚠ Lý do: {error}\n"
            f"🔁 Retry in 60 phút"
        )
    _send(msg)
