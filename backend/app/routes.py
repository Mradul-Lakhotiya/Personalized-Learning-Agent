from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from .models import StartSessionRequest, SubmitAnswerRequest
from .Agent.GraphService import GraphService

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Operations"])

@router.post("/start")
async def start_session(request: StartSessionRequest):
    """
    Initializes a new LangGraph session or resumes an existing one.
    Returns a Server-Sent Events (SSE) stream of execution updates.
    """
    generator = await GraphService.start_session(
        user_id=request.user_id,
        thread_id=request.thread_id
    )
    
    return StreamingResponse(
        generator, 
        media_type="text/event-stream"
    )

@router.post("/reply")
async def submit_answer(request: SubmitAnswerRequest):
    """
    Injects the user's answer into a paused graph state and resumes execution.
    Returns a Server-Sent Events (SSE) stream of execution updates.
    """
    generator = await GraphService.submit_answer(
        thread_id=request.thread_id,
        answer_text=request.answer_text
    )
    
    return StreamingResponse(
        generator, 
        media_type="text/event-stream"
    )
