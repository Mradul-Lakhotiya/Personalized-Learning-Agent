from typing import Annotated, Any
from typing_extensions import TypedDict
import operator

class SwarmWorkerResult(TypedDict):
    source_type: str
    raw_text: str
    source_url: str
    title: str
    metadata: dict

class SwarmQuery(TypedDict):
    engine: str
    query: str

class LearnerState(TypedDict):
    """
    The central state object passed between all LangGraph nodes.
    """
    # Identifiers
    user_id: str
    
    # State Data
    user_profile: dict
    current_topic: str
    
    # Current Interaction
    current_question: dict
    user_answer: str
    evaluation: dict
    
    # History (we append to this list using the `operator.add` reducer conceptually,
    # but since this is a TypedDict we can just overwrite or mutate it manually in nodes, 
    # or use Annotated if using LangGraph's reducer pattern)
    recent_history: Annotated[list[dict], operator.add]
    
    # Circuit Breakers
    loop_counters: dict[str, int]
    
    # Error Handling
    error: str
    
    # Routing Flag
    next_route: str

    # --- Swarm Sub-Graph State ---
    swarm_queries: list[SwarmQuery]
    swarm_raw_results: Annotated[list[SwarmWorkerResult], operator.add]
    content_module: str
