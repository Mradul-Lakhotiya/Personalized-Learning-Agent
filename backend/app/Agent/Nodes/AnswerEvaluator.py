import json
import os
import asyncio
import urllib.request
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState
from ..Tools.LlmFactory import LlmFactory, safe_ainvoke
from langchain_core.prompts import PromptTemplate

class EvalResult(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0 (1.0 being perfectly correct)")
    feedback: str = Field(description="Constructive feedback explaining the grade")
    misconceptions: list[str] = Field(description="List of identified misconceptions, or empty list")

async def answer_evaluator_node(state: LearnerState) -> dict:
    """
    Node 6: Answer Evaluator
    Grades the user's answer. Uses LLM for text, and Piston API for code execution.
    """
    question = state.get("current_question", {})
    user_answer = state.get("user_answer", "")
    
    if not question or not user_answer:
        return {"error": "Missing question or user answer in state"}
        
    q_type = question.get("type")
    
    # --- Code Evaluation (Piston) ---
    if q_type == "code":
        try:
            # Assuming user_answer is the code snippet, and question['expected'] contains test cases.
            # For simplicity in this scaffold, we just execute the code to see if it runs cleanly.
            api_url = os.getenv("PISTON_API_URL", "https://emkc.org/api/v2/piston")
            
            payload = {
                "language": "python",
                "version": "3.10.0",
                "files": [{"content": user_answer}],
                "stdin": "",
                "args": [],
                "compile_timeout": 10000,
                "run_timeout": 3000,
                "compile_memory_limit": -1,
                "run_memory_limit": -1
            }
            
            def run_piston():
                req = urllib.request.Request(
                    f"{api_url}/execute",
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read().decode('utf-8'))
                    
            piston_result = await asyncio.to_thread(run_piston)
            
            run_output = piston_result.get("run", {})
            code = run_output.get("code", 1)
            output = run_output.get("output", "")
            
            if code == 0:
                # Code ran successfully, now ask LLM to verify if it actually solves the prompt
                pass
            else:
                return {
                    "evaluation": {
                        "score": 0.0,
                        "feedback": f"Your code threw an error:\n{output}",
                        "misconceptions": ["Syntax or Runtime Error"]
                    },
                    "error": ""
                }
        except Exception as e:
            return {"error": f"Piston execution failed: {str(e)}"}
            
    # --- Text / General Evaluation (Gemini) ---
    try:
        llm = LlmFactory.get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(EvalResult)
        
        prompt = PromptTemplate.from_template(
            "You are an expert grader. Grade the student's answer.\n\n"
            "Question: {question}\n"
            "Expected/Rubric: {expected}\n"
            "Student's Answer: {answer}\n\n"
            "Provide a score from 0.0 to 1.0, feedback, and any misconceptions."
        )
        
        chain = prompt | structured_llm
        
        inputs = {
            "question": question.get("text"),
            "expected": question.get("expected"),
            "answer": user_answer
        }
        
        result: EvalResult = await safe_ainvoke(chain, inputs)
        
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
