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
        
    # 1. Accumulate current score into batch
    batch_scores = list(state.get("current_batch_scores", []))
    batch_scores.append(score)
    
    # 2. Check if we have reached the batch size (5 questions)
    if len(batch_scores) < 5:
        # Not enough data to update mastery — continue asking questions
        return {
            "current_batch_scores": batch_scores,
            "next_route": "assessor",
            "error": ""
        }
        
    # 3. Batch complete: Calculate batch average
    batch_avg = sum(batch_scores) / len(batch_scores)
    
    # 4. Update progress in DB based on EMA
    db = Database()
    progress = await db.get_topic_progress(user_id, topic_id)
    current_mastery = progress.get("mastery_score", 0.0) if progress else 0.0
        
    # EMA update (alpha = 0.3)
    alpha = 0.3
    new_mastery = (alpha * batch_avg) + ((1 - alpha) * current_mastery)
    
    status = "in_progress"
    if new_mastery >= 0.85:
        status = "mastered"
        
    # Update DB
    try:
        await db.upsert_topic_progress(user_id, topic_id, {
            "mastery_score": new_mastery,
            "status": status,
            "last_assessed_at": "now()"
        })
    except Exception as e:
        print(f"[PathRerouter] ⚠️ Failed to update DB: {e}")
    
    # 5. Decide routing flag based on new mastery
    if status == "mastered":
        route = "planner"   # Pick a new topic
    elif new_mastery < 0.4:
        route = "swarm"     # User is failing badly, trigger swarm to teach
    else:
        route = "assessor"  # Need more practice (0.40 <= mastery < 0.85)
        
    return {
        # Clear the batch for the next round (or next topic)
        "current_batch_scores": [],
        "next_route": route,
        "error": ""
    }
