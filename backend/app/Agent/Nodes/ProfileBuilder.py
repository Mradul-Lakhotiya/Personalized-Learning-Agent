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
        # If user doesn't exist, we could return a default or flag an error
        # Assuming the auth trigger created it, it should exist.
        return {"error": f"Profile not found for user: {user_id}"}
        
    # Return updates to the state
    return {
        "user_profile": profile,
        "error": "" # Clear any previous errors
    }
