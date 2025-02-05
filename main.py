# main.py
# ruff: noqa: F401
import logging
from typing import List, Tuple
from fastapi import FastAPI, APIRouter
from fastapi.logger import logger
from fastapi.openapi.docs import get_swagger_ui_html

from documentation.docs import API_DOCS_METADATA
from internal.dependencies.default_responses import DEFAULT_RESPONSES

from internal.auth.auth_controller import router as auth_router
from internal.health.healthcheck import router as healthcheck_router
from routes.weather.weather_controller import (
    ENDPOINT_ACTIVE as WEATHER_ENDPOINT_ACTIVE,
    router as weather_router,
)
from routes.chat_websocket.chat_controller import router as chat_websocket_router

def configure_router(router: APIRouter, responses: dict) -> APIRouter:
    """
    Configure an APIRouter with default responses and other settings.

    Args:
        router: The APIRouter to configure
        responses: Dictionary of default responses to apply

    Returns:
        APIRouter: The configured router
    """
    # Create a new router with the defaults
    configured_router = APIRouter(
        responses=responses,  # Set default responses here
    )

    # Copy all routes and other attributes from the original router
    configured_router.routes = router.routes
    configured_router.dependencies = router.dependencies

    return configured_router


def setup_routers(app: FastAPI) -> None:
    """
    Configure and include all API routers with their default responses.
    """
    # Define your router configurations
    router_configs: List[Tuple[APIRouter, str, List[str]]] = [
        (auth_router, "/auth", ["auth"]),
        # Add more routers as needed:
        # (users_router, "/users", ["users"]),
        (weather_router, "/weather", ["weather"]) if WEATHER_ENDPOINT_ACTIVE else ...,
        (healthcheck_router, "/health", ["health"]),
        (chat_websocket_router, "/websockets", ["websockets"]),]

    for router, prefix, tags in router_configs:
        try:
            # Configure the router with default responses
            configured_router = configure_router(router, DEFAULT_RESPONSES)

            # Include the configured router in the app
            app.include_router(
                configured_router,
                prefix=prefix,
                tags=tags,
            )
            logger.info(f"Successfully configured router for prefix: {prefix}")

        except Exception as e:
            error_msg = f"Failed to configure router for prefix {prefix}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application with all its routers and settings.
    """
    # Initialize FastAPI with custom documentation settings
    app = FastAPI(**API_DOCS_METADATA, docs_url=None, redoc_url=None)

    try:
        setup_routers(app)
        logger.info("Successfully configured all routers")
    except Exception as e:
        error_msg = f"Failed to configure application: {e}"
        logger.error(error_msg)
        exit(1)

    return app


# Create the application instance
app = create_application()


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> str:
    """
    Serve custom Swagger UI documentation.
    """
    ui_html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Your New API",
    )
    if ui_html:
        logger.info("Successfully generated /docs")
        return ui_html

    logger.error("Failed to generate /docs")
    raise RuntimeError("Failed to generate /docs")
