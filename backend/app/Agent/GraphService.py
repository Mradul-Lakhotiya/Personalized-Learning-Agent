import json
import uuid
import asyncio
from typing import AsyncGenerator
from .Graph import app_graph
from .LearnerState import LearnerState

class GraphService:
    @staticmethod
    def _format_sse(event_type: str, payload: dict) -> str:
        """Format an event into Server-Sent Events (SSE) format."""
        data = {"type": event_type, **payload}
        return f"data: {json.dumps(data)}\n\n"

    @staticmethod
    async def run_and_stream(initial_state: dict | None, config: dict) -> AsyncGenerator[str, None]:
        """
        Executes (or resumes) the graph and yields state updates as SSE.
        """
        try:
            yield GraphService._format_sse("connection_established", {"message": "Streaming started"})

            # Stream node-by-node updates
            async for output in app_graph.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in output.items():
                    print(f"DEBUG: node_name={node_name}, type(state_update)={type(state_update)}, state_update={state_update}")
                    if isinstance(state_update, dict):
                        err = state_update.get("error", "")
                    else:
                        err = ""
                    if err:
                        yield GraphService._format_sse("error", {"node": node_name, "message": err})
                    else:
                        yield GraphService._format_sse("node_update", {"node": node_name})

            # Read final state after graph pauses or finishes
            state = app_graph.get_state(config)

            if state.next:
                yield GraphService._format_sse("paused", {"next_node": list(state.next)[0]})

            # Build the payload the frontend needs to render the UI
            values = state.values
            payload = {}

            if values.get("current_question"):
                payload["current_question"] = values["current_question"]

            if values.get("content_module"):
                payload["content_module"] = values["content_module"]

            if values.get("evaluation"):
                payload["evaluation"] = values["evaluation"]

            if values.get("current_topic"):
                payload["current_topic"] = values["current_topic"]

            if values.get("session_complete"):
                payload["session_complete"] = True

            yield GraphService._format_sse("execution_complete", {"payload": payload})

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield GraphService._format_sse("fatal_error", {"message": str(e)})

    @staticmethod
    async def start_session(user_id: str, thread_id: str) -> AsyncGenerator[str, None]:
        """
        Initializes a new LangGraph session or resumes an existing one for the thread.
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Check if thread already has a checkpoint
        existing_state = app_graph.get_state(config)

        if existing_state and existing_state.values and existing_state.values.get("user_id"):
            # Already active — resume from checkpoint
            return GraphService.run_and_stream(None, config)

        # Brand-new session: build full initial state with defaults for all required fields
        initial_state: dict = {
            # Identity
            "user_id": user_id,
            "session_id": thread_id,

            # Profile (filled by ProfileBuilder node)
            "user_profile": {},
            "skill_map": {},

            # Curriculum (filled by CurriculumPlanner node)
            "master_curriculum": [],
            "current_unit_index": 0,
            "current_topic": "",
            "current_topic_id": "",
            "current_subtopic": "",

            # Dialogue
            "conversation_history": [],
            "last_user_message": "",

            # Assessment
            "current_question": None,
            "user_answer": "",
            "evaluation": {},
            "answered_questions": [],
            "current_batch_scores": [],
            "consecutive_streak": 0,

            # Routing
            "next_route": "assessor",
            "remediation_needed": False,
            "session_complete": False,

            # Circuit breakers
            "loop_counters": {},
            "error_context": None,
            "error": "",

            # Swarm
            "swarm_queries": [],
            "swarm_raw_results": [],
            "content_module": "",

            # Meta
            "total_sessions": 1,
            "flags": {},
        }

        return GraphService.run_and_stream(initial_state, config)

    @staticmethod
    async def submit_answer(thread_id: str, answer_text: str) -> AsyncGenerator[str, None]:
        """
        Injects the user's answer into a paused graph and resumes execution.
        """
        config = {"configurable": {"thread_id": thread_id}}

        existing_state = app_graph.get_state(config)
        if not existing_state or not existing_state.next:
            async def error_gen():
                yield GraphService._format_sse("error", {"message": "No active paused session found for this thread."})
            return error_gen()

        # Inject the answer into state
        app_graph.update_state(config, {"user_answer": answer_text, "last_user_message": answer_text})

        # Resume from checkpoint
        return GraphService.run_and_stream(None, config)
