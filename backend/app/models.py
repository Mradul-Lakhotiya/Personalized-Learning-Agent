from pydantic import BaseModel, Field
from typing import Optional, Any

class StartSessionRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user.")
    thread_id: str = Field(..., description="Unique identifier for the LangGraph state thread.")

class SubmitAnswerRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user.")
    thread_id: str = Field(..., description="Unique identifier for the LangGraph state thread.")
    answer_text: str = Field(..., description="The textual or code answer submitted by the user.")
