from ..LearnerState import LearnerState
from ..Tools.Database import Database

async def profile_builder_node(state: LearnerState) -> dict:
    """
    Node 1: Profile Builder
    Retrieves the user's profile and learning goals from Supabase.
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"error": "No user_id provided in state"}
        
    db = Database()
    
    # Fetch profile
    profile = await db.get_user_profile(user_id)
    
    if not profile:
        profile = {
            "id": user_id,
            "name": "Guest Learner",
            "learning_goals": ["Learn Python", "Understand Web Architecture", "Master System Design"]
        }
    elif not profile.get("learning_goals") or len(profile.get("learning_goals")) == 0:
        # Provide default goals if the user just signed up and hasn't set any
        profile["learning_goals"] = ["Learn Python", "Understand Web Architecture", "Master System Design"]
        
    # Return updates to the state
    return {
        "user_profile": profile,
        "error": "" # Clear any previous errors
    }
