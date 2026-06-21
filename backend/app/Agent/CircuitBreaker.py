from .LearnerState import LearnerState
from typing import Literal

# Per-node max consecutive visits before the circuit breaker fires
MAX_LOOPS: dict[str, int] = {
    "knowledge_assessor": 3,   # 3 entries with no valid question served
    "answer_evaluator":   3,   # 3 consecutive parse failures or gibberish
    "curriculum_planner": 2,   # 2 consecutive re-plans (replan storm prevention)
}

def check_circuit_breaker(state: LearnerState, node_name: str) -> bool:
    """
    Returns True if the circuit breaker has TRIPPED (too many loops).
    Returns False if it is safe to proceed normally.

    Usage in routing functions:
        if check_circuit_breaker(state, "knowledge_assessor"):
            return "error_handler"
    """
    counters = state.get("loop_counters", {})
    count = counters.get(node_name, 0)
    limit = MAX_LOOPS.get(node_name, 999)
    return count >= limit

def increment_counter(state: LearnerState, node_name: str) -> dict:
    """Returns a state update dict that increments a single node's loop counter."""
    counters = dict(state.get("loop_counters", {}))
    counters[node_name] = counters.get(node_name, 0) + 1
    return {"loop_counters": counters}

def reset_counter(state: LearnerState, node_name: str) -> dict:
    """Returns a state update dict that resets a single node's loop counter to 0."""
    counters = dict(state.get("loop_counters", {}))
    counters[node_name] = 0
    return {"loop_counters": counters}

def reset_all_counters() -> dict:
    """Returns a state update dict that clears ALL loop counters (used by ErrorHandler)."""
    return {"loop_counters": {}}
