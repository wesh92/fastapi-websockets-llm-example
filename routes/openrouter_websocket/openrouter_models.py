from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from warnings import deprecated

@deprecated("Switch To LangChain System Messages")
class Message(BaseModel):
    """Individual message in the chat sequence"""

    role: Literal["user", "assistant", "system"]
    content: str


class OpenRouterRequestModel(BaseModel):
    """Model for incoming WebSocket requests"""

    messages: List[Message]
    model: Optional[str] = Field(default="google/gemini-flash-1.5")
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    repetition_penalty: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=0, ge=0)


class OpenRouterConfigModel(BaseModel):
    """Configuration for OpenRouter API"""

    api_key: str
    site_url: Optional[str] = ""
    site_name: Optional[str] = ""
    default_model: str = "google/gemini-flash-1.5"
    api_url: str = "https://openrouter.ai/api/v1/chat/completions"


class WebSocketStateModel(BaseModel):
    """Model for tracking WebSocket connection state"""

    connection_id: str
    connected_at: datetime
    last_activity: datetime
    total_messages: int = 0
    current_request: Optional[OpenRouterRequestModel] = None


class OpenRouterErrorResponse(BaseModel):
    """Model for error responses"""

    type: Literal["error"]
    message: str
    code: Optional[str] = None
