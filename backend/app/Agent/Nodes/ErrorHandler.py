from ..LearnerState import LearnerState
from ..CircuitBreaker import reset_all_counters

async def error_handler_node(state: LearnerState) -> dict:
    """
    Node 6: Error Handler
    Fallback node if something goes catastrophically wrong or loops exceed limits.
    """
    err = state.get("error", "Unknown error occurred")
    ctx = state.get("error_context") or {}
    reason = ctx.get("reason", "")
    
    print(f"[ErrorHandler] Triggered. Reason: {reason} | Error: {err}")
    
    # 1. Stuck in assessment loop (user keeps getting questions wrong but not failing badly enough for swarm)
    if reason == "stuck_in_assessment_loop":
        # Force a transition. We clear the counters and let Graph.py route to content_delivery
        return {
            "loop_counters": reset_all_counters(state),
            "error": "", # Clear error so graph can proceed
            "current_question": {
                "type": "error",
                "text": "It seems like we're stuck here. Let's review the material again.",
                "options": [],
                "expected": "",
                "source": "system"
            }
        }
        
    # 2. Evaluation Parse Failure (LLM returned garbage)
    elif reason == "evaluation_parse_failure":
        # We don't advance the topic, we just re-ask or skip
        return {
            "error": "",
            "current_question": {
                "type": "error",
                "text": f"I had trouble grading that. Let's try another question.",
                "options": [],
                "expected": "",
                "source": "system"
            }
        }
        
    # 3. Replan Storm (Curriculum planner keeps looping without picking a valid topic)
    elif reason == "replan_storm":
        return {
            "error": "",
            "session_complete": True,
            "current_question": {
                "type": "error",
                "text": "I'm having trouble figuring out what to teach next. Let's wrap up this session for now.",
                "options": [],
                "expected": "",
                "source": "system"
            }
        }
        
    # 4. Default / Catastrophic
    return {
        "error": "",
        "current_question": {
            "type": "error",
            "text": f"SYSTEM ERROR: {err}. Let's try moving forward.",
            "options": [],
            "expected": "",
            "source": "system"
        }
    }
