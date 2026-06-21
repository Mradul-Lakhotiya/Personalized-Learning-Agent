from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import safe_ainvoke_groq, safe_ainvoke_gemini
from langchain_core.prompts import PromptTemplate

class EvalResult(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0 (1.0 being perfectly correct)")
    feedback: str = Field(description="Constructive feedback explaining the grade")
    misconceptions: list[str] = Field(description="List of identified misconceptions, or empty list")

async def answer_evaluator_node(state: LearnerState) -> dict:
    """
    Node 5: Answer Evaluator
    Grades the user's answer against the question rubric.

    LLM Routing:
    - Groq (llama-3.3-70b-versatile): Fast consolidation — comparing the answer
      against the rubric, scoring, and extracting misconceptions (data processing).
    - Gemini (gemini-2.5-flash): NOT used here — reserved for generation tasks.
    """
    question = state.get("current_question", {})
    user_answer = state.get("user_answer", "")

    if not question or not user_answer:
        return {"error": "Missing question or user answer in state"}

    # ── Input Sanity Check ──────────────────────────────────────────────────
    if len(user_answer.strip()) < 3:
        return {
            "evaluation": {
                "score": 0.0,
                "feedback": "Please give a real answer — I can't evaluate that.",
                "misconceptions": []
            },
            "error": ""
        }

    q_type = question.get("type", "open_ended")

    # ── MCQ: Zero-cost exact match (no LLM needed) ──────────────────────────
    if q_type == "mcq":
        expected = question.get("expected", "")
        is_correct = user_answer.strip().lower() == expected.strip().lower()
        return {
            "evaluation": {
                "score": 1.0 if is_correct else 0.0,
                "feedback": "Correct!" if is_correct else f"The correct answer was: {expected}",
                "misconceptions": [] if is_correct else ["Incorrect option selected"]
            },
            "error": ""
        }

    # ── All other types: Groq consolidates/grades the answer ────────────────
    # Groq is used here because this is fundamentally a data consolidation task:
    # compare the user's answer text against the rubric and extract a structured grade.
    try:
        prompt = PromptTemplate.from_template(
            "You are an expert grader. Grade the student's answer carefully.\n\n"
            "Question: {question}\n"
            "Expected Answer / Rubric: {expected}\n"
            "Question Type: {q_type}\n"
            "Student's Answer: {answer}\n\n"
            "Evaluate whether the student's answer demonstrates understanding of the key concepts.\n"
            "Provide a score from 0.0 to 1.0, constructive feedback, and any specific misconceptions."
        )

        def build_chain(api_key: str):
            from langchain_groq import ChatGroq
            llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0, groq_api_key=api_key)
            structured_llm = llm.with_structured_output(EvalResult)
            return prompt | structured_llm

        inputs = {
            "question": question.get("text", ""),
            "expected": question.get("expected", ""),
            "q_type": q_type,
            "answer": user_answer
        }

        result: EvalResult = await safe_ainvoke_groq(build_chain, inputs)

        return {
            "evaluation": {
                "score": result.score,
                "feedback": result.feedback,
                "misconceptions": result.misconceptions
            },
            "error": ""
        }

    except Exception as e:
        return {"error": f"Evaluator failed: {str(e)}"}
