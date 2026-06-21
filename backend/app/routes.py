from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from .models import StartSessionRequest, SubmitAnswerRequest
from .Agent.GraphService import GraphService
from .api.auth import get_current_user

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Operations"])

@router.post("/start")
async def start_session(request: StartSessionRequest, user_id: str = Depends(get_current_user)):
    """
    Initializes a new LangGraph session or resumes an existing one.
    Returns a Server-Sent Events (SSE) stream of execution updates.
    """
    generator = await GraphService.start_session(
        user_id=user_id,
        thread_id=request.thread_id
    )
    
    return StreamingResponse(
        generator, 
        media_type="text/event-stream"
    )

@router.post("/reply")
async def submit_answer(request: SubmitAnswerRequest, user_id: str = Depends(get_current_user)):
    """
    Injects the user's answer into a paused graph state and resumes execution.
    Returns a Server-Sent Events (SSE) stream of execution updates.
    """
    generator = await GraphService.submit_answer(
        thread_id=request.thread_id,
        answer_text=request.answer
    )
    
    return StreamingResponse(
        generator, 
        media_type="text/event-stream"
    )

@router.post("/end")
async def end_session(request: StartSessionRequest, user_id: str = Depends(get_current_user)):
    """
    Ends the current session and triggers background consolidation.
    Returns immediately while consolidation happens in the background.
    """
    await GraphService.end_session(request.thread_id)
    return {"status": "success", "message": "Session consolidation started in background"}
