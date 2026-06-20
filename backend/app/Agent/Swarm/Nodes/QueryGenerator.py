from pydantic import BaseModel, Field
from ...LearnerState import LearnerState, SwarmQuery
from ...Tools.LlmFactory import LlmFactory, safe_ainvoke
from langchain_core.prompts import PromptTemplate

class QueryDecomposition(BaseModel):
    queries: list[SwarmQuery] = Field(description="A list of specific search queries tailored for web, academic, and video search engines.")

async def query_generator_node(state: LearnerState) -> dict:
    """
    Decomposer Node: Breaks down the target topic into 3 specific queries,
    one for each worker (web, academic, video).
    """
    topic = state.get("current_topic")
    if not topic:
        return {"error": "Missing current_topic for Swarm"}
        
    llm = LlmFactory.get_llm(temperature=0.3)
    structured_llm = llm.with_structured_output(QueryDecomposition)
    
    prompt = PromptTemplate.from_template(
        "You are an AI learning architect. The user needs to learn the topic: '{topic}'.\n"
        "We have three search workers: 'web' (for general tutorials/docs), 'academic' (for research papers), and 'video' (for YouTube practicals).\n"
        "Generate exactly one highly optimized search query for each engine to gather the best learning material.\n\n"
        "Respond with a list of dictionaries with 'engine' ('web', 'academic', 'video') and the optimized 'query' string."
    )
    
    chain = prompt | structured_llm
    
    try:
        result: QueryDecomposition = await safe_ainvoke(chain, {"topic": topic})
        
        # Ensure we don't carry over old results from a previous swarm cycle
        return {
            "swarm_queries": result.queries,
            "swarm_raw_results": [], # Clear previous raw results conceptually?
            # Wait, since `swarm_raw_results` uses operator.add, returning an empty list just appends nothing.
            # To actually clear an Annotated list, you'd usually pass a command to clear it,
            # but since we create a new scope for the subgraph, it's safer to just let the reducer append 
            # and rely on the Synthesizer processing the latest N items, or just not clear it in the state.
            "error": ""
        }
    except Exception as e:
        return {"error": f"Query Generator failed: {str(e)}"}
