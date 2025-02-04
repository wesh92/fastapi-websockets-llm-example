API_VERSION = "0.1.5"
FEATURE_OR_CODENAME = "Basic Setup"


# Top level description of the API
API_DESCRIPTION = """
Top-level API Description
"""

# NOTE: This dict is what should be provided
# to the FastAPI() constructor in order to
# have nice swagger docs
# Add any additional metadata here
API_DOCS_METADATA = {
    "description": API_DESCRIPTION,
    "title": "api-template-1",  # TODO: Change this to the name of your API
    "version": f"{API_VERSION} - {FEATURE_OR_CODENAME}",
    "openapi_tags": [
        {
            "name": "auth",
            "description": "Authentication and Authorization",
        },
        {
            "name": "weather",
            "description": "Weather Data",
        },
        {
            "name": "health",
            "description": "Health Check",
        },
        {
            "name": "websockets",
            "description": "Websockets",
        },
    ],
}
