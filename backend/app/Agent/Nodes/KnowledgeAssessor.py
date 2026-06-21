import json
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_gemini
from ..Tools.VectorStore import VectorStore
from langchain_core.prompts import PromptTemplate

class QuestionFormat(BaseModel):
    question_type: str = Field(description="'mcq', 'open_ended', or 'code'")
    question_text: str = Field(description="The actual question to ask the user")
    options: list[str] = Field(description="List of options if MCQ, else empty list", default=[])
    expected_answer: str = Field(description="The correct answer or evaluation rubric for the LLM grader")

async def knowledge_assessor_node(state: LearnerState) -> dict:
    """
    Node 4: Knowledge Assessor
    Generates or retrieves a question to test the user's mastery of the current topic.

    LLM Routing:
    - Gemini (gemini-2.5-flash): This is a GENERATION task — creating a high-quality,
      pedagogically sound question for the learner. Gemini is used for its strong
      instruction-following and educational content generation capabilities.
    - Groq: NOT used here — question generation requires creative generation, not consolidation.
    """
    err = state.get("error")
    if err:
        return {"error": err}

    topic = state.get("current_topic")
    if not topic:
        return {"error": "No current_topic found in state"}

    vs = VectorStore()

    try:
        # 1. Try to fetch a verified question from Pinecone cache (threshold: 0.92)
        cached_matches = await vs.asearch(
            query=f"Question about {topic}",
            namespace="questions",
            top_k=1
        )

        if cached_matches and cached_matches[0].get("score", 0) > 0.92:
            meta = cached_matches[0].get("metadata", {})
            return {
                "current_question": {
                    "type": meta.get("type", "open_ended"),
                    "text": meta.get("text", "Error loading question"),
                    "options": json.loads(meta.get("options", "[]")),
                    "expected": meta.get("expected", ""),
                    "source": "cache"
                },
                "error": ""
            }

        # 2. Cache miss → generate a new question via Gemini (GENERATION task)
        prompt = PromptTemplate.from_template(
            "You are an expert educator creating an assessment question for a learner.\n\n"
            "Topic: {topic}\n\n"
            "Generate a single, high-quality question to test understanding of this topic.\n"
            "Choose the most appropriate type:\n"
            "- 'mcq': For conceptual knowledge (provide 4 options in 'options' field)\n"
            "- 'open_ended': For analytical/explanatory topics\n"
            "- 'code': For programming topics (describe the task clearly)\n\n"
            "Also provide the correct answer or evaluation rubric in 'expected_answer'."
        )

        def build_chain(api_key: str):
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, google_api_key=api_key)
            structured_llm = llm.with_structured_output(QuestionFormat)
            return prompt | structured_llm

        result: QuestionFormat = await safe_ainvoke_gemini(build_chain, {"topic": topic})

        # 3. Write new question to staging (quality gate — not yet verified)
        # TODO: upsert to staging_questions table and questions_staging Pinecone namespace

        return {
            "current_question": {
                "type": result.question_type,
                "text": result.question_text,
                "options": result.options,
                "expected": result.expected_answer,
                "source": "generated"
            },
            "error": ""
        }

    except Exception as e:
        return {"error": f"Knowledge Assessor failed: {str(e)}"}
