from typing import Optional
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import LlmFactory, safe_ainvoke
from langchain_core.prompts import PromptTemplate

class CurriculumDecision(BaseModel):
    topic_id: str = Field(description="The UUID of the topic the user should learn next.")
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

    # In a real scenario, we would also fetch the topic graph from Supabase here
    # and provide it to the LLM so it knows the valid UUIDs and dependencies.
    # For now, we will simulate the LLM choosing a topic.
    
    llm = LlmFactory.get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(CurriculumDecision)
    
    prompt = PromptTemplate.from_template(
        "You are an expert curriculum planner. Analyze the user's profile and goals.\n"
        "User Profile: {profile}\n\n"
        "Select the most appropriate foundational topic for them to learn right now.\n"
        "Respond strictly with a topic_id (UUID format, can be generated if new), topic_name, and reasoning."
    )
    
    chain = prompt | structured_llm
    
    try:
        # safe_ainvoke handles retries, but structured output chaining needs a slightly different wrapper
        # We'll use safe_ainvoke on the chain itself
        result: CurriculumDecision = await safe_ainvoke(chain, {"profile": profile})
        
        return {
            "current_topic": result.topic_name, # We store the name for the state
            # In full implementation, we'd store the topic in DB if it's dynamically generated
            "error": ""
        }
    except Exception as e:
        return {"error": f"Curriculum Planner LLM failed: {str(e)}"}
