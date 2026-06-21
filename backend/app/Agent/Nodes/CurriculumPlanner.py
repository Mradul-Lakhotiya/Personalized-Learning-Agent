from typing import Optional
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_gemini
from ..Tools.VectorStore import VectorStore
from langchain_core.prompts import PromptTemplate

class CurriculumDecision(BaseModel):
    topic_name: str = Field(description="The human-readable name of the topic.")
    reasoning: str = Field(description="Why this topic was chosen based on their profile and goals.")

async def curriculum_planner_node(state: LearnerState) -> dict:
    """
    Node 2: Curriculum Planner
    Analyzes the profile and determines the optimal next topic to teach.
    Also performs a Pinecone content cache lookup — if this topic's lesson
    was already synthesized and stored, we can skip the expensive swarm run.

    LLM Routing:
    - Gemini (gemini-2.5-flash): GENERATION task — reasoning about prerequisites
      and learning path order requires high-cognition curriculum planning.
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

        # ── Content Cache Lookup ──────────────────────────────────────────────
        # Check if we already have synthesized content for this topic in Pinecone.
        # If we do (cosine > 0.90), skip the swarm and serve from cache directly.
        cached_lesson = None
        try:
            vs = VectorStore()
            matches = await vs.asearch(
                query=f"lesson about {result.topic_name}",
                namespace="content",
                top_k=1
            )
            if matches and matches[0].get("score", 0) > 0.90:
                meta = matches[0].get("metadata", {})
                cached_topic = meta.get("topic", "")
                # Only use cache if the topic name matches closely
                if result.topic_name.lower() in cached_topic.lower() or cached_topic.lower() in result.topic_name.lower():
                    print(f"[CurriculumPlanner] ✅ Content cache HIT for topic: '{result.topic_name}' (score={matches[0]['score']:.3f})")
                    # We flag this in state — GraphService/Graph will skip the swarm
                    cached_lesson = f"_cached_topic:{result.topic_name}"
        except Exception as cache_err:
            # Cache lookup failure is non-fatal — just run the swarm
            print(f"[CurriculumPlanner] ⚠️ Content cache lookup failed (non-fatal): {cache_err}")

        return {
            "current_topic": result.topic_name,
            "current_topic_id": topic_id,
            # If content_module is pre-set, Graph.py will route directly to assessor
            # bypassing the swarm. If None, the full swarm runs.
            "content_module": cached_lesson or "",
            "error": ""
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Curriculum Planner LLM failed: {str(e)}"}
