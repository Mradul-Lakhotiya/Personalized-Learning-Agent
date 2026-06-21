import asyncio
import random
from pydantic import BaseModel, Field
from ...LearnerState import LearnerState
from ...Tools.LlmFactory import safe_ainvoke_groq
from langchain_core.prompts import PromptTemplate

class SynthesizedContent(BaseModel):
    markdown_lesson: str = Field(description="The finalized educational lesson formatted in clean Markdown.")

async def synthesizer_node(state: LearnerState) -> dict:
    """
    Synthesizer Node: Merges all raw content from parallel workers into a cohesive lesson.
    """
    # Prevent parallel swarm burst spikes
    await asyncio.sleep(random.uniform(0.3, 1.2))
    
    topic = state.get("current_topic")
    raw_results = state.get("swarm_raw_results", [])
    
    if not topic or not raw_results:
        return {"error": "Missing topic or raw results for Synthesizer"}
        
    # Compile the massive context
    context_str = ""
    for idx, res in enumerate(raw_results):
        context_str += f"--- Source {idx+1} ({res['source_type'].upper()} - {res['title']}) ---\n"
        context_str += f"URL: {res['source_url']}\n"
        context_str += f"Content: {res['raw_text']}\n\n"
        
    prompt = PromptTemplate.from_template(
        "You are an expert AI teacher. You must create a comprehensive, engaging lesson on the topic: '{topic}'.\n\n"
        "Here is the raw data gathered by your web, academic, and multimedia researchers:\n"
        "{context}\n\n"
        "Using ONLY the provided data (synthesize and simplify it), write a clear Markdown lesson.\n"
        "Include a brief introduction, core concepts, practical examples (if any), and references at the bottom."
    )

    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=api_key)
        structured_llm = llm.with_structured_output(SynthesizedContent)
        return prompt | structured_llm
    
    try:
        # Note: Depending on token limits, context_str might need truncation in a real production system
        result: SynthesizedContent = await safe_ainvoke_groq(build_chain, {"topic": topic, "context": context_str})
        
        return {
            "content_module": result.markdown_lesson,
            "next_route": "assessor", # Send back to assessor after teaching
            "error": ""
        }
    except Exception as e:
        return {"error": f"Synthesizer failed: {str(e)}"}
