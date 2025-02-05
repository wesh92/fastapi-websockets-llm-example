from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

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

class ChatAvailableModels(str, Enum):
    """Available models for chat"""
    GEMINI_FLASH_1_5 = "google/gemini-flash-1.5"
    QWEN2_5_72b_free = "qwen/qwen2.5-vl-72b-instruct:free"
    GEMINI_FLASH_2_0 = "google/gemini-2.0-flash-001"
    R1_DISTILL_70b = "deepseek/deepseek-r1-distill-llama-70b"
    CODESTRAL_2501 = "mistralai/codestral-2501"

class ChatModelResponse(BaseModel):
    """Response model for chat models"""
    models: list[ChatAvailableModels] = Field(
        default_factory=lambda: list(ChatAvailableModels),
        description="List of available models"
    )

