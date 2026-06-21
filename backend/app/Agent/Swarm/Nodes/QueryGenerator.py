import asyncio
import random
from pydantic import BaseModel, Field
from ...LearnerState import LearnerState, SwarmQuery
from ...Tools.LlmFactory import safe_ainvoke_groq
from langchain_core.prompts import PromptTemplate

class QueryDecomposition(BaseModel):
    queries: list[SwarmQuery] = Field(description="A list of specific search queries tailored for web, academic, and video search engines.")

async def query_generator_node(state: LearnerState) -> dict:
    """
    Decomposer Node: Breaks down the target topic into 3 specific queries,
    one for each worker (web, academic, video).
    """
    # Prevent parallel swarm burst spikes
    await asyncio.sleep(random.uniform(0.3, 1.2))
    
    topic = state.get("current_topic")
    if not topic:
        return {"error": "Missing current_topic for Swarm"}
        
    prompt = PromptTemplate.from_template(
        "You are an AI learning architect. The user needs to learn the topic: '{topic}'.\n"
        "We have three search workers: 'web' (for general tutorials/docs), 'academic' (for research papers), and 'video' (for YouTube practicals).\n"
        "Generate exactly one highly optimized search query for each engine to gather the best learning material.\n\n"
        "Respond with a list of dictionaries with 'engine' ('web', 'academic', 'video') and the optimized 'query' string."
    )
    
    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7, groq_api_key=api_key)
        structured_llm = llm.with_structured_output(QueryDecomposition)
        return prompt | structured_llm
    
    try:
        result: QueryDecomposition = await safe_ainvoke_groq(build_chain, {"topic": topic})
        
        return {
            "swarm_queries": result.queries,
            "error": ""
        }
    except Exception as e:
        return {"error": f"QueryGenerator LLM failed: {str(e)}"}
