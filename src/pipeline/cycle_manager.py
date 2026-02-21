"""
src/pipeline/cycle_manager.py
Manage prediction cycles: create, track, and complete.
"""
from __future__ import annotations

from src.utils import supabase_client as db
from src.utils.logger import get_logger

log = get_logger("pipeline.cycle")


def get_or_create_cycle(lottery_type: str, model_version: str) -> dict:
    """
    Return the active cycle for a lottery type, or create a new one.
    """
    cycle = db.get_active_cycle(lottery_type)
    if cycle:
        log.info(f"Active cycle found: #{cycle['cycle_number']} ({lottery_type}), draws_tracked={cycle['draws_tracked']}")
        return cycle

    # No active cycle — create cycle N+1
    cycle_number = db.get_next_cycle_number(lottery_type)
    cycle = db.create_prediction_cycle(lottery_type, cycle_number, model_version)
    log.info(f"Created new cycle #{cycle_number} for {lottery_type}")
    return cycle


def advance_cycle(cycle_id: str, lottery_type: str) -> dict:
    """
    Increment draws_tracked.
    If draws_tracked reaches 5, mark cycle as completed and return updated record.
    """
    updated = db.increment_draws_tracked(cycle_id)
    log.info(f"draws_tracked → {updated['draws_tracked']} for cycle {cycle_id}")

    if updated["draws_tracked"] >= 5:
        completed = db.complete_cycle(cycle_id)
        log.info(f"Cycle {cycle_id} COMPLETED (5/5 draws tracked)")
        return completed

    return updated


def is_cycle_complete(cycle: dict) -> bool:
    return cycle.get("draws_tracked", 0) >= 5 or cycle.get("status") == "completed"
