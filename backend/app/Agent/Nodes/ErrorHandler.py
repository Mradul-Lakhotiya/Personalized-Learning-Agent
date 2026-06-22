from ..LearnerState import LearnerState


async def error_handler_node(state: LearnerState) -> dict:
    """
    Error Handler Node — simplified for the new graph-based architecture.
    No longer handles Q&A-related errors. Just logs and resets state.
    """
    err = state.get("error", "Unknown error occurred")
    ctx = state.get("error_context") or {}
    reason = ctx.get("reason", "unknown")

    print(f"[ErrorHandler] Triggered. Reason: {reason} | Error: {err}")

    if reason == "replan_storm":
        return {
            "error": "",
            "error_context": None,
            "session_complete": True,
        }

    # Default: clear error and let the routing function decide what to retry
    return {
        "error": "",
        "error_context": None,
        "loop_counters": {},
    }
