from datetime import datetime
from typing import Deque
import time
from logging import log, INFO
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from .chat_models import ChatMessage, ChatResponse


import sqlite3
from typing import List
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from collections import deque
import asyncio

class RateLimiter:
    """Implements token bucket algorithm for rate limiting"""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire a token"""
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + time_passed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

class MessageQueue:
    """Manages message queuing with backpressure"""
    def __init__(self, maxsize: int = 100):
        self.queue: Deque[ChatMessage] = deque(maxlen=maxsize)
        self.lock = asyncio.Lock()
    
    async def put(self, message: ChatMessage) -> bool:
        """Try to add message to queue"""
        async with self.lock:
            if len(self.queue) < self.queue.maxlen:
                self.queue.append(message)
                return True
            return False
    
    async def get(self) -> ChatMessage:
        """Get next message from queue"""
        async with self.lock:
            return self.queue.popleft() if self.queue else None

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
        self._message_queues: dict[str, MessageQueue] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._processing_tasks: dict[str, asyncio.Task] = {}

    def initialize_session(self, session_id: str):
        """Initialize resources for a new session"""
        if session_id not in self._message_queues:
            self._message_queues[session_id] = MessageQueue(maxsize=100)
            self._rate_limiters[session_id] = RateLimiter(rate=2.0, capacity=5)
            self._chat_histories[session_id] = SQLiteChatMessageHistory(session_id)

    def cleanup_session(self, session_id: str):
        """Clean up resources for a closed session"""
        self._message_queues.pop(session_id, None)
        self._rate_limiters.pop(session_id, None)
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
            self._processing_tasks.pop(session_id, None)

    async def can_accept_message(self, session_id: str) -> bool:
        """Check if a new message can be accepted"""
        rate_limiter = self._rate_limiters.get(session_id)
        return rate_limiter and await rate_limiter.acquire()

    async def queue_message(self, message: ChatMessage) -> bool:
        """Queue a message for processing"""
        queue = self._message_queues.get(message.session_id)
        return queue and await queue.put(message)

    async def process_queued_messages(self, session_id: str, 
                                    model: RunnableWithMessageHistory,
                                    callback) -> None:
        """Process messages in the queue for a session"""
        try:
            while True:
                queue = self._message_queues.get(session_id)
                if not queue:
                    break
                    
                message = await queue.get()
                if message:
                    config = {"configurable": {"session_id": session_id}}


                    human_message = HumanMessage(content=message.content)
                    

                    async for response in model.astream(
                        [human_message],
                        config=config,
                    ):
                        await callback(ChatResponse(
                            message=response.content,
                            session_id=session_id,
                            metrics={
                                "processing_time_ms": round(
                                    (time.time() - message.timestamp.timestamp()) * 1000, 
                                    2
                                ),
                                "timestamp": datetime.now().isoformat()
                            }
                        ))
                
                await asyncio.sleep(0.1)  # Prevent CPU spinning
                
        except asyncio.CancelledError:
            # Clean handling of task cancellation
            pass
        except Exception as e:
            # Notify callback of error
            await callback(ChatResponse(
                message=f"Error in message processing: {str(e)}",
                session_id=session_id,
                metrics={"error": "queue_processing_error"}
            ))

    def start_processing_task(self, session_id: str, 
                            model: RunnableWithMessageHistory,
                            callback) -> None:
        """Start background task for processing messages"""
        if session_id not in self._processing_tasks:
            self._processing_tasks[session_id] = asyncio.create_task(
                self.process_queued_messages(session_id, model, callback)
            )