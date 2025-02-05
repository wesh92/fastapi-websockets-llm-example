from pathlib import Path
import tomllib
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Set
import json
from .chat_models import ChatAvailableModels, ChatMessage, ChatModelResponse, ChatResponse
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
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                # Clean up the model when the last connection is closed
                self.session_models.pop(session_id, None)

    async def broadcast_to_session(self, message: str, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_text(message)

    def get_or_create_model(self, session_id: str, model_name: str) -> RunnableWithMessageHistory:
        """
        Get an existing model for the session or create a new one.
        
        Args:
            session_id: The session identifier
            model_name: The name of the model to use
            
        Returns:
            RunnableWithMessageHistory: The configured model instance
        """
        if session_id not in self.session_models:
            model = create_model(model_name)
            with_message_history = RunnableWithMessageHistory(model, get_session_history)
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
            
            # Extract message and optional model name
            content = message_data["message"]
            model_name = message_data.get("model", ChatAvailableModels.GEMINI_FLASH_1_5.value)
            
            try:
                # Create or get the model for this session
                model = manager.get_or_create_model(session_id, model_name)
                
                # Process the message
                chat_message = ChatMessage(
                    content=content,
                    role="human",
                    session_id=session_id
                )
                
                # Process the message and stream responses
                async for response in manager.chat_service.process_message(chat_message, model):
                    await manager.broadcast_to_session(
                        response.model_dump_json(),
                        session_id
                    )
                    
            except ValueError as e:
                # Handle invalid model selection
                error_response = ChatResponse(
                    message=f"Error: {str(e)}",
                    session_id=session_id,
                    metrics={"error": "invalid_model"}
                )
                await manager.broadcast_to_session(
                    error_response.model_dump_json(),
                    session_id
                )
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, session_id)
    except Exception as e:
        error_response = ChatResponse(
            message=f"Error: {str(e)}",
            session_id=session_id,
            metrics={"error": "general_error"}
        )
        await websocket.send_text(error_response.model_dump_json())
        await manager.disconnect(websocket, session_id)

@http_router.get("/metadata/available_models")
async def available_models():
    return ChatModelResponse(models=list(ChatAvailableModels))