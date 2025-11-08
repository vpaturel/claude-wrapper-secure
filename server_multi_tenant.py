#!/usr/bin/env python3
"""
FastAPI Server - Claude Multi-Tenant API

Production-ready server pour hébergement Cloud Run.

Usage:
    python3 server_multi_tenant.py

    # Production
    uvicorn server_multi_tenant:app --host 0.0.0.0 --port 8080 --workers 4
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import logging
import time
from claude_oauth_api_multi_tenant import (
    MultiTenantClaudeAPI,
    MCPServerConfig
)

# =============================================================================
# Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("claude_multi_tenant")

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Claude Multi-Tenant API",
    version="3.0",
    description="Production-ready multi-tenant Claude OAuth API with MCP support",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (ajuster selon tes besoins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: spécifier domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API instance globale
api = MultiTenantClaudeAPI()

# =============================================================================
# Models
# =============================================================================

class Message(BaseModel):
    """Message format"""
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")


class MessageRequest(BaseModel):
    """Request format compatible OpenAI/Anthropic"""
    messages: List[Message]
    model: str = Field("sonnet", description="opus, sonnet, or haiku")
    session_id: Optional[str] = Field(None, description="Session ID for context persistence")
    stream: bool = Field(False, description="Enable streaming (SSE)")
    max_tokens: Optional[int] = Field(4096, description="Max tokens (not enforced)")
    temperature: Optional[float] = Field(1.0, description="Temperature (not enforced)")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "model": "sonnet",
                "session_id": "user1-conv-123"
            }
        }


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    alias: str
    description: str


class ErrorResponse(BaseModel):
    """Error response format"""
    error: Dict[str, str]
    type: str = "error"


# =============================================================================
# Middleware
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log toutes les requêtes"""
    start_time = time.time()

    # Log request
    logger.info(json.dumps({
        "event": "request_start",
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown"
    }))

    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(json.dumps({
        "event": "request_end",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    }))

    return response


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API info"""
    return {
        "name": "Claude Multi-Tenant API",
        "version": "3.0",
        "status": "healthy",
        "features": [
            "Multi-tenant OAuth",
            "Custom MCP servers per request",
            "Session persistence",
            "Streaming support"
        ],
        "endpoints": {
            "messages": "POST /v1/messages",
            "models": "GET /v1/models",
            "mcp_tools": "GET /v1/mcp/tools",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.post(
    "/v1/messages",
    tags=["Messages"],
    response_model=None,  # Dynamic response
    responses={
        200: {"description": "Success"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def create_message(
    request: MessageRequest,
    authorization: str = Header(
        ...,
        description="OAuth token: Bearer sk-ant-oat01-xxx",
        example="Bearer sk-ant-oat01-your-token-here"
    ),
    x_mcp_config: Optional[str] = Header(
        None,
        description='MCP servers config JSON: {"server": {"command": "...", "args": [...]}}',
        example='{"memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]}}'
    ),
    x_session_id: Optional[str] = Header(
        None,
        description="Session ID for conversation persistence",
        example="user1-conv-123"
    )
):
    """
    Create message with multi-tenant support.

    **Authentication:**
    - Header `Authorization`: `Bearer sk-ant-oat01-<your_oauth_token>`

    **MCP Servers (optional):**
    - Header `X-MCP-Config`: JSON config for custom MCP servers

    **Session Management (optional):**
    - Header `X-Session-ID`: Session ID to persist conversation context

    **Example:**
    ```bash
    curl -X POST https://your-api.run.app/v1/messages \\
      -H "Authorization: Bearer sk-ant-oat01-xxx" \\
      -H "X-MCP-Config: {\\"memory\\": {\\"command\\": \\"npx\\", \\"args\\": [\\"-y\\", \\"@modelcontextprotocol/server-memory\\"]}}" \\
      -H "X-Session-ID: user1-conv-123" \\
      -H "Content-Type: application/json" \\
      -d '{
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "sonnet"
      }'
    ```
    """

    # Validate OAuth token
    if not authorization.startswith("Bearer sk-ant-oat01-"):
        logger.warning(json.dumps({
            "event": "auth_failed",
            "reason": "invalid_token_format",
            "token_prefix": authorization[:20] if authorization else "none"
        }))
        raise HTTPException(
            status_code=401,
            detail="Invalid OAuth token. Expected: Bearer sk-ant-oat01-xxx"
        )

    oauth_token = authorization.replace("Bearer ", "")

    # Parse MCP config
    mcp_servers = None
    if x_mcp_config:
        try:
            mcp_data = json.loads(x_mcp_config)
            mcp_servers = {
                name: MCPServerConfig(**config)
                for name, config in mcp_data.items()
            }
            logger.info(json.dumps({
                "event": "mcp_config_loaded",
                "servers": list(mcp_servers.keys())
            }))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid X-MCP-Config JSON: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MCP config format: {str(e)}"
            )

    # Session ID (header > body)
    session_id = x_session_id or request.session_id

    # Log request
    logger.info(json.dumps({
        "event": "message_request",
        "model": request.model,
        "session_id": session_id,
        "mcp_enabled": mcp_servers is not None,
        "stream": request.stream,
        "messages_count": len(request.messages)
    }))

    # Create message
    try:
        response = api.create_message(
            oauth_token=oauth_token,
            messages=[msg.dict() for msg in request.messages],
            session_id=session_id,
            mcp_servers=mcp_servers,
            model=request.model,
            stream=request.stream,
            skip_mcp_permissions=True
        )

        # Log response
        logger.info(json.dumps({
            "event": "message_response",
            "status": "success" if response.get("type") != "error" else "error",
            "response_type": response.get("type")
        }))

        return response

    except subprocess.TimeoutExpired:
        logger.error(json.dumps({
            "event": "timeout",
            "session_id": session_id
        }))
        raise HTTPException(
            status_code=504,
            detail="Request timeout (>180s). Try simpler prompt or increase timeout."
        )

    except Exception as e:
        logger.error(json.dumps({
            "event": "error",
            "error": str(e),
            "session_id": session_id
        }))
        raise HTTPException(
            status_code=500,
            detail=f"Claude API error: {str(e)}"
        )


@app.get("/v1/models", tags=["Models"])
async def list_models():
    """
    List available Claude models.

    Returns model IDs and aliases.
    """
    return {
        "data": [
            {
                "id": "claude-opus-4-20250514",
                "alias": "opus",
                "description": "Most capable model, best for complex tasks"
            },
            {
                "id": "claude-sonnet-4-5-20250929",
                "alias": "sonnet",
                "description": "Balanced model, best for general use (recommended)"
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "alias": "haiku",
                "description": "Fastest model, best for simple tasks"
            }
        ]
    }


@app.get("/v1/mcp/tools", tags=["MCP"])
async def list_mcp_tools(
    authorization: str = Header(..., description="OAuth token"),
    x_mcp_config: Optional[str] = Header(None, description="Custom MCP config")
):
    """
    List all MCP tools available for authenticated user.

    **Headers:**
    - `Authorization`: Bearer sk-ant-oat01-xxx
    - `X-MCP-Config`: Optional custom MCP servers config

    **Example:**
    ```bash
    curl https://your-api.run.app/v1/mcp/tools \\
      -H "Authorization: Bearer sk-ant-oat01-xxx" \\
      -H "X-MCP-Config: {\\"custom\\": {\\"command\\": \\"npx\\", \\"args\\": [\\"-y\\", \\"@modelcontextprotocol/server-memory\\"]}}"
    ```
    """

    # Validate token
    if not authorization.startswith("Bearer sk-ant-oat01-"):
        raise HTTPException(401, "Invalid OAuth token")

    oauth_token = authorization.replace("Bearer ", "")

    # Parse MCP
    mcp_servers = None
    if x_mcp_config:
        try:
            mcp_data = json.loads(x_mcp_config)
            mcp_servers = {
                name: MCPServerConfig(**config)
                for name, config in mcp_data.items()
            }
        except Exception as e:
            raise HTTPException(400, f"Invalid MCP config: {str(e)}")

    # List tools
    try:
        tools = api.list_mcp_tools(
            oauth_token=oauth_token,
            mcp_servers=mcp_servers
        )

        logger.info(json.dumps({
            "event": "mcp_tools_listed",
            "count": len(tools)
        }))

        return {
            "tools": tools,
            "count": len(tools),
            "mcp_servers": list(mcp_servers.keys()) if mcp_servers else []
        }

    except Exception as e:
        logger.error(json.dumps({
            "event": "mcp_tools_error",
            "error": str(e)
        }))
        raise HTTPException(500, f"Error listing MCP tools: {str(e)}")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for Cloud Run / Kubernetes.

    Returns:
        - status: "healthy" if API is operational
        - version: API version
        - claude_cli: Claude CLI availability
    """
    try:
        # Test Claude CLI availability
        import subprocess
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        claude_available = result.returncode == 0

        status = "healthy" if claude_available else "degraded"

        return {
            "status": status,
            "version": "3.0",
            "claude_cli": "available" if claude_available else "unavailable",
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(json.dumps({
            "event": "health_check_failed",
            "error": str(e)
        }))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Prometheus-compatible metrics endpoint (basic).

    For production, use prometheus_client library.
    """
    # Placeholder - implement with prometheus_client in production
    return {
        "message": "Metrics endpoint - implement with prometheus_client for production"
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(json.dumps({
        "event": "unhandled_exception",
        "error": str(exc),
        "path": request.url.path,
        "method": request.method
    }))

    return JSONResponse(
        status_code=500,
        content={
            "type": "error",
            "error": {
                "message": "Internal server error",
                "code": "internal_error"
            }
        }
    )


# =============================================================================
# Startup/Shutdown
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info(json.dumps({
        "event": "server_startup",
        "version": "3.0"
    }))

    # Test Claude CLI availability
    try:
        import subprocess
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(json.dumps({
                "event": "claude_cli_available",
                "version": result.stdout.strip()
            }))
        else:
            logger.warning(json.dumps({
                "event": "claude_cli_unavailable",
                "error": result.stderr
            }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "claude_cli_check_failed",
            "error": str(e)
        }))


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info(json.dumps({
        "event": "server_shutdown"
    }))

    # Cleanup temp files
    api.cleanup()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Claude Multi-Tenant API Server")
    logger.info("📚 Docs: http://localhost:8000/docs")
    logger.info("🔧 Health: http://localhost:8000/health")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
