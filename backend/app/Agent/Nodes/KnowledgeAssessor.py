import json
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_gemini
from ..Tools.VectorStore import VectorStore
from ..Tools.QualityGate import write_question_to_staging
from langchain_core.prompts import PromptTemplate

class QuestionFormat(BaseModel):
    question_type: str = Field(description="'mcq', 'open_ended', or 'code'")
    question_text: str = Field(description="The actual question to ask the user")
    options: list[str] = Field(description="List of 4 options if MCQ, else empty list", default=[])
    expected_answer: str = Field(description="The correct answer or evaluation rubric")

async def knowledge_assessor_node(state: LearnerState) -> dict:
    """
    Node 4: Knowledge Assessor — RAG Question Cache

    Flow:
    1. Search Pinecone 'questions' namespace (verified pool only, threshold: 0.92)
    2. Cache HIT  → return verified question (0 LLM tokens, guaranteed quality)
    3. Cache MISS → generate new question via Gemini (GENERATION task)
                  → write to staging_questions Postgres table
                  → embed + upsert to Pinecone 'questions_staging' namespace
                  → return staged question with staging_id for quality gate

    LLM Routing:
    - Gemini (gemini-2.5-flash): GENERATION task — creating a high-quality,
      pedagogically sound question requires creative generation, not consolidation.
    """
    err = state.get("error", "")
    if err:
        return {"error": err}

    topic = state.get("current_topic", "")
    if not topic:
        return {"error": "No current_topic found in state"}

    answered_questions = state.get("answered_questions", [])
    # IDs of questions already answered this session — avoid repeats
    answered_ids = {q.get("staging_id") for q in answered_questions if q.get("staging_id")}

    vs = VectorStore()

    try:
        # ── Step 1: Search verified 'questions' namespace ─────────────────────
        cached_matches = await vs.asearch(
            query=f"Assessment question about {topic}",
            namespace="questions",
            top_k=5  # fetch top 5 so we can skip already-answered ones
        )

        for match in cached_matches:
            score = match.get("score", 0)
            meta  = match.get("metadata", {})
            if score > 0.92 and meta.get("staging_id") not in answered_ids:
                print(f"[KnowledgeAssessor] ✅ Cache HIT (score={score:.3f}) for topic: '{topic}'")
                return {
                    "current_question": {
                        "type":       meta.get("type", "open_ended"),
                        "text":       meta.get("text", ""),
                        "options":    json.loads(meta.get("options", "[]")) if isinstance(meta.get("options"), str) else meta.get("options", []),
                        "expected":   meta.get("expected", ""),
                        "topic":      topic,
                        "source":     "cache",
                        "staging_id": meta.get("staging_id"),
                    },
                    "error": ""
                }

        # ── Step 2: Cache MISS — generate new question via Gemini ────────────
        print(f"[KnowledgeAssessor] Cache MISS. Generating new question for topic: '{topic}'")

        prompt = PromptTemplate.from_template(
            "You are an expert educator creating an assessment question for a learner.\n\n"
            "Topic: {topic}\n\n"
            "Generate a single, high-quality question to test understanding of this topic.\n"
            "Choose the most appropriate type:\n"
            "- 'mcq': For conceptual knowledge (provide exactly 4 options)\n"
            "- 'open_ended': For analytical/explanatory topics\n"
            "- 'code': For programming topics (describe the coding task clearly)\n\n"
            "For MCQ: put the correct option first in the options list.\n"
            "Provide the correct answer or evaluation rubric in 'expected_answer'."
        )

        def build_chain(api_key: str):
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.7,
                google_api_key=api_key
            )
            structured_llm = llm.with_structured_output(QuestionFormat)
            return prompt | structured_llm

        result: QuestionFormat = await safe_ainvoke_gemini(build_chain, {"topic": topic})

        # ── Step 3: Write to staging (quality gate — not yet verified) ────────
        staging_row = await write_question_to_staging(
            topic=topic,
            subtopic=state.get("current_subtopic", ""),
            question_type=result.question_type,
            question_text=result.question_text,
            expected_answer=result.expected_answer,
            options=result.options,
        )
        staging_id = staging_row.get("staging_id", "")

        return {
            "current_question": {
                "type":       result.question_type,
                "text":       result.question_text,
                "options":    result.options,
                "expected":   result.expected_answer,
                "topic":      topic,
                "source":     "staged",
                "staging_id": staging_id,
            },
            "error": ""
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Knowledge Assessor failed: {str(e)}"}
