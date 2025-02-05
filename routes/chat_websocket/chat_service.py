from datetime import datetime
from typing import AsyncGenerator
import time
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from .chat_models import ChatMessage, ChatResponse

import sqlite3
from typing import List
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

class SQLiteChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, db_path: str = "chat_history.db"):
        self.session_id = session_id
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (self.session_id, message.type, message.content)
            )

    def clear(self) -> None:
        """Clear session messages from the store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (self.session_id,)
            )

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at",
                (self.session_id,)
            )
            messages = []
            for role, content in cursor:
                if role == "human":
                    messages.append(HumanMessage(content=content))
                elif role == "ai":
                    messages.append(AIMessage(content=content))
            return messages

class ChatService:
    def __init__(self):
        self._chat_histories = {}

    async def process_message(self, message: ChatMessage, with_message_history: RunnableWithMessageHistory) -> AsyncGenerator[ChatResponse, None]:
        start_time = time.time()
        
        # Get or create chat history for this session
        if message.session_id not in self._chat_histories:
            self._chat_histories[message.session_id] = SQLiteChatMessageHistory(message.session_id)
        
        # Prepare the configuration for message history
        config = {"configurable": {"session_id": message.session_id}}
        
        # Create the message and stream the response
        human_message = HumanMessage(content=message.content)
        
        async for chunk in with_message_history.astream(
            [human_message],
            config=config,
        ):
            processing_time = time.time() - start_time
            yield ChatResponse(
                message=chunk.content,
                session_id=message.session_id,
                metrics={
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "timestamp": datetime.now().isoformat()
                }
            )