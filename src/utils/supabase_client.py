"""
src/utils/supabase_client.py  — v4.0
Typed Supabase client wrapper for all pipeline tables.
"""
from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from src.utils.config import SUPABASE_KEY, SUPABASE_URL
from src.utils.logger import get_logger

log = get_logger("supabase")

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ── lottery_results ───────────────────────────────────────────────

def upsert_lottery_result(record: dict[str, Any]) -> dict[str, Any]:
    """Upsert a draw result. Handles both session and non-session lottery types."""
    db = get_client()
    # Unique constraint: lottery_type, draw_id, draw_session (NULL-safe via DB constraint)
    resp = (
        db.table("lottery_results")
        .upsert(record, on_conflict="lottery_type,draw_id,draw_session")
        .execute()
    )
    return resp.data[0] if resp.data else {}


def get_recent_results(lottery_type: str, limit: int = 50, session: str | None = None) -> list[dict]:
    db = get_client()
    q = (
        db.table("lottery_results")
        .select("*")
        .eq("lottery_type", lottery_type)
        .order("draw_date", desc=True)
        .order("draw_session", desc=True)  # PM before AM within same day
        .limit(limit)
    )
    if session:
        q = q.eq("draw_session", session)
    resp = q.execute()
    return resp.data or []


def get_result_by_draw_id(lottery_type: str, draw_id: str, session: str | None = None) -> dict | None:
    db = get_client()
    q = (
        db.table("lottery_results")
        .select("*")
        .eq("lottery_type", lottery_type)
        .eq("draw_id", draw_id)
    )
    if session:
        q = q.eq("draw_session", session)
    resp = q.maybe_single().execute()
    return getattr(resp, "data", None) if resp else None


# ── prediction_cycles ─────────────────────────────────────────────

def get_active_cycle(lottery_type: str) -> dict | None:
    db = get_client()
    resp = (
        db.table("prediction_cycles")
        .select("*")
        .eq("lottery_type", lottery_type)
        .eq("status", "active")
        .maybe_single()
        .execute()
    )
    return getattr(resp, "data", None) if resp else None

def get_cycle_by_number(lottery_type: str, cycle_number: int) -> dict | None:
    db = get_client()
    resp = (
        db.table("prediction_cycles")
        .select("*")
        .eq("lottery_type", lottery_type)
        .eq("cycle_number", cycle_number)
        .maybe_single()
        .execute()
    )
    return getattr(resp, "data", None) if resp else None


def create_prediction_cycle(lottery_type: str, cycle_number: int, model_version: str, max_draws: int = 5) -> dict:
    db = get_client()
    resp = (
        db.table("prediction_cycles")
        .insert({
            "lottery_type": lottery_type,
            "cycle_number": cycle_number,
            "status": "active",
            "draws_tracked": 0,
            "max_draws": max_draws,
            "model_version": model_version,
        })
        .execute()
    )
    return resp.data[0]


def increment_draws_tracked(cycle_id: str) -> dict:
    db = get_client()
    current = db.table("prediction_cycles").select("draws_tracked").eq("id", cycle_id).single().execute().data
    new_count = current["draws_tracked"] + 1
    resp = (
        db.table("prediction_cycles")
        .update({"draws_tracked": new_count})
        .eq("id", cycle_id)
        .execute()
    )
    return resp.data[0]


def complete_cycle(cycle_id: str) -> dict:
    from datetime import datetime, timezone
    db = get_client()
    resp = (
        db.table("prediction_cycles")
        .update({"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", cycle_id)
        .execute()
    )
    return resp.data[0]


def get_next_cycle_number(lottery_type: str) -> int:
    db = get_client()
    resp = (
        db.table("prediction_cycles")
        .select("cycle_number")
        .eq("lottery_type", lottery_type)
        .order("cycle_number", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["cycle_number"] + 1
    return 1


# ── predictions ───────────────────────────────────────────────────

def insert_prediction(
    cycle_id: str,
    lottery_type: str,
    numbers: list[int],
    model_version: str,
    special_number: int | None = None,
) -> dict:
    db = get_client()
    payload: dict[str, Any] = {
        "cycle_id": cycle_id,
        "lottery_type": lottery_type,
        "numbers": numbers,
        "model_version": model_version,
    }
    if special_number is not None:
        payload["special_number"] = special_number
    resp = db.table("predictions").insert(payload).execute()
    return resp.data[0]


def get_prediction_for_cycle(cycle_id: str) -> dict | None:
    db = get_client()
    resp = (
        db.table("predictions")
        .select("*")
        .eq("cycle_id", cycle_id)
        .maybe_single()
        .execute()
    )
    return getattr(resp, "data", None) if resp else None


# ── match_results ─────────────────────────────────────────────────

def insert_match_result(record: dict[str, Any]) -> dict:
    db = get_client()
    resp = (
        db.table("match_results")
        .upsert(record, on_conflict="cycle_id,draw_id,draw_session")
        .execute()
    )
    return resp.data[0]


def get_match_results_for_cycle(cycle_id: str) -> list[dict]:
    db = get_client()
    resp = (
        db.table("match_results")
        .select("*")
        .eq("cycle_id", cycle_id)
        .order("draw_number", desc=False)
        .execute()
    )
    return resp.data or []


# ── model_configs ─────────────────────────────────────────────────

def get_active_model_configs(lottery_type: str) -> list[dict]:
    db = get_client()
    resp = (
        db.table("model_configs")
        .select("*")
        .eq("lottery_type", lottery_type)
        .eq("is_active", True)
        .execute()
    )
    return resp.data or []


def update_model_weight(config_id: str, new_weight: float) -> dict:
    db = get_client()
    resp = (
        db.table("model_configs")
        .update({"ensemble_weight": new_weight})
        .eq("id", config_id)
        .execute()
    )
    return resp.data[0]


def deactivate_old_configs(lottery_type: str, model_name: str) -> None:
    db = get_client()
    db.table("model_configs").update({"is_active": False}).eq("lottery_type", lottery_type).eq("model_name", model_name).execute()


# ── model_training_logs ───────────────────────────────────────────

def insert_training_log(record: dict[str, Any]) -> dict:
    db = get_client()
    resp = db.table("model_training_logs").insert(record).execute()
    return resp.data[0]
