from pydantic import BaseModel, Field
from datetime import datetime

class ChatMessage(BaseModel):
    """Individual chat message model"""
    content: str = Field(..., description="Content of the message")
    role: str = Field(..., description="Role of the message sender (human/ai)")
    session_id: str = Field(..., description="Unique session identifier")
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatResponse(BaseModel):
    """Response model for chat messages"""
    message: str = Field(..., description="Generated response content")
    session_id: str = Field(..., description="Session identifier")
    metrics: dict = Field(default_factory=dict, description="Response metrics")