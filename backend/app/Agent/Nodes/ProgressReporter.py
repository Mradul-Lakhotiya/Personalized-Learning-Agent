from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_groq
from ..Tools.Database import Database
from langchain_core.prompts import PromptTemplate

class ProgressSummary(BaseModel):
    narrative: str = Field(description="A warm, encouraging paragraph summarizing their session and overall progress.")
    weakest_areas: list[str] = Field(description="Top 1-3 topics that need more practice.")
    next_topics: list[str] = Field(description="What they should focus on next time.")

async def progress_reporter_node(state: LearnerState) -> dict:
    """
    Node 7: Progress Reporter
    Terminal node of a session. Summarizes everything using Groq and prepares
    the state payload for the frontend dashboard.
    """
    user_id = state.get("user_id")
    profile = state.get("user_profile", {})
    
    # 1. Fetch raw progress data from DB
    db = Database()
    import asyncio
    try:
        resp = await asyncio.to_thread(
            db.client.table("user_progress").select("*").eq("user_id", user_id).execute
        )
        progress_data = resp.data if resp.data else []
    except Exception as e:
        print(f"[ProgressReporter] ⚠️ Failed to fetch progress: {e}")
        progress_data = []

    mastered = [p["topic_id"] for p in progress_data if p.get("status") == "mastered"]
    in_progress = [p["topic_id"] for p in progress_data if p.get("status") == "in_progress"]
    
    # We don't have topic names easily accessible here without a join, but we can pass raw stats
    raw_stats = f"Mastered Topics Count: {len(mastered)}\nIn-Progress Topics Count: {len(in_progress)}"
    
    # 2. Use Groq to generate a human-readable summary
    # (Groq is perfect for this: CONSOLIDATION task summarizing structured data)
    prompt = PromptTemplate.from_template(
        "You are an encouraging AI tutor.\n"
        "User Profile: {profile}\n"
        "Session Stats: {stats}\n"
        "Recent Topic: {current_topic}\n\n"
        "Write a warm summary of their progress today, pointing out what they mastered and what needs work. "
        "Keep it to 2-3 sentences."
    )
    
    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, groq_api_key=api_key)
        return prompt | llm.with_structured_output(ProgressSummary)
        
    try:
        result: ProgressSummary = await safe_ainvoke_groq(build_chain, {
            "profile": profile,
            "stats": raw_stats,
            "current_topic": state.get("current_topic", "General Studies")
        })
        
        narrative = result.narrative
        weakest = result.weakest_areas
        next_up = result.next_topics
    except Exception as e:
        print(f"[ProgressReporter] ⚠️ Groq failed: {e}")
        narrative = "Great job today! Let's keep up the momentum."
        weakest = []
        next_up = []

    return {
        "evaluation": {
            "score": 0.0,
            "feedback": narrative,
            "misconceptions": weakest
        },
        "session_complete": True,
        "error": ""
    }
