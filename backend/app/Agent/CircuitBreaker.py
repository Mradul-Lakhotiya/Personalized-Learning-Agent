from .LearnerState import LearnerState

MAX_LOOPS = 3

def check_circuit_breaker(state: LearnerState, node_name: str) -> bool:
    """
    Checks if a node has executed more times than the allowed MAX_LOOPS
    in a single graph traversal cycle to prevent infinite LLM loops.
    
    Returns True if safe to proceed, False if tripped.
    """
    counters = state.get("loop_counters", {})
    count = counters.get(node_name, 0)
    
    if count >= MAX_LOOPS:
        return False
        
    return True
