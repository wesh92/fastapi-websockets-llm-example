from pathlib import Path
import aiohttp
import json
import logging
from typing import AsyncGenerator, Dict, Optional
from datetime import datetime
from .openrouter_models import (
    OpenRouterRequestModel,
    OpenRouterResponseChunk,
    OpenRouterErrorResponse,
    OpenRouterConfigModel,
    WebSocketStateModel
)
import tomllib

# Get the directory of the current script
current_dir = Path(__file__).parent
# Navigate up to the root project directory and find secrets.toml
secrets_path = current_dir.parent.parent / "secrets.toml"
assert secrets_path.exists(), f"Secrets file not found at {secrets_path}"
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

logger = logging.getLogger(__name__)

class OpenRouterService:
    """Service for handling OpenRouter API communication"""
    def __init__(self, config: OpenRouterConfigModel):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize the aiohttp session"""
        if not self._session:
            self._session = aiohttp.ClientSession()

    async def cleanup(self):
        """Clean up resources"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_headers(self) -> Dict[str, str]:
        """Generate headers for OpenRouter API calls"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.site_url:
            headers["HTTP-Referer"] = self.config.site_url
        if self.config.site_name:
            headers["X-Title"] = self.config.site_name
        return headers

    async def process_request(
        self,
        request: OpenRouterRequestModel
    ) -> AsyncGenerator[OpenRouterResponseChunk | OpenRouterErrorResponse, None]:
        """Process a request to OpenRouter and yield response chunks"""
        if not self._session:
            yield OpenRouterErrorResponse(
                type="error",
                message="Service not initialized",
                code="SERVICE_ERROR"
            )
            return

        try:
            payload = request.model_dump()
            payload["stream"] = True  # Ensure streaming is enabled

            async with self._session.post(
                self.config.api_url,
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield OpenRouterErrorResponse(
                        type="error",
                        message=f"OpenRouter API error: {error_text}",
                        code="API_ERROR"
                    )
                    return

                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            yield OpenRouterResponseChunk(
                                type="completion",
                                data=data
                            )
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding response: {e}")
                            yield OpenRouterErrorResponse(
                                type="error",
                                message="Error decoding response",
                                code="DECODE_ERROR"
                            )

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            yield OpenRouterErrorResponse(
                type="error",
                message=f"Internal error: {str(e)}",
                code="INTERNAL_ERROR"
            )

class WebSocketStateService:
    """Service for managing WebSocket connection states"""
    def __init__(self):
        self.connections: Dict[str, WebSocketStateModel] = {}

    def create_connection(self, connection_id: str) -> WebSocketStateModel:
        """Create and store a new connection state"""
        now = datetime.now()
        state = WebSocketStateModel(
            connection_id=connection_id,
            connected_at=now,
            last_activity=now
        )
        self.connections[connection_id] = state
        return state

    def update_activity(self, connection_id: str):
        """Update the last activity timestamp for a connection"""
        if connection_id in self.connections:
            self.connections[connection_id].last_activity = datetime.now()
            self.connections[connection_id].total_messages += 1

    def remove_connection(self, connection_id: str):
        """Remove a connection state"""
        if connection_id in self.connections:
            del self.connections[connection_id]