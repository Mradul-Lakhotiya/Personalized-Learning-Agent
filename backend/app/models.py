from pydantic import BaseModel, Field
from typing import Optional, Any

class StartSessionRequest(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the LangGraph state thread.")

class SubmitAnswerRequest(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the LangGraph state thread.")
    answer: str = Field(..., description="The textual or code answer submitted by the user.")
