import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
load_dotenv(dotenv_path=".env")

from app.Agent.LearnerState import LearnerState
from app.Agent.Tools.LlmFactory import LlmFactory
from langchain_core.prompts import PromptTemplate
from app.Agent.Nodes.CurriculumPlanner import CurriculumDecision

async def run_debug():
    print("Testing LLM Directly...")
    profile = {
        "id": "123",
        "name": "Guest Learner",
        "learning_goals": ["Learn Python"]
    }
    
    llm = LlmFactory.get_llm(temperature=0.2)
    print("LLM Created")
    
    structured_llm = llm.with_structured_output(CurriculumDecision)
    print("Structured LLM Created")
    
    prompt = PromptTemplate.from_template(
        "You are an expert curriculum planner. Analyze the user's profile and goals.\n"
        "User Profile: {profile}\n\n"
        "Select the most appropriate foundational topic for them to learn right now.\n"
        "Respond strictly with a topic_id (UUID format, can be generated if new), topic_name, and reasoning."
    )
    
    chain = prompt | structured_llm
    
    print("Invoking chain...")
    try:
        result = await chain.ainvoke({"profile": profile})
        print("Result:", result)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run_debug())
