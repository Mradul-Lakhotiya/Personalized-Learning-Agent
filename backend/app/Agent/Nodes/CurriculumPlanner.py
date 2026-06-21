from typing import Optional
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_groq
from langchain_core.prompts import PromptTemplate

class CurriculumDecision(BaseModel):
    topic_name: str = Field(description="The human-readable name of the topic.")
    reasoning: str = Field(description="Why this topic was chosen based on their profile and goals.")

async def curriculum_planner_node(state: LearnerState) -> dict:
    """
    Node 2: Curriculum Planner
    Analyzes the profile and determines the optimal next topic.
    """
    profile = state.get("user_profile")
    if not profile:
        return {"error": "Curriculum Planner requires a valid user_profile in state"}

    prompt = PromptTemplate.from_template(
        "You are an expert curriculum planner. Analyze the user's profile and goals.\n"
        "User Profile: {profile}\n\n"
        "Select the most appropriate foundational topic for them to learn right now.\n"
        "Respond strictly with the topic_name and reasoning."
    )
    
    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=api_key)
        structured_llm = llm.with_structured_output(CurriculumDecision)
        return prompt | structured_llm
    
    try:
        result: CurriculumDecision = await safe_ainvoke_groq(build_chain, {"profile": profile})
        
        from ..Tools.Database import Database
        db = Database()
        topic_id = await db.get_or_create_topic(result.topic_name, result.reasoning)
        
        return {
            "current_topic": result.topic_name,
            "current_topic_id": topic_id,
            "error": ""
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] CurriculumPlanner failed: {str(e)}")
        return {"error": f"Curriculum Planner LLM failed: {str(e)}"}
