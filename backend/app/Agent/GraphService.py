"""
GraphService — AI session lifecycle manager.

Responsibilities:
- Start / resume sessions (LangGraph state + Supabase persistence)
- Collect survey answers (state update + Supabase write per answer)
- Trigger CurriculumPlanner after survey (graph generation + DB save)

Note: Node completion, path history, and CRUD operations are handled
by the Go backend (port 4000), not this service.
"""

import json
import asyncio
from typing import AsyncGenerator, Optional

from .Graph import app_graph
from .LearnerState import LearnerState
from .Tools.Database import Database
from langchain_core.messages import HumanMessage


class GraphService:

    @staticmethod
    def _sse(event_type: str, payload: dict) -> str:
        return f"data: {json.dumps({'type': event_type, **payload})}\n\n"

    # ── Internal: SSE stream over a graph run ─────────────────────────────────

    @staticmethod
    async def _stream(initial_state: Optional[dict], config: dict) -> AsyncGenerator[str, None]:
        try:
            yield GraphService._sse("connection_established", {"message": "Streaming started"})

            async for output in app_graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                for node_name, update in output.items():
                    err = update.get("error", "") if isinstance(update, dict) else ""
                    if err:
                        yield GraphService._sse("error", {"node": node_name, "message": err})
                    else:
                        yield GraphService._sse("node_update", {"node": node_name})

            # Read final state after all nodes have run
            snap = app_graph.get_state(config)
            values = snap.values if snap else {}
            payload = {}

            # ── Onboarding: return first unanswered survey question ───────────
            if not values.get("survey_complete"):
                questions = values.get("survey_questions", [])
                answers   = values.get("survey_answers", [])
                answered  = len(answers)
                if answered < len(questions):
                    payload["phase"] = "onboarding"
                    payload["survey_question"] = questions[answered]
                    payload["survey_progress"] = {
                        "answered": answered,
                        "total":    len(questions),
                    }
                else:
                    payload["phase"] = "onboarding"
                    payload["survey_complete"] = True

            # ── Graph ready: return curriculum ────────────────────────────────
            if values.get("phase") == "graph_ready":
                payload["phase"] = "graph_ready"
                payload["curriculum_graph"]    = values.get("curriculum_graph", {})
                payload["completed_node_ids"]  = values.get("completed_node_ids", [])

            if values.get("error"):
                payload["error"] = values["error"]

            yield GraphService._sse("execution_complete", {"payload": payload})

        except Exception as e:
            import traceback; traceback.print_exc()
            yield GraphService._sse("fatal_error", {"message": str(e)})

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    async def start_session(
        user_id: str,
        thread_id: str,
        initial_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Start a new session or resume an existing one.

        On new session:
          1. Creates a 'onboarding' learning_path row in Supabase
          2. Runs ProfileBuilder → generates survey questions
          3. Streams SSE with the first survey question

        On resume:
          - Returns immediately from existing LangGraph checkpoint
        """
        config = {"configurable": {"thread_id": thread_id}}

        # ── Attempt to resume existing graph state ────────────────────────────
        existing = app_graph.get_state(config)
        if existing and existing.values and existing.values.get("user_id"):
            print(f"[GraphService] Resuming existing session: {thread_id}")
            return GraphService._stream(None, config)

        # ── Attempt to restore from Supabase (backend restart scenario) ───────
        try:
            db = Database()
            saved = await db.get_learning_path(thread_id)
            if saved and saved.get("phase") == "graph_ready":
                # Session already completed — return graph directly
                async def _cached_stream():
                    yield GraphService._sse("connection_established", {"message": "Restoring from DB"})
                    yield GraphService._sse("execution_complete", {"payload": {
                        "phase":            "graph_ready",
                        "curriculum_graph": saved.get("curriculum_graph", {}),
                        "completed_node_ids": saved.get("completed_node_ids", []),
                    }})
                return _cached_stream()
        except Exception as e:
            print(f"[GraphService] DB restore check failed (non-fatal): {e}")

        # ── New session ───────────────────────────────────────────────────────
        # Create a stub path row in Supabase immediately so survey answers
        # can be persisted against a path_id from the first answer.
        path_id = ""
        try:
            db = Database()
            path_id = await db.save_learning_path(
                thread_id=thread_id,
                user_id=user_id,
                learning_goal=initial_prompt or "",
                phase="onboarding",
            )
            print(f"[GraphService] Created DB path row: {path_id}")
        except Exception as e:
            print(f"[GraphService] DB path creation failed (non-fatal): {e}")

        initial_state: dict = {
            "user_id":          user_id,
            "session_id":       thread_id,
            "user_profile":     {},
            "skill_ratings":    {},
            "learning_goal":    initial_prompt or "",

            "curriculum_graph":    {},
            "sections_generated":  0,
            "current_section":     1,
            "completed_node_ids":  [],
            "active_node_id":      None,

            "survey_questions":    [],
            "survey_answers":      [],
            "survey_complete":     False,

            "conversation_history": [HumanMessage(content=initial_prompt)] if initial_prompt else [],
            "last_user_message":    initial_prompt or "",

            "phase":            "onboarding",
            "session_complete": False,
            "error":            "",
            "loop_counters":    {},
            "error_context":    None,

            "swarm_queries":        [],
            "swarm_raw_results":    [],
            "content_module":       "",
            "node_resources_output": {},
            "current_topic":        "",
            "db_path_id":           path_id,

            "total_sessions": 1,
            "flags":          {},
        }
        return GraphService._stream(initial_state, config)

    # ── Survey ────────────────────────────────────────────────────────────────

    @staticmethod
    async def submit_survey_answer(
        thread_id: str,
        user_id: str,
        topic: str,
        rating: int,
    ) -> dict:
        """
        Record one survey answer:
        - Appends to LangGraph state (no graph resumption)
        - Writes to Supabase survey_responses table
        Returns next question dict, or { survey_complete: True }
        """
        config  = {"configurable": {"thread_id": thread_id}}
        snap    = app_graph.get_state(config)
        if not snap or not snap.values:
            return {"error": "No active session found."}

        values    = snap.values
        questions = values.get("survey_questions", [])
        answers   = list(values.get("survey_answers", []))

        matched_q = next((q for q in questions if q["topic"] == topic), None)
        if not matched_q and len(answers) < len(questions):
            matched_q = questions[len(answers)]

        if matched_q:
            answers.append({
                "topic":    topic,
                "rating":   rating,
                "question": matched_q.get("question", ""),
            })

        skill_ratings    = {a["topic"]: a["rating"] for a in answers}
        survey_complete  = len(answers) >= len(questions)

        app_graph.update_state(config, {
            "survey_answers":  answers,
            "skill_ratings":   skill_ratings,
            "survey_complete": survey_complete,
        })

        # Persist answer to Supabase immediately (non-blocking)
        path_id = values.get("db_path_id", "")
        if path_id:
            try:
                db = Database()
                await db.save_survey_response(
                    path_id  = path_id,
                    user_id  = user_id,
                    topic    = topic,
                    question = matched_q.get("question", "") if matched_q else "",
                    rating   = rating,
                )
            except Exception as e:
                print(f"[GraphService] Survey DB write failed (non-fatal): {e}")

        if survey_complete:
            return {"survey_complete": True, "skill_ratings": skill_ratings}

        next_index = len(answers)
        if next_index < len(questions):
            return {
                "survey_complete": False,
                "next_question": questions[next_index],
                "progress": {"answered": next_index, "total": len(questions)},
            }

        return {"survey_complete": True, "skill_ratings": skill_ratings}

    # ── Generate curriculum ───────────────────────────────────────────────────

    @staticmethod
    async def generate_curriculum(thread_id: str, user_id: str) -> AsyncGenerator[str, None]:
        """
        Resume the graph after survey is done → runs CurriculumPlanner.
        After graph is ready, saves to Supabase (learning_paths + path_nodes).
        """
        config = {"configurable": {"thread_id": thread_id}}
        snap   = app_graph.get_state(config)
        if not snap or not snap.values:
            async def _err():
                yield GraphService._sse("error", {"message": "No active session found."})
            return _err()

        async def _run():
            async for event in GraphService._stream(None, config):
                yield event

            # After stream ends, persist to Supabase
            snap2  = app_graph.get_state(config)
            values = snap2.values if snap2 else {}

            if values.get("phase") == "graph_ready":
                graph   = values.get("curriculum_graph", {})
                path_id = values.get("db_path_id", "")
                try:
                    db = Database()
                    # Update the path row with the full graph
                    saved_path_id = await db.save_learning_path(
                        thread_id       = thread_id,
                        user_id         = user_id,
                        learning_goal   = values.get("learning_goal", ""),
                        skill_ratings   = values.get("skill_ratings", {}),
                        curriculum_graph= graph,
                        phase           = "graph_ready",
                    )
                    path_id = saved_path_id or path_id

                    # Bulk insert all nodes
                    nodes = graph.get("nodes", [])
                    if nodes and path_id:
                        await db.save_path_nodes(path_id, user_id, nodes)
                        print(f"[GraphService] Saved {len(nodes)} nodes to DB for path {path_id}")
                except Exception as e:
                    print(f"[GraphService] DB graph save failed (non-fatal): {e}")

        return _run()

    # ── End session ───────────────────────────────────────────────────────────

    @staticmethod
    async def end_session(thread_id: str, user_id: str) -> None:
        """
        Called as a FastAPI background task when POST /agent/end is received.
        Reads the last LangGraph checkpoint and triggers memory consolidation.
        """
        config = {"configurable": {"thread_id": thread_id}}
        snap   = app_graph.get_state(config)
        if snap and snap.values:
            from .Nodes.MemoryConsolidator import consolidate_session
            # await directly — asyncio.create_task() would fail here because
            # this function is itself running inside a background task, not
            # inside a normal coroutine with an attached event loop task group.
            await consolidate_session(snap.values)
            app_graph.update_state(config, {"session_complete": True})
