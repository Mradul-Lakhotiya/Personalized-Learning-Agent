from ..LearnerState import LearnerState
from ..Tools.Database import Database
from ..Tools.LlmFactory import safe_ainvoke_gemini
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List


# ── Pydantic model for survey generation ────────────────────────────────────

class SurveyQuestion(BaseModel):
    topic: str = Field(description="The specific prerequisite topic being assessed.")
    question: str = Field(description="The question to ask the user, e.g. 'Rate your knowledge of Python: 0 (none) to 5 (expert)'")



async def profile_builder_node(state: LearnerState) -> dict:
    """
    Node 1: Profile Builder
    
    Retrieves the user profile from Supabase, then uses Gemini to generate
    a targeted self-assessment survey based on the user's learning goal.
    
    The survey questions are stored in state so the frontend can render them
    one at a time. Actual answers come via `submit_survey_answer` in GraphService.
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"error": "No user_id provided in state"}

    db = Database()
    profile = await db.get_user_profile(user_id)

    if not profile:
        profile = {
            "id": user_id,
            "name": "Learner",
            "background": "unknown",
            "learning_style": "visual",
            "daily_time_budget_minutes": 30,
        }

    learning_goal = state.get("learning_goal", "")
    if not learning_goal and profile.get("learning_goals"):
        learning_goal = profile["learning_goals"][0] if profile["learning_goals"] else ""

    # If survey is already complete, skip re-generating
    if state.get("survey_complete"):
        return {
            "user_profile": profile,
            "error": "",
        }

    # ── Generate a targeted self-assessment survey ───────────────────────────
    prompt = PromptTemplate.from_template(
        "You are an expert AI educator. A learner wants to: '{goal}'.\n\n"
        "Generate a self-assessment survey of 5-8 prerequisite topics relevant to this goal.\n"
        "For each topic, write a concise question asking the user to rate their knowledge "
        "from 0 (no knowledge) to 5 (expert).\n\n"
        "Focus on foundational prerequisites - things they MUST know before starting.\n"
        "Keep questions short, clear, and conversational.\n\n"
        "OUTPUT FORMAT: Respond with ONLY a valid JSON object. No markdown, no code fences.\n"
        "The JSON must have exactly this structure:\n"
        "{{\n"
        '  "prerequisite_topics": [\n'
        "    {{\n"
        '      "topic": "Topic Name",\n'
        '      "question": "Rate your knowledge of X: 0 (none) to 5 (expert)."\n'
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Generate the survey JSON now:"
    )

    def build_chain(api_key: str):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key
        )
        # Raw text output — parse JSON manually to avoid Gemini schema constraints
        return prompt | llm

    try:
        import json as _json, re as _re

        raw_response = await safe_ainvoke_gemini(build_chain, {"goal": learning_goal})
        raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

        # Strip markdown fences
        clean = _re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`").strip()

        data = None
        try:
            data = _json.loads(clean)
        except _json.JSONDecodeError:
            match = _re.search(r'\{[\s\S]*\}', clean)
            if match:
                try:
                    data = _json.loads(match.group())
                except _json.JSONDecodeError:
                    pass

        if data is None:
            raise ValueError(f"ProfileBuilder: non-JSON response: {raw_text[:200]}")

        topics = data.get("prerequisite_topics", [])
        if not topics:
            raise ValueError("ProfileBuilder: empty prerequisite_topics in response")

        survey_questions = [
            {"topic": q["topic"], "question": q["question"], "index": i}
            for i, q in enumerate(topics)
        ]

        print(f"[ProfileBuilder] Generated {len(survey_questions)} survey questions for goal: '{learning_goal}'")

        return {
            "user_profile": profile,
            "learning_goal": learning_goal,
            "survey_questions": survey_questions,
            "survey_answers": [],
            "survey_complete": False,
            "phase": "onboarding",
            "error": "",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"ProfileBuilder failed: {str(e)}"}
