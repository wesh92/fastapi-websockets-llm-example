# FastAPI AI Chat Template

A robust FastAPI-based WebSocket and HTTP server template that integrates with OpenRouter's API for real-time AI model interactions. This project provides a production-ready foundation for building chat applications powered by various AI models through OpenRouter's unified API interface.

## Features

This template includes a comprehensive set of features designed for building production-ready AI chat applications:

- Real-time WebSocket communication with AI models through OpenRouter
- Support for multiple chat models including Gemini, Qwen, and other leading options
- Message history persistence using SQLite
- Rate limiting and backpressure handling for reliable performance
- Robust error handling and logging
- Docker containerization with optimized uv package management
- Health check endpoints
- Structured API documentation
- Authentication support
- Configurable routing system
- State management for WebSocket connections

## Prerequisites

Before getting started, ensure you have:

- Python 3.13 or higher
- Docker and Docker Compose (for containerized deployment)
- OpenRouter API key (stored in secrets.toml)

## Dependencies

The project relies on several key dependencies for its functionality:

- FastAPI (>= 0.115.6) - Modern web framework for building APIs
- LangChain (>= 0.3.17) - Framework for working with language models
- aiohttp (>= 3.11.11) - Async HTTP client/server framework
- uvicorn (>= 0.34.0) - Lightning-fast ASGI server
- pydantic (>= 2.10.4) - Data validation using Python type annotations
- gunicorn (>= 23.0.0) - Production-grade WSGI HTTP server
- JWT authentication libraries:
  - PyJWT[crypto] (>= 2.10.1)
  - passlib (>= 1.7.4)
  - bcrypt (>= 4.2.1)

## Project Structure

The project follows a clear and modular structure:

```
├── routes/
│   ├── chat/
│   │   ├── chat_models.py           # Pydantic models for chat functionality
│   │   ├── chat_service.py          # Core chat service implementation
│   │   └── chat_controller.py       # WebSocket and HTTP endpoints
├── internal/
│   ├── auth/                        # Authentication components
│   ├── health/                      # Health check endpoints
│   └── dependencies/                # Shared dependencies
├── documentation/                   # API documentation
├── Dockerfile                      # Main docker entrypoint for the python app
├── docker-compose.yml              # Docker Compose configuration
├── main.py                        # Application entry point
└── pyproject.toml                 # Project metadata and dependencies
```

## Configuration

### Environment Setup

1. Create a `secrets.toml` file in the project root:
```toml
SECRET_KEY = "your-openssl-rand-hex-32-key"
OPENROUTER_SECRET = "your-openrouter-api-key"
```

### Docker Configuration

The provided Docker setup includes several optimizations:

- Uses Python 3.13 slim-bookworm base image
- Implements uv for faster package management
- Configures health checks and automatic restarts
- Sets up volume mounting for development
- Creates a named network for service communication

## Usage

### Starting the Server

Using Docker (recommended for production):
```bash
docker-compose up -d
```

Using Python directly (development):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### WebSocket Connection

Connect to the WebSocket endpoint at:
```
ws://localhost:8000/websockets/chat/{session_id}
```

The session_id parameter allows for maintaining separate chat sessions with persistent history.

### Message Format

Messages to the WebSocket should follow this format (model is optional, defaults to gemini-flash-1.5):
```json
{
    "message": "Write a simple python script to add 3 numbers.",
    "model": "google/gemini-flash-1.5"
}
```

Available models can be queried through the HTTP endpoint:
```
GET http://localhost:8000/chat/metadata/available_models
```

## API Documentation

Access the interactive API documentation at:
```
http://localhost:8000/docs
```

## Chat Service Architecture

The chat service implements several important features:

- Message queuing with backpressure control
- Rate limiting using a token bucket algorithm
- Persistent message history using SQLite
- Support for multiple simultaneous chat sessions
- Real-time streaming of AI responses

## Error Handling

The system provides comprehensive error handling across multiple layers:

- WebSocket connection management
- Message rate limiting and queuing
- API communication errors
- Database operations
- Service initialization

All errors are logged with appropriate detail levels and returned to the client with clear error messages.

## Health Monitoring

A health check endpoint is available at:
```
http://localhost:8000/health
```

The Docker container includes automated health checking every 90 seconds to ensure system stability.

## Development

### Adding New Routes

1. Create a new module in the `routes` directory
2. Define your router using FastAPI's `APIRouter`
3. Add the router configuration in `main.py`
4. Update the OpenAPI documentation as needed

### Code Style

The project uses ruff for code formatting and linting, with configuration provided in `pyproject.toml`. The uv package manager is recommended for dependency management and virtual environment handling.

## Security Considerations

- API keys are stored in `secrets.toml` (not version controlled)
- WebSocket connections include state tracking and rate limiting
- Authentication middleware available for protected routes
- SQLite database for persistent storage with proper connection management
- Headers are sanitized in logs