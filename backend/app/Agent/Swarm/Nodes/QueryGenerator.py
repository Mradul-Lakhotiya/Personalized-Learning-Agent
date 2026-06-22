import asyncio
import random
from pydantic import BaseModel, Field
from ...LearnerState import LearnerState, SwarmQuery
from ...Tools.LlmFactory import safe_ainvoke_groq
from langchain_core.prompts import PromptTemplate


class QueryDecomposition(BaseModel):
    queries: list[SwarmQuery]


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
        "You are an AI learning architect. The user needs to learn: '{topic}'.\n"
        "Generate exactly three search queries to gather the best learning material:\n"
        " - one for general web search (tutorials, documentation)\n"
        " - one for academic/research search\n"
        " - one for video search (YouTube practicals)\n\n"
        "OUTPUT FORMAT: Respond with ONLY a valid JSON object. No markdown, no code fences.\n"
        "The JSON must have exactly this structure:\n"
        "{{\n"
        '  "queries": [\n'
        "    {{\n"
        '      "engine": "web",\n'
        '      "query": "optimized search query here"\n'
        "    }},\n"
        "    {{\n"
        '      "engine": "academic",\n'
        '      "query": "optimized search query here"\n'
        "    }},\n"
        "    {{\n"
        '      "engine": "video",\n'
        '      "query": "optimized search query here"\n'
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Generate the JSON now:"
    )

    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7, groq_api_key=api_key)
        # Raw text — parse JSON manually to avoid Groq schema constraint failures
        return prompt | llm

    try:
        import json as _json, re as _re

        raw_response = await safe_ainvoke_groq(build_chain, {"topic": topic})
        raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

        # Strip markdown fences
        clean = _re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`").strip()

        data = None
        try:
            data = _json.loads(clean)
        except _json.JSONDecodeError:
            match = _re.search(r'\{[\s\S]*\}', clean)
            if match:
                try:
                    data = _json.loads(match.group())
                except _json.JSONDecodeError:
                    pass

        if data is None:
            raise ValueError(f"QueryGenerator: non-JSON response: {raw_text[:200]}")

        # Validate via Pydantic
        result = QueryDecomposition.model_validate(data)

        return {
            "swarm_queries": result.queries,
            "error": ""
        }

    except Exception as e:
        return {"error": f"QueryGenerator failed: {str(e)}"}
