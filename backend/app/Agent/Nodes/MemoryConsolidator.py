"""
MemoryConsolidator — Background session persistence.

Called asynchronously when a session ends (POST /agent/end).
Writes a session summary to:
  1. Supabase `sessions` table (relational history)
  2. Pinecone `user_memory_{user_id}` namespace (semantic memory for future personalisation)
"""

import asyncio
from datetime import datetime, timezone
from ..Tools.Database import Database
from ..Tools.VectorStore import VectorStore
from ..Tools.LlmFactory import safe_ainvoke_gemini
from langchain_core.prompts import PromptTemplate


async def consolidate_session(state: dict) -> None:
    user_id    = state.get("user_id")
    session_id = state.get("session_id")
    if not user_id or not session_id:
        print("[MemoryConsolidator] Missing user_id or session_id — skipping.")
        return

    print(f"[MemoryConsolidator] Starting consolidation for session {session_id[:8]}...")

    learning_goal      = state.get("learning_goal", "Unknown goal")
    completed_node_ids = state.get("completed_node_ids", [])
    graph              = state.get("curriculum_graph", {})
    total_nodes        = len(graph.get("nodes", []))

    # ── 1. Generate a concise session summary (Gemini) ────────────────────────
    summary = (
        f"Session ended for goal: '{learning_goal}'. "
        f"Completed {len(completed_node_ids)} of {total_nodes} nodes."
    )
    try:
        completed_titles = [
            n["title"] for n in graph.get("nodes", [])
            if n["id"] in completed_node_ids
        ]
        if completed_titles:
            prompt = PromptTemplate.from_template(
                "A learner finished a study session with the goal: '{goal}'.\n"
                "They marked these topics as completed: {topics}.\n\n"
                "Write a 2–3 sentence summary of their progress, what they accomplished, "
                "and a brief suggestion for what to focus on next."
            )
            def build_chain(api_key: str):
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key
                )
                return prompt | llm

            result = await safe_ainvoke_gemini(build_chain, {
                "goal":   learning_goal,
                "topics": ", ".join(completed_titles[:20]),  # cap to avoid context overflow
            })
            summary = result.content if hasattr(result, "content") else str(result)
            print(f"[MemoryConsolidator] Summary generated.")
    except Exception as e:
        print(f"[MemoryConsolidator] Gemini summary failed (non-fatal): {e}")

    # ── 2. Write to Supabase sessions table ──────────────────────────────────
    try:
        db = Database()
        await db.save_session(
            session_id = session_id,
            user_id    = user_id,
            summary    = summary,
            topics     = [learning_goal],
        )
        print(f"[MemoryConsolidator] Session saved to Supabase.")
    except Exception as e:
        print(f"[MemoryConsolidator] Supabase session save failed (non-fatal): {e}")

    # ── 3. Upsert semantic memory to Pinecone ────────────────────────────────
    try:
        vs = VectorStore()
        namespace = f"user_memory_{user_id}"
        await vs.aupsert(
            texts=[summary],
            metadatas=[{
                "session_id":    session_id,
                "type":          "session_summary",
                "learning_goal": learning_goal,
                "nodes_done":    len(completed_node_ids),
                "nodes_total":   total_nodes,
                "timestamp":     datetime.now(timezone.utc).isoformat(),
            }],
            namespace=namespace,
        )
        print(f"[MemoryConsolidator] Semantic memory written to Pinecone: {namespace}")
    except Exception as e:
        print(f"[MemoryConsolidator] Pinecone write failed (non-fatal): {e}")

    print(f"[MemoryConsolidator] Consolidation complete for session {session_id[:8]}")
