import json
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import LlmFactory, safe_ainvoke
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
    """
    topic = state.get("current_topic")
    if not topic:
        return {"error": "No current_topic found in state"}
        
    vs = VectorStore()
    
    try:
        # 1. Try to fetch an existing verified question from Pinecone cache
        cached_matches = await vs.asearch(
            query=f"Question about {topic}",
            namespace="questions",
            top_k=1
        )
        
        if cached_matches and cached_matches[0].get("score", 0) > 0.85:
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
            
        # 2. If no cache match, generate a new question using Gemini
        llm = LlmFactory.get_llm(temperature=0.7)
        structured_llm = llm.with_structured_output(QuestionFormat)
        
        prompt = PromptTemplate.from_template(
            "Generate a challenging question to test the user's knowledge on: {topic}.\n"
            "Decide whether 'mcq', 'open_ended', or 'code' is best for this topic.\n"
            "Provide the question, any options (if MCQ), and a strict rubric or expected answer."
        )
        
        chain = prompt | structured_llm
        result: QuestionFormat = await safe_ainvoke(chain, {"topic": topic})
        
        # We don't cache it into "questions" immediately!
        # It goes to "questions_staging" later if the user gets it right.
        
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
