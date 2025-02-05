from pathlib import Path
import tomllib
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
from .chat_models import ChatMessage
from .chat_service import ChatService, SQLiteChatMessageHistory
from langchain_openai import ChatOpenAI as OpenAIChatModel
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

router = APIRouter()
chat_service = ChatService()

# Get the directory of the current script
current_dir = Path(__file__).parent
# Navigate up to the root project directory and find secrets.toml
secrets_path = current_dir.parent.parent / "secrets.toml"
assert secrets_path.exists(), f"Secrets file not found at {secrets_path}"
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

OPENROUTER_SECRET = secrets["OPENROUTER_SECRET"]

model = OpenAIChatModel(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_SECRET,
    model="google/gemini-flash-1.5",
    temperature=0.7,
    max_tokens=1000,
    streaming=True,
)

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return SQLiteChatMessageHistory(session_id)

with_message_history = RunnableWithMessageHistory(model, get_session_history)

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

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

    async def broadcast_to_session(self, message: str, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Parse the incoming message
            chat_message = ChatMessage(
                content=json.loads(data)["message"],
                role="human",
                session_id=session_id
            )
            
            # Process the message and stream responses
            async for response in chat_service.process_message(chat_message, with_message_history):
                await manager.broadcast_to_session(
                    response.model_dump_json(),
                    session_id
                )
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, session_id)
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        await manager.disconnect(websocket, session_id)