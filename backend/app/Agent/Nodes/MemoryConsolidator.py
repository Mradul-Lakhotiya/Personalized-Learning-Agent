import asyncio
from typing import Any
from datetime import datetime, timezone
from ..LearnerState import LearnerState
from ..Tools.Database import Database
from ..Tools.VectorStore import VectorStore
from ..Tools.LlmFactory import safe_ainvoke_gemini
from langchain_core.prompts import PromptTemplate

async def consolidate_session(state: dict[str, Any]) -> None:
    """
    Background Task: Memory Consolidator
    Triggered asynchronously when a session ends to persist all transient
    data to long-term storage (Postgres and Pinecone).
    
    Operations:
    1. Summarizes the conversation_history using Gemini
    2. Writes session summary to Postgres `sessions` table
    3. Batch inserts `answered_questions` to Postgres
    4. Upserts summary to Pinecone `user_memory_{user_id}` namespace
    """
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    if not user_id or not session_id:
        print("[MemoryConsolidator] ⚠️ Missing user_id or session_id. Aborting.")
        return

    print(f"[MemoryConsolidator] Starting background consolidation for session {session_id[:8]}...")
    
    db = Database()
    vs = VectorStore()
    
    # ── 1. Summarize Session (Gemini) ──────────────────────────────────────────
    conversation_history = state.get("conversation_history", [])
    history_text = "\n".join([f"{msg.type}: {msg.content}" for msg in conversation_history])
    
    summary = "No conversation history available for this session."
    if len(conversation_history) > 0:
        try:
            prompt = PromptTemplate.from_template(
                "You are an AI tasked with summarizing a tutoring session for long-term memory.\n\n"
                "Session History:\n{history}\n\n"
                "Write a concise 3-5 sentence summary of what the user learned, what they struggled with, "
                "and what their general performance was like. Be objective and factual."
            )
            
            def build_chain(api_key: str):
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key)
                return prompt | llm
                
            result = await safe_ainvoke_gemini(build_chain, {"history": history_text[:8000]}) # limit context window
            summary = result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            print(f"[MemoryConsolidator] ⚠️ Gemini summary failed (non-fatal): {e}")
            summary = "Session finished, but summary generation failed."

    # ── 2. Write to `sessions` table (Postgres) ───────────────────────────────
    try:
        await asyncio.to_thread(
            db.client.table("sessions").upsert({
                "id": session_id,
                "user_id": user_id,
                "summary": summary,
                "topics_covered": [state.get("current_topic")] if state.get("current_topic") else [],
                "ended_at": datetime.now(timezone.utc).isoformat()
            }).execute
        )
        print(f"[MemoryConsolidator] ✅ Saved session summary to Postgres.")
    except Exception as e:
        print(f"[MemoryConsolidator] ⚠️ Failed to save session to Postgres: {e}")

    # ── 3. Batch insert `answered_questions` (Postgres) ───────────────────────
    answered = state.get("answered_questions", [])
    if answered:
        payloads = []
        for ans in answered:
            payloads.append({
                "user_id": user_id,
                "session_id": session_id,
                "question_text": ans.get("question", ""),
                "user_answer": ans.get("answer", ""),
                "is_correct": ans.get("score", 0.0) >= 0.8,
                "score": ans.get("score", 0.0),
                "feedback": ans.get("feedback", ""),
                "topic": ans.get("topic", state.get("current_topic", "")),
            })
        try:
            await asyncio.to_thread(
                db.client.table("answered_questions").insert(payloads).execute
            )
            print(f"[MemoryConsolidator] ✅ Inserted {len(payloads)} answered questions to Postgres.")
        except Exception as e:
            print(f"[MemoryConsolidator] ⚠️ Failed to insert answered questions: {e}")

    # ── 4. Upsert Semantic Memory (Pinecone) ──────────────────────────────────
    try:
        namespace = f"user_memory_{user_id}"
        await vs.aupsert(
            texts=[summary],
            metadatas=[{
                "session_id": session_id,
                "type": "session_summary",
                "topics": state.get("current_topic", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }],
            namespace=namespace
        )
        print(f"[MemoryConsolidator] ✅ Upserted semantic memory to Pinecone namespace: {namespace}.")
    except Exception as e:
        print(f"[MemoryConsolidator] ⚠️ Failed to upsert semantic memory to Pinecone: {e}")

    print(f"[MemoryConsolidator] 🎉 Consolidation complete for session {session_id[:8]}")
