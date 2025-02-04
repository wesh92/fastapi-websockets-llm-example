from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
from uuid import uuid4
from .openrouter_models import (
    OpenRouterRequestModel,
    OpenRouterErrorResponse,
    OpenRouterConfigModel,
)
from .openrouter_service import OpenRouterService, WebSocketStateService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (you should load config from your settings)
config = OpenRouterConfigModel(
    api_key="your_api_key_here",
    site_url="your_site_url",
    site_name="your_site_name"
)

openrouter_service = OpenRouterService(config)
state_service = WebSocketStateService()

@router.websocket("/openrouter")
async def openrouter_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for OpenRouter communication"""
    connection_id = str(uuid4())
    
    try:
        # Initialize connection
        await websocket.accept()
        await openrouter_service.initialize()
        state_service.create_connection(connection_id)

        # Main message processing loop
        while True:
            try:
                # Receive and validate message
                message = await websocket.receive_text()
                state_service.update_activity(connection_id)
                
                # Parse and validate the request
                try:
                    data = json.loads(message)
                    request = OpenRouterRequestModel(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    await websocket.send_json(
                        OpenRouterErrorResponse(
                            type="error",
                            message="Invalid request format",
                            code="VALIDATION_ERROR"
                        ).model_dump()
                    )
                    continue

                # Process the request and stream responses
                async for response in openrouter_service.process_request(request):
                    await websocket.send_json(response.model_dump())

            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json(
                    OpenRouterErrorResponse(
                        type="error",
                        message=f"Error processing message: {str(e)}",
                        code="PROCESSING_ERROR"
                    ).model_dump()
                )

    finally:
        # Clean up resources
        state_service.remove_connection(connection_id)
        await openrouter_service.cleanup()