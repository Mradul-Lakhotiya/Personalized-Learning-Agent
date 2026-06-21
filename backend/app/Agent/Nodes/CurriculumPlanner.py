from typing import Optional
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_gemini
from langchain_core.prompts import PromptTemplate

class CurriculumDecision(BaseModel):
    topic_name: str = Field(description="The human-readable name of the topic.")
    reasoning: str = Field(description="Why this topic was chosen based on their profile and goals.")

async def curriculum_planner_node(state: LearnerState) -> dict:
    """
    Node 2: Curriculum Planner
    Analyzes the profile and determines the optimal next topic to teach.

    LLM Routing:
    - Gemini (gemini-2.5-flash): This is a GENERATION task — creating a personalized
      curriculum plan requires high-cognition reasoning about prerequisites, learning
      style, and goal alignment. Gemini excels at this.
    """
    profile = state.get("user_profile")
    if not profile:
        return {"error": "Curriculum Planner requires a valid user_profile in state"}

    prompt = PromptTemplate.from_template(
        "You are an expert AI curriculum planner. Analyze the learner's profile carefully.\n\n"
        "User Profile: {profile}\n\n"
        "Based on their goals, background, and learning style, select the single most appropriate "
        "foundational topic to teach them right now. Consider prerequisite relationships — "
        "start from the ground up if needed.\n\n"
        "Respond with the topic_name and your reasoning."
    )

    def build_chain(api_key: str):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=api_key)
        structured_llm = llm.with_structured_output(CurriculumDecision)
        return prompt | structured_llm

    try:
        result: CurriculumDecision = await safe_ainvoke_gemini(build_chain, {"profile": profile})

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
        return {"error": f"Curriculum Planner LLM failed: {str(e)}"}
