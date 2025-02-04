import aiohttp
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from datetime import datetime
from .openrouter_models import (
    WebSocketStateModel
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OpenRouterService:
    """Service for handling OpenRouter API communication with SSE support"""
    def __init__(self, config):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self.request_id = 0

    async def initialize(self):
        """Initialize the aiohttp session"""
        if not self._session:
            self._session = aiohttp.ClientSession()
            logger.info("Initialized new aiohttp session")

    async def cleanup(self):
        """Clean up resources"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Cleaned up aiohttp session")

    def _get_headers(self) -> Dict[str, str]:
        """Generate headers for OpenRouter API calls"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",  # Explicitly request SSE format
        }
        if self.config.site_url:
            headers["HTTP-Referer"] = self.config.site_url
        if self.config.site_name:
            headers["X-Title"] = self.config.site_name
        
        safe_headers = headers.copy()
        safe_headers["Authorization"] = "Bearer [REDACTED]"
        logger.debug(f"Generated headers: {safe_headers}")
        return headers

    def _parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a Server-Sent Events (SSE) line and extract the data"""
        # Handle empty lines
        if not line.strip():
            logger.debug("Skipping empty line")
            return None

        # Handle processing messages
        if line.startswith(": "):
            processing_msg = line[2:].strip()
            logger.debug(f"Processing message: {processing_msg}")
            return {
                "type": "processing",
                "message": processing_msg
            }

        # Handle data messages
        if line.startswith("data: "):
            data_str = line[6:].strip()  # Remove 'data: ' prefix
            
            # Handle stream completion
            if data_str == "[DONE]":
                logger.debug("Stream completed")
                return {
                    "type": "done"
                }
            
            # Parse JSON data
            try:
                data = json.loads(data_str)
                logger.debug(f"Parsed JSON data: {data}")
                return {
                    "type": "completion",
                    "data": data
                }
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON data: {e}")
                logger.error(f"Problematic data: {data_str}")
                return {
                    "type": "error",
                    "message": f"Error parsing response: {str(e)}"
                }

        # Handle unknown message format
        logger.warning(f"Unknown message format: {line}")
        return None

    async def process_request(
        self,
        request: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a request to OpenRouter and yield response chunks"""
        if not self._session:
            error_msg = "Service not initialized"
            logger.error(error_msg)
            yield {"type": "error", "message": error_msg}
            return

        self.request_id += 1
        current_request_id = self.request_id

        try:
            logger.info(f"Request {current_request_id}: Starting OpenRouter API call")
            logger.debug(f"Request {current_request_id} payload: {request}")

            payload = request.copy()
            payload["stream"] = True  # Ensure streaming is enabled

            async with self._session.post(
                self.config.api_url,
                headers=self._get_headers(),
                json=payload
            ) as response:
                logger.info(f"Request {current_request_id}: Got response with status {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Request {current_request_id}: API error: {error_text}")
                    yield {
                        "type": "error",
                        "message": f"OpenRouter API error: {error_text}"
                    }
                    return

                # Initialize accumulator for the response and metadata storage
                full_response = ""
                final_metadata = {}

                logger.info(f"Request {current_request_id}: Starting to process stream")
                async for line in response.content:
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')

                    logger.debug(f"Request {current_request_id}: Raw line: {line}")

                    parsed = self._parse_sse_line(line)
                    if parsed:
                        if parsed["type"] == "completion":
                            # Accumulate the content and metadata
                            delta_content = parsed["data"]["choices"][0]["delta"].get("content", "")
                            full_response += delta_content
                            final_metadata = parsed["data"] #Keep latest metadata in case of updates.

                            # Check for finish reason
                            finish_reason = parsed["data"]["choices"][0].get("finish_reason")
                            if finish_reason:
                                # Send the complete response
                                yield {
                                    "type": "completion",
                                    "data": {
                                        "full_response": full_response,
                                        "meta": final_metadata,
                                    }
                                }
                                full_response = ""  # Reset for next potential request
                                final_metadata = {} # Reset metadata
                        elif parsed["type"] == "processing":
                            yield parsed #Pass through processing messages.
                        elif parsed["type"] == "error":
                            yield parsed # Pass through error messages.
                        elif parsed["type"] == "done":
                            yield parsed # Pass through done messages; this is the final message.
                        else:
                            logger.warning(f"Unexpected response type: {parsed['type']}")


                logger.info(f"Request {current_request_id}: Finished processing stream")

        except Exception as e:
            logger.error(f"Request {current_request_id}: Fatal error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "message": f"Internal error: {str(e)}"
            }

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