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

    # AI determines max_draws based on previous cycle performance
    cycle_number = db.get_next_cycle_number(lottery_type)
    max_draws = 5
    if cycle_number > 1:
        prev_cycle = db.get_cycle_by_number(lottery_type, cycle_number - 1)
        if prev_cycle:
            match_rows = db.get_match_results_for_cycle(prev_cycle["id"])
            hit_3plus = sum(1 for row in match_rows if row.get("matched_count", 0) >= 3)
            # If AI is doing well, stretch out (5). If failing, shrink to 3 draws to re-evaluate sooner.
            max_draws = 5 if hit_3plus >= 1 else 3

    cycle = db.create_prediction_cycle(lottery_type, cycle_number, model_version, max_draws)
    log.info(f"Created new cycle #{cycle_number} for {lottery_type} (AI dynamic length: {max_draws} kỳ)")
    return cycle


def advance_cycle(cycle_id: str, lottery_type: str) -> dict:
    """
    Increment draws_tracked.
    If draws_tracked reaches 5, mark cycle as completed and return updated record.
    """
    updated = db.increment_draws_tracked(cycle_id)
    log.info(f"draws_tracked → {updated['draws_tracked']} for cycle {cycle_id}")

    cycle = db.get_active_cycle(lottery_type)
    max_draws = cycle.get("max_draws", 5) if cycle else 5

    if updated["draws_tracked"] >= max_draws:
        completed = db.complete_cycle(cycle_id)
        log.info(f"Cycle {cycle_id} COMPLETED ({max_draws}/{max_draws} draws tracked)")
        return completed

    return updated


def is_cycle_complete(cycle: dict) -> bool:
    max_draws = cycle.get("max_draws", 5)
    return cycle.get("draws_tracked", 0) >= max_draws or cycle.get("status") == "completed"
