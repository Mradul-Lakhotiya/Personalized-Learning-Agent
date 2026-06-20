import json
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
    async def run_and_stream(initial_state: dict, config: dict) -> AsyncGenerator[str, None]:
        """
        Executes the graph and yields state updates formatted as SSE.
        """
        try:
            # Yield initial connection success
            yield GraphService._format_sse("connection_established", {"message": "Streaming started"})

            # Stream graph updates
            async for output in app_graph.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in output.items():
                    # If an error occurred in a node, we should ideally stream it
                    if "error" in state_update and state_update["error"]:
                        yield GraphService._format_sse("error", {"node": node_name, "message": state_update["error"]})
                    else:
                        yield GraphService._format_sse("node_update", {"node": node_name})
            
            # Check the final state after the graph pauses or finishes
            state = app_graph.get_state(config)
            
            if state.next:
                # Graph paused (e.g. before answer_evaluator)
                yield GraphService._format_sse("paused", {"next_node": list(state.next)[0]})
            
            # Yield the final payload data so the frontend can render the question or lesson
            # We access the values using state.values
            values = state.values
            payload = {}
            if "current_question" in values:
                payload["current_question"] = values["current_question"]
            if "content_module" in values:
                payload["content_module"] = values["content_module"]
                
            yield GraphService._format_sse("execution_complete", {"payload": payload})

        except Exception as e:
            yield GraphService._format_sse("fatal_error", {"message": str(e)})

    @staticmethod
    async def start_session(user_id: str, thread_id: str) -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Check if thread already has state
        existing_state = app_graph.get_state(config)
        
        if existing_state and existing_state.values:
            # Session already active, just resume from current state
            # If it's paused, we just yield the paused state and current data
            return GraphService.run_and_stream(None, config)
        
        # Completely new session
        initial_state = {
            "user_id": user_id,
            "loop_counters": {},
            "recent_history": [],
            "swarm_queries": [],
            "swarm_raw_results": [],
            "content_module": ""
        }
        
        return GraphService.run_and_stream(initial_state, config)

    @staticmethod
    async def submit_answer(thread_id: str, answer_text: str) -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Ensure graph is currently paused
        existing_state = app_graph.get_state(config)
        if not existing_state or not existing_state.next:
            async def error_generator():
                yield GraphService._format_sse("error", {"message": "No active paused session found for this thread."})
            return error_generator()

        # Update the state with the user's answer
        app_graph.update_state(config, {"user_answer": answer_text})
        
        # Resume the graph (passing None to initial_state resumes from checkpoint)
        return GraphService.run_and_stream(None, config)
