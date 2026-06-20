from ..LearnerState import LearnerState

async def error_handler_node(state: LearnerState) -> dict:
    """
    Node: Error Handler
    Fallback node if something goes catastrophically wrong or loops exceed limits.
    """
    err = state.get("error", "Unknown error occurred")
    return {
        "current_question": {
            "type": "error",
            "text": f"SYSTEM ERROR: {err}",
            "options": [],
            "expected": "",
            "source": "system"
        }
    }

async def progress_reporter_node(state: LearnerState) -> dict:
    """
    Node: Progress Reporter
    Terminal node of a cycle. Formats the state for output to the frontend.
    """
    # In a real app, you might summarize history or prepare a clean payload.
    # We just pass the state through here.
    return {}
