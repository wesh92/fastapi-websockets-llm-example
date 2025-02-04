# FastAPI WebSocket OpenRouter Template

A robust FastAPI-based WebSocket server template that integrates with OpenRouter's API for real-time AI model interactions. This project provides a production-ready foundation for building WebSocket-based applications that require AI model integration.

## Features

This template includes:

- Real-time WebSocket communication with AI models through OpenRouter
- Robust error handling and logging
- Docker containerization
- Health check endpoints
- Structured API documentation
- Authentication support
- Configurable routing system
- State management for WebSocket connections

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- OpenRouter API key (stored in secrets.toml)

## Dependencies

Core dependencies include:

- FastAPI (>= 0.115.6) - Web framework for building APIs
- aiohttp (>= 3.11.11) - Async HTTP client/server framework
- uvicorn (>= 0.34.0) - ASGI server implementation
- pydantic (>= 2.10.4) - Data validation using Python type annotations
- gunicorn (>= 23.0.0) - WSGI HTTP server
- python-multipart (>= 0.0.20) - Streaming multipart parser
- JWT authentication libraries:
  - PyJWT[crypto] (>= 2.10.1)
  - passlib (>= 1.7.4)
  - bcrypt (>= 4.2.1)

## Project Structure

```
├── routes/
│   ├── openrouter_websocket/
│   │   ├── openrouter_models.py      # Pydantic models for OpenRouter
│   │   ├── openrouter_service.py     # OpenRouter API communication service
│   │   └── openrouter_websocket_controller.py  # WebSocket endpoint controller
├── internal/
│   ├── auth/                         # Authentication components
│   ├── health/                       # Health check endpoints
│   └── dependencies/                 # Shared dependencies
├── documentation/                    # API documentation
├── docker-compose.yml               # Docker Compose configuration
├── main.py                         # Application entry point
└── pyproject.toml                  # Project metadata and dependencies
```

## Configuration

### Environment Setup

1. Create a `secrets.toml` file in the project root:
```toml
OPENROUTER_SECRET = "your-openrouter-api-key"
```

### Docker Configuration

The included `docker-compose.yml` provides:
- Port mapping (8000:8000)
- Volume mounting for development
- Health check configuration
- Automatic container restart
- Named network for service communication

## Usage

### Starting the Server

Using Docker:
```bash
docker-compose up -d
```

Using Python directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### WebSocket Connection

Connect to the WebSocket endpoint at:
```
ws://localhost:8000/websockets/openrouter
```

### Message Format

Messages to the WebSocket should follow this format:
```json
{
    "messages": [
        {
            "role": "user",
            "content": "Your message here"
        }
    ],
    "model": "google/gemini-flash-1.5",
    "temperature": 1.0
}
```

## API Documentation

Access the API documentation at:
```
http://localhost:8000/docs
```

## Error Handling

The system includes comprehensive error handling:
- WebSocket connection management
- API communication errors
- Message parsing errors
- Service initialization failures

All errors are logged with appropriate detail levels and returned to the client with clear error messages.

## Health Monitoring

Health checks are available at:
```
http://localhost:8000/health
```

The Docker container includes automated health checking every 90 seconds.

## Development

### Adding New Routes

1. Create a new module in the `routes` directory
2. Define your router using FastAPI's `APIRouter`
3. Add the router configuration in `main.py`
4. Update the OpenAPI documentation as needed

### Code Style

The project uses ruff for code formatting and linting. Configuration is provided in `pyproject.toml`.

## Security Considerations

- API keys are stored in `secrets.toml` (not version controlled). You should probably use GH Secrets or some other provider.
- WebSocket connections include state tracking
- Authentication middleware available for protected routes
- Headers are sanitized in logs