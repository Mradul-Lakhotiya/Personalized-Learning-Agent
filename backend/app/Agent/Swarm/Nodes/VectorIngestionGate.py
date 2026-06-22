import asyncio
import re
from ...LearnerState import LearnerState
from ...Tools.RAGService import RAGService


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))


async def vector_ingestion_gate_node(state: LearnerState) -> dict:
    """
    VectorIngestionGate — runs after Synthesizer.

    Reads node_resources_output from Synthesizer (summary + resource list)
    and persists it to:
      - Pinecone `node_content` namespace (shared cross-user vector cache)
      - Supabase `path_nodes` row for this user's thread (user-specific cache)
        via RAGService.save_node_resources(thread_id=session_id)

    Resets swarm state fields so the graph is clean for the next node request.
    No LLM call — fully programmatic.
    """
    topic = state.get("current_topic", "unknown")
    thread_id = state.get("session_id", "")          # passed into swarm_input by routes.py
    resources_output = state.get("node_resources_output") or {}
    summary = resources_output.get("summary", state.get("content_module", ""))
    resources = resources_output.get("resources", [])
    questions = resources_output.get("questions", [])

    if not summary and not resources:
        print("[VectorIngestionGate] No output from Synthesizer — skipping persistence.")
        return {
            "swarm_queries": [],
            "swarm_raw_results": [],
            "node_resources_output": {},
        }

    node_slug = _slugify(topic)

    try:
        await RAGService.save_node_resources(
            node_slug=node_slug,
            title=topic,
            description=summary,
            resources=resources,
            questions=questions,
            thread_id=thread_id or None,    # None triggers the Pinecone-only path
        )
        print(f"[VectorIngestionGate] Persisted resources for node '{node_slug}' "
              f"({len(resources)} resources, {len(questions)} questions).")
    except Exception as e:
        print(f"[VectorIngestionGate] WARNING: save failed (non-fatal): {e}")

    return {
        "swarm_queries": [],
        "swarm_raw_results": [],
        "content_module": summary,   # keep summary accessible in state
    }
