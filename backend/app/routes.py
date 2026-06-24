"""
FastAPI routes for PathMind AI.

All endpoints require Supabase JWT auth (Authorization: Bearer <token>).
SSE endpoints stream events using text/event-stream.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse

from .models import (
    StartSessionRequest,
    SurveyAnswerRequest,
    GenerateCurriculumRequest,
    GenerateNodeRequest,
)
from .Agent.GraphService import GraphService
from .Agent.Tools.RAGService import RAGService
from .Agent.Tools.Database import Database
from .Agent.Swarm.SwarmGraph import swarm_graph
from .api.auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["PathMind"])


# ── Session Lifecycle ─────────────────────────────────────────────────────────

@router.post("/agent/start")
async def start_session(
    request: StartSessionRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Start a new learning session or resume an existing one.
    Returns SSE stream.
    On new session: ProfileBuilder runs → generates survey questions.
    On existing session: returns current state.
    """
    generator = await GraphService.start_session(
        user_id        = user_id,
        thread_id      = request.thread_id,
        initial_prompt = request.initial_prompt,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/agent/end")
async def end_session(
    request: StartSessionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """End session and trigger background memory consolidation."""
    background_tasks.add_task(GraphService.end_session, request.thread_id, user_id)
    return {"status": "success", "message": "Session ended. Memory consolidation queued."}


# ── Survey (Onboarding) ───────────────────────────────────────────────────────

@router.post("/agent/survey-answer")
async def submit_survey_answer(
    request: SurveyAnswerRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Submit one self-assessment answer (topic + rating 0–5).
    Returns the next survey question, or { survey_complete: true } when done.
    """
    result = await GraphService.submit_survey_answer(
        thread_id = request.thread_id,
        user_id   = user_id,
        topic     = request.topic,
        rating    = request.rating,
    )
    return result


@router.post("/agent/generate-curriculum")
async def generate_curriculum(
    request: GenerateCurriculumRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Trigger CurriculumPlanner after all survey answers are submitted.
    Returns SSE stream. On completion, saves graph to Supabase.
    """
    generator = await GraphService.generate_curriculum(request.thread_id, user_id)
    return StreamingResponse(generator, media_type="text/event-stream")


# ── Node Content Generation ───────────────────────────────────────────────────
# Note: CRUD operations (complete_node, get_user_paths, get_curriculum) are
# handled by the Go backend (port 4000) which owns all state/CRUD operations.

@router.post("/agent/generate-node")
async def generate_node_content(
    req: GenerateNodeRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Trigger content swarm for a node.
    Cache-first: checks Supabase → Pinecone before running the swarm.
    Returns an SSE stream that yields {"type": "ready"} when done.
    """
    # 1. Check cache (Pinecone / Supabase) to avoid re-running the swarm
    cached = await RAGService.get_node_resources(
        node_slug        = req.node_id,
        node_title       = req.title,
        node_description = req.description,
    )

    if cached:
        # Cache hit — save directly to the user's path_nodes row and stream 'ready'
        db = Database()
        await db.cache_node_content_by_thread(
            thread_id = req.thread_id,
            node_id   = req.node_id,
            resources = cached.get("resources", []),
            questions = cached.get("questions", []),
        )

        async def _cached():
            yield GraphService._sse("ready", {"source": "pinecone_cache"})

        return StreamingResponse(_cached(), media_type="text/event-stream")

    # 2. Cache miss — run the content swarm and stream progress via SSE
    async def _stream_swarm():
        yield GraphService._sse("status", {"message": "Gathering resources"})

        # Use a unique config per node so swarms don't collide across concurrent requests
        config = {"configurable": {"thread_id": f"swarm-{req.node_id}"}}
        swarm_input = {
            "current_topic":         req.title,
            "swarm_queries":         [],
            "swarm_raw_results":     [],
            "node_resources_output": {},
            "content_module":        "",
            "user_id":               user_id,
            "session_id":            req.thread_id,
            "learning_goal":         req.learning_goal,
        }

        try:
            final_state = await swarm_graph.ainvoke(swarm_input)

            resources_output = final_state.get("node_resources_output") or {}
            resources = resources_output.get("resources", [])
            questions = resources_output.get("questions", [])

            if resources or questions:
                db = Database()
                await db.cache_node_content_by_thread(
                    thread_id = req.thread_id,
                    node_id   = req.node_id,
                    resources = resources,
                    questions = questions,
                )

            yield GraphService._sse("ready", {"source": "swarm"})

        except Exception as e:
            yield GraphService._sse("error", {"message": f"Swarm failed: {e}"})

    return StreamingResponse(_stream_swarm(), media_type="text/event-stream")
