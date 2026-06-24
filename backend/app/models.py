from pydantic import BaseModel, Field
from typing import Optional


class StartSessionRequest(BaseModel):
    thread_id:      str            = Field(..., description="Unique LangGraph thread ID.")
    initial_prompt: Optional[str]  = Field(None, description="The user's stated learning goal.")


class SurveyAnswerRequest(BaseModel):
    thread_id: str = Field(..., description="Unique thread ID.")
    topic:     str = Field(..., description="The prerequisite topic being rated.")
    rating:    int = Field(..., ge=0, le=5, description="Self-assessed knowledge 0–5.")


class GenerateCurriculumRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID. Survey must be complete.")


class GenerateNodeRequest(BaseModel):
    """Request body for POST /agent/generate-node (content swarm)."""
    node_id:       str = Field(..., description="URL-safe slug of the node (e.g. 'python-basics').")
    thread_id:     str = Field(..., description="LangGraph thread ID of the active session.")
    title:         str = Field(..., description="Human-readable node title.")
    description:   str = Field("",  description="1–2 sentence node description.")
    learning_goal: str = Field("",  description="The user's overall learning goal (context for swarm).")

