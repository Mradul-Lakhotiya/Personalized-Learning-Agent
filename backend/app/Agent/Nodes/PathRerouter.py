from ..LearnerState import LearnerState
from ..Tools.Database import Database

async def path_rerouter_node(state: LearnerState) -> dict:
    """
    Node 8: Path Rerouter
    Updates user progress in the DB and determines the next step.
    (This node does not route execution directly; it sets a state flag 
    that the conditional edges in Graph.py will use to route).
    """
    user_id = state.get("user_id")
    topic_name = state.get("current_topic")
    topic_id = state.get("current_topic_id")
    evaluation = state.get("evaluation", {})
    score = evaluation.get("score", 0.0)
    
    if not user_id or not topic_id:
        return {"error": "Missing user_id or current_topic_id for Path Rerouter"}
        
    # 1. Update progress in DB based on evaluation
    db = Database()
    
    # We fetch existing progress (if any)
    progress = await db.get_topic_progress(user_id, topic_id)
    
    if not progress:
        current_mastery = 0.0
    else:
        current_mastery = progress.get("mastery_score", 0.0)
        
    # EMA update
    alpha = 0.3
    new_mastery = (alpha * score) + ((1 - alpha) * current_mastery)
    
    status = "in_progress"
    if new_mastery >= 0.85:
        status = "mastered"
        
    # Update DB
    await db.upsert_topic_progress(user_id, topic_id, {
        "mastery_score": new_mastery,
        "status": status,
        "last_assessed_at": "now()" # In a real app, pass ISO timestamp
    })
    
    # Decide routing flag
    route = "assessor" # Default to another question
    if status == "mastered":
        route = "planner" # Pick a new topic
    elif score < 0.4:
        route = "swarm" # User is failing badly, trigger swarm to teach
        
    return {
        # We can store the routing decision in a transient state variable if needed,
        # but LangGraph conditional edges usually just read the state.
        # Let's add 'next_route' to the state to make it explicit.
        "next_route": route,
        "error": ""
    }
