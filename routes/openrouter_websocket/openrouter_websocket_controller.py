from pathlib import Path
import tomllib
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

# Get the directory of the current script
current_dir = Path(__file__).parent
# Navigate up to the root project directory and find secrets.toml
secrets_path = current_dir.parent.parent / "secrets.toml"
assert secrets_path.exists(), f"Secrets file not found at {secrets_path}"
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

OPENROUTER_SECRET = secrets["OPENROUTER_SECRET"]
# Initialize services (you should load config from your settings)
config = OpenRouterConfigModel(
    api_key=OPENROUTER_SECRET,
)

openrouter_service = OpenRouterService(config)
state_service = WebSocketStateService()

@router.websocket("/openrouter")
async def openrouter_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for OpenRouter communication"""
    connection_id = str(uuid4())
    logger.info(f"New connection request: {connection_id}")
    
    try:
        # Initialize connection
        await websocket.accept()
        logger.info(f"Connection {connection_id}: Accepted")
        
        await openrouter_service.initialize()
        logger.info(f"Connection {connection_id}: Service initialized")

        # Main message processing loop
        while True:
            try:
                # Receive and log the raw message
                raw_message = await websocket.receive_text()
                logger.debug(f"Connection {connection_id}: Received raw message: {raw_message}")
                
                # Parse the message
                try:
                    data = json.loads(raw_message)
                    logger.info(f"Connection {connection_id}: Successfully parsed message")
                    logger.debug(f"Connection {connection_id}: Parsed data: {data}")
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON format: {str(e)}"
                    logger.error(f"Connection {connection_id}: {error_msg}")
                    await websocket.send_json({
                        "type": "error",
                        "message": error_msg
                    })
                    continue

                # Process the request and stream responses
                logger.info(f"Connection {connection_id}: Starting to process request")
                async for response in openrouter_service.process_request(data):
                    logger.debug(f"Connection {connection_id}: Sending response: {response}")
                    await websocket.send_json(response)
                logger.info(f"Connection {connection_id}: Finished processing request")

            except WebSocketDisconnect:
                logger.info(f"Connection {connection_id}: Client disconnected")
                break
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                logger.error(f"Connection {connection_id}: {error_msg}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": error_msg
                    })
                except Exception as send_error:
                    logger.error(f"Connection {connection_id}: Failed to send error message: {str(send_error)}")

    except Exception as e:
        logger.error(f"Connection {connection_id}: Fatal error: {str(e)}", exc_info=True)
    
    finally:
        # Clean up resources
        logger.info(f"Connection {connection_id}: Cleaning up resources")
        await openrouter_service.cleanup()
        logger.info(f"Connection {connection_id}: Connection closed")