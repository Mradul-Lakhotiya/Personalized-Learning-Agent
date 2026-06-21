import asyncio
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_groq
from ..Tools.QualityGate import evaluate_and_promote
from langchain_core.prompts import PromptTemplate

class EvalResult(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0 (1.0 = perfectly correct)")
    feedback: str = Field(description="Constructive feedback explaining the grade")
    misconceptions: list[str] = Field(description="List of identified misconceptions, or empty list")

async def answer_evaluator_node(state: LearnerState) -> dict:
    """
    Node 5: Answer Evaluator + Quality Gate

    Flow:
    1. Input sanity check (gibberish / empty answer → score 0.0)
    2. MCQ: zero-cost exact match (no LLM)
    3. All other types: Groq grades against rubric (CONSOLIDATION task)
    4. Quality Gate:
       - staged question + score >= 0.70 → promote to verified 'questions' namespace
       - staged question + score < 0.70 → increment failure counter (auto-reject at 3)
       - cached question → no action (already verified)
    5. Append to answered_questions audit list in state

    LLM Routing:
    - Groq (llama-3.3-70b-versatile): CONSOLIDATION task — comparing student
      answer vs. rubric, extracting score + misconceptions. Fast and accurate
      for structured grading.
    """
    question    = state.get("current_question", {})
    user_answer = state.get("user_answer", "")

    if not question or not user_answer:
        return {"error": "Missing question or user answer in state"}

    # ── Input Sanity Check ────────────────────────────────────────────────────
    if len(user_answer.strip()) < 3:
        return {
            "evaluation": {
                "score": 0.0,
                "feedback": "Please give a real answer — I can't evaluate that.",
                "misconceptions": []
            },
            "answered_questions": [*state.get("answered_questions", []), {
                "question": question.get("text", ""),
                "answer": user_answer,
                "score": 0.0,
                "source": question.get("source", ""),
                "staging_id": question.get("staging_id"),
            }],
            "error": ""
        }

    q_type     = question.get("type", "open_ended")
    staging_id = question.get("staging_id")
    source     = question.get("source", "")

    # ── MCQ: Zero-cost exact match ────────────────────────────────────────────
    if q_type == "mcq":
        expected   = question.get("expected", "")
        # For MCQ we match against the first option (correct one, per architecture)
        options    = question.get("options", [])
        correct    = options[0] if options else expected
        is_correct = user_answer.strip().lower() == correct.strip().lower()
        score      = 1.0 if is_correct else 0.0
        result     = EvalResult(
            score=score,
            feedback="Correct! Well done." if is_correct else f"The correct answer was: {correct}",
            misconceptions=[] if is_correct else ["Incorrect option selected"]
        )

    else:
        # ── Open-ended / Code: Groq grades against rubric ─────────────────────
        try:
            prompt = PromptTemplate.from_template(
                "You are an expert grader. Grade the student's answer carefully.\n\n"
                "Question: {question}\n"
                "Expected Answer / Rubric: {expected}\n"
                "Question Type: {q_type}\n"
                "Student's Answer: {answer}\n\n"
                "Evaluate whether the student's answer demonstrates clear understanding.\n"
                "Provide a score 0.0–1.0, constructive feedback, and any specific misconceptions."
            )

            def build_chain(api_key: str):
                from langchain_groq import ChatGroq
                llm = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.0,
                    groq_api_key=api_key
                )
                return prompt | llm.with_structured_output(EvalResult)

            result: EvalResult = await safe_ainvoke_groq(build_chain, {
                "question": question.get("text", ""),
                "expected": question.get("expected", ""),
                "q_type":   q_type,
                "answer":   user_answer,
            })

        except Exception as e:
            return {"error": f"Evaluator LLM failed: {str(e)}"}

    # ── Quality Gate (fire-and-forget, non-blocking) ──────────────────────────
    if source == "staged" and staging_id:
        asyncio.create_task(
            evaluate_and_promote(
                staging_id=staging_id,
                question=question,
                score=result.score,
            )
        )

    # ── Append to answered_questions audit log ────────────────────────────────
    answered = list(state.get("answered_questions", []))
    answered.append({
        "question":   question.get("text", ""),
        "type":       q_type,
        "answer":     user_answer,
        "score":      result.score,
        "feedback":   result.feedback,
        "source":     source,
        "staging_id": staging_id,
        "topic":      question.get("topic", state.get("current_topic", "")),
    })

    return {
        "evaluation": {
            "score":          result.score,
            "feedback":       result.feedback,
            "misconceptions": result.misconceptions,
        },
        "answered_questions": answered,
        "error": ""
    }
