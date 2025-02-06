from pathlib import Path
import tomllib
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
from .chat_models import (
    ChatAvailableModels,
    ChatMessage,
    ChatModelResponse,
    ChatResponse,
)
from .chat_service import ChatService, SQLiteChatMessageHistory
from langchain_openai import ChatOpenAI as OpenAIChatModel
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

websocket_router = APIRouter()
http_router = APIRouter()

# Get the directory of the current script
current_dir = Path(__file__).parent
secrets_path = current_dir.parent.parent / "secrets.toml"
assert secrets_path.exists(), f"Secrets file not found at {secrets_path}"
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

OPENROUTER_SECRET = secrets["OPENROUTER_SECRET"]


def create_model(model_name: str) -> OpenAIChatModel:
    """
    Create a new OpenAI chat model instance with the specified model name.

    Args:
        model_name: The name of the model to use

    Returns:
        OpenAIChatModel: Configured model instance

    Raises:
        ValueError: If the model name is not in ChatAvailableModels
    """
    if model_name not in ChatAvailableModels.__members__.values():
        raise ValueError(f"Model {model_name} is not supported")

    return OpenAIChatModel(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_SECRET,
        model=model_name,
        temperature=0.7,
        max_tokens=1000,
        streaming=True,
    )


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return SQLiteChatMessageHistory(session_id)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.session_models: Dict[str, OpenAIChatModel] = {}
        self.chat_service = ChatService()

    async def connect(self, websocket: WebSocket, session_id: str):
        """Handle new WebSocket connection"""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
            # Initialize chat service for this session
            self.chat_service.initialize_session(session_id)

        self.active_connections[session_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket disconnection"""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                # Clean up when last connection closes
                del self.active_connections[session_id]
                self.session_models.pop(session_id, None)
                self.chat_service.cleanup_session(session_id)

    async def broadcast_to_session(self, response: ChatResponse, session_id: str):
        """Send response to all connections in a session"""
        if session_id in self.active_connections:
            message_json = response.model_dump_json()
            for connection in self.active_connections[session_id]:
                await connection.send_text(message_json)

    def get_or_create_model(
        self, session_id: str, model_name: str
    ) -> RunnableWithMessageHistory:
        """Get or create model instance for session"""
        if session_id not in self.session_models:
            model = create_model(model_name)
            with_message_history = RunnableWithMessageHistory(
                model, lambda session_id: self.chat_service._chat_histories[session_id]
            )
            self.session_models[session_id] = with_message_history
        return self.session_models[session_id]


manager = ConnectionManager()


@websocket_router.websocket("/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Extract message details
            content = message_data["message"]
            model_name = message_data.get(
                "model", ChatAvailableModels.GEMINI_FLASH_1_5.value
            )

            # Create chat message
            chat_message = ChatMessage(
                content=content, role="human", session_id=session_id
            )

            # Check if we can accept the message
            if not await manager.chat_service.can_accept_message(session_id):
                error_response = ChatResponse(
                    message="Server is busy. Please try again in a moment.",
                    session_id=session_id,
                    metrics={"error": "backpressure_applied"},
                )
                await websocket.send_text(error_response.model_dump_json())
                continue

            # Queue the message
            if not await manager.chat_service.queue_message(chat_message):
                error_response = ChatResponse(
                    message="Message queue is full. Please try again later.",
                    session_id=session_id,
                    metrics={"error": "queue_full"},
                )
                await websocket.send_text(error_response.model_dump_json())
                continue

            # Ensure processing task is running
            model = manager.get_or_create_model(session_id, model_name)
            manager.chat_service.start_processing_task(
                session_id,
                model,
                lambda response: manager.broadcast_to_session(response, session_id),
            )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, session_id)
    except Exception as e:
        error_response = ChatResponse(
            message=f"Error: {str(e)}",
            session_id=session_id,
            metrics={"error": "general_error"},
        )
        await websocket.send_text(error_response.model_dump_json())
        await manager.disconnect(websocket, session_id)


@http_router.get("/metadata/available_models")
async def available_models():
    return ChatModelResponse(models=list(ChatAvailableModels))
