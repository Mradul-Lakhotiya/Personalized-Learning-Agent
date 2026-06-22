import asyncio
import random
from typing import List
from pydantic import BaseModel, Field
from ...LearnerState import LearnerState
from langchain_core.prompts import PromptTemplate


# ── Output schema ────────────────────────────────────────────────────────────

class NodeResource(BaseModel):
    type: str = Field(description="Resource type: 'video', 'article', or 'academic'")
    title: str = Field(description="Short, descriptive title for the resource")
    url: str = Field(description="Full URL to the resource")
    why_relevant: str = Field(description="One sentence explaining why this resource is useful for this topic")



class NodeResourceOutput(BaseModel):
    summary: str = Field(
        description="2–3 sentence plain-English summary of what this topic covers and why it matters"
    )
    resources: List[NodeResource] = Field(
        description="3 to 5 curated resources drawn from the gathered content",
        min_length=1,
        max_length=5,
    )


async def synthesizer_node(state: LearnerState) -> dict:
    """
    Synthesizer Node (repurposed for visual learning path).

    Instead of generating a full lesson, this node now produces:
    - A 2–3 sentence summary of the node topic
    - 3–5 curated resource links extracted from the gathered content

    This output is used by GET /node/{id}/detail to populate the
    NodeDetailPanel in the frontend.
    """
    await asyncio.sleep(random.uniform(0.2, 0.8))  # prevent parallel burst spikes

    topic = state.get("current_topic", "")
    raw_results = state.get("swarm_raw_results", [])

    if not topic or not raw_results:
        return {"error": "Synthesizer: missing topic or raw results"}

    # Build context from swarm workers (cap to keep within context window)
    context_lines = []
    for res in raw_results[:8]:  # cap at 8 sources
        context_lines.append(
            f"[{res['source_type'].upper()}] {res['title']}\n"
            f"URL: {res['source_url']}\n"
            f"Excerpt: {res['raw_text'][:600]}\n"
        )
    context_str = "\n".join(context_lines)

    prompt = PromptTemplate.from_template(
        "You are an expert AI educator curating learning resources.\n\n"
        "TOPIC: {topic}\n\n"
        "GATHERED CONTENT FROM RESEARCHERS:\n{context}\n\n"
        "TASK:\n"
        "1. Write a 2-3 sentence plain-English summary of what '{topic}' is and why it matters "
        "   in the context of learning this subject. Be concrete and beginner-friendly.\n"
        "2. From the URLs provided above, select the 3-5 most useful resources. "
        "   For each resource, provide its type (video/article/academic), title, URL, "
        "   and one sentence on why it's useful.\n\n"
        "Only use URLs that are present in the gathered content. Do not invent URLs.\n\n"
        "OUTPUT FORMAT: Respond with ONLY a valid JSON object. No markdown, no code fences.\n"
        "The JSON must have exactly this structure:\n"
        "{{\n"
        '  "summary": "2-3 sentence summary here",\n'
        '  "resources": [\n'
        "    {{\n"
        '      "type": "video",\n'
        '      "title": "Resource title",\n'
        '      "url": "https://...",\n'
        '      "why_relevant": "One sentence explanation."\n'
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Generate the JSON now:"
    )

    def build_chain(api_key: str):
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=api_key
        )
        # Raw text output — parse JSON manually
        return prompt | llm

    try:
        import json as _json, re as _re
        from ...Tools.LlmFactory import safe_ainvoke_groq

        raw_response = await safe_ainvoke_groq(
            build_chain,
            {"topic": topic, "context": context_str}
        )
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
            raise ValueError(f"Synthesizer: non-JSON response: {raw_text[:200]}")

        # Validate via Pydantic (type coercion only, not sent to Gemini)
        result = NodeResourceOutput.model_validate(data)

        resources = [
            {
                "type":         r.type,
                "title":        r.title,
                "url":          r.url,
                "why_relevant": r.why_relevant,
            }
            for r in result.resources
        ]

        print(f"[Synthesizer] Generated {len(resources)} resources for '{topic}'")

        return {
            "content_module": result.summary,
            "node_resources_output": {
                "summary":   result.summary,
                "resources": resources,
                "questions": [],
            },
            "error": "",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Synthesizer failed: {str(e)}"}
