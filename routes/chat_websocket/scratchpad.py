from pathlib import Path
import tomllib
import sqlite3
from typing import List
from langchain_openai import ChatOpenAI as OpenAIChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
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

# Example usage
if __name__ == "__main__":
    config = {"configurable": {"session_id": "abc3"}}

    # Test message persistence
    response = with_message_history.invoke(
        [HumanMessage(content="Hi! I'm Bob")],
        config=config,
    )

    # Test message retrieval
    for r in with_message_history.stream(
        [HumanMessage(content="What's my name?")],
        config=config,
    ):
        print(r.content, end="|")