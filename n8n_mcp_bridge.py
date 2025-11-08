#!/usr/bin/env python3
"""
n8n MCP Bridge Server

Ce serveur expose l'API n8n via le protocole MCP (Model Context Protocol)
pour permettre à Claude d'interagir avec n8n.

Architecture:
    Claude CLI → MCP Protocol → n8n MCP Bridge → n8n API

Installation:
    pip install fastapi uvicorn httpx

Usage:
    python n8n_mcp_bridge.py --n8n-url http://localhost:5678 --n8n-api-key your-key

Puis dans votre requête Claude Wrapper:
    {
      "mcp_servers": {
        "n8n": {
          "url": "http://localhost:8000/mcp/sse",
          "transport": "sse",
          "auth_type": "bearer",
          "auth_token": "your-bridge-token"
        }
      }
    }
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import argparse

try:
    from fastapi import FastAPI, Header, HTTPException, Request
    from fastapi.responses import StreamingResponse
    import httpx
except ImportError:
    print("❌ Dépendances manquantes!")
    print("   Installez: pip install fastapi uvicorn httpx")
    exit(1)

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

app = FastAPI(
    title="n8n MCP Bridge",
    description="MCP Bridge Server for n8n API",
    version="1.0.0"
)

# Configuration globale (définie au démarrage)
N8N_URL = "http://localhost:5678"
N8N_API_KEY = ""
BRIDGE_TOKEN = "test-bridge-token"

# =============================================================================
# n8n API Client
# =============================================================================

class N8nClient:
    """Client pour interagir avec l'API n8n"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json"
        }

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """Liste tous les workflows"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Récupère un workflow par ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exécute un workflow"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
                headers=self.headers,
                json=data or {},
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()

    async def get_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Liste les exécutions"""
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/executions",
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def health_check(self) -> bool:
        """Vérifie si n8n est accessible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/healthz",
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False


# =============================================================================
# MCP Protocol Implementation
# =============================================================================

class MCPTools:
    """Outils MCP pour n8n"""

    def __init__(self, n8n_client: N8nClient):
        self.n8n = n8n_client

    def get_tools(self) -> List[Dict[str, Any]]:
        """Retourne la liste des outils MCP disponibles"""
        return [
            {
                "name": "list_workflows",
                "description": "Liste tous les workflows n8n disponibles",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_workflow",
                "description": "Récupère les détails d'un workflow par son ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID du workflow"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "execute_workflow",
                "description": "Exécute un workflow n8n avec des données optionnelles",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID du workflow à exécuter"
                        },
                        "data": {
                            "type": "object",
                            "description": "Données à passer au workflow (optionnel)"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "get_executions",
                "description": "Liste les exécutions de workflows (historique)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID du workflow (optionnel)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre max d'exécutions (défaut: 10)",
                            "default": 10
                        }
                    },
                    "required": []
                }
            }
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exécute un outil MCP"""

        try:
            if tool_name == "list_workflows":
                workflows = await self.n8n.list_workflows()
                return {
                    "success": True,
                    "result": {
                        "count": len(workflows),
                        "workflows": workflows
                    }
                }

            elif tool_name == "get_workflow":
                workflow_id = arguments.get("workflow_id")
                if not workflow_id:
                    return {"success": False, "error": "workflow_id required"}

                workflow = await self.n8n.get_workflow(workflow_id)
                return {
                    "success": True,
                    "result": workflow
                }

            elif tool_name == "execute_workflow":
                workflow_id = arguments.get("workflow_id")
                if not workflow_id:
                    return {"success": False, "error": "workflow_id required"}

                data = arguments.get("data", {})
                result = await self.n8n.execute_workflow(workflow_id, data)
                return {
                    "success": True,
                    "result": result
                }

            elif tool_name == "get_executions":
                workflow_id = arguments.get("workflow_id")
                limit = arguments.get("limit", 10)

                executions = await self.n8n.get_executions(workflow_id, limit)
                return {
                    "success": True,
                    "result": {
                        "count": len(executions),
                        "executions": executions
                    }
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"n8n API error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }


# =============================================================================
# MCP Endpoints (SSE Transport)
# =============================================================================

@app.get("/")
async def root():
    """Info endpoint"""
    return {
        "service": "n8n MCP Bridge",
        "version": "1.0.0",
        "protocol": "MCP",
        "transport": "SSE",
        "n8n_url": N8N_URL,
        "endpoints": {
            "sse": "/mcp/sse",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    n8n_client = N8nClient(N8N_URL, N8N_API_KEY)
    n8n_healthy = await n8n_client.health_check()

    return {
        "status": "healthy" if n8n_healthy else "degraded",
        "n8n_accessible": n8n_healthy,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/mcp/sse")
async def mcp_sse(
    authorization: Optional[str] = Header(None)
):
    """
    MCP Server-Sent Events endpoint.

    Claude CLI se connecte à cet endpoint pour:
    1. Découvrir les outils disponibles (tools/list)
    2. Exécuter des outils (tools/call)
    """

    # Vérifier auth
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token != BRIDGE_TOKEN:
            raise HTTPException(401, "Invalid authorization token")

    # Initialize clients
    n8n_client = N8nClient(N8N_URL, N8N_API_KEY)
    mcp_tools = MCPTools(n8n_client)

    async def event_generator():
        """Génère les événements SSE"""

        # 1. Send initialization message
        init_msg = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "serverInfo": {
                    "name": "n8n-mcp-bridge",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
        yield f"data: {json.dumps(init_msg)}\n\n"

        # 2. Simulate tools/list request
        tools = mcp_tools.get_tools()
        tools_msg = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "result": {
                "tools": tools
            }
        }
        yield f"data: {json.dumps(tools_msg)}\n\n"

        # 3. Keep connection alive (heartbeat)
        while True:
            await asyncio.sleep(30)
            heartbeat = {
                "jsonrpc": "2.0",
                "method": "heartbeat",
                "params": {"timestamp": datetime.utcnow().isoformat()}
            }
            yield f"data: {json.dumps(heartbeat)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/mcp/tools/call")
async def mcp_tools_call(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Endpoint pour appeler un outil MCP.

    Body:
        {
          "tool": "list_workflows",
          "arguments": {}
        }
    """

    # Vérifier auth
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token != BRIDGE_TOKEN:
            raise HTTPException(401, "Invalid authorization token")

    # Parse request
    body = await request.json()
    tool_name = body.get("tool")
    arguments = body.get("arguments", {})

    if not tool_name:
        raise HTTPException(400, "Missing 'tool' parameter")

    # Execute tool
    n8n_client = N8nClient(N8N_URL, N8N_API_KEY)
    mcp_tools = MCPTools(n8n_client)

    result = await mcp_tools.call_tool(tool_name, arguments)

    return result


# =============================================================================
# Main
# =============================================================================

def main():
    """Lance le serveur MCP bridge"""
    global N8N_URL, N8N_API_KEY, BRIDGE_TOKEN

    parser = argparse.ArgumentParser(
        description="n8n MCP Bridge Server"
    )
    parser.add_argument(
        "--n8n-url",
        default="http://localhost:5678",
        help="URL de l'instance n8n"
    )
    parser.add_argument(
        "--n8n-api-key",
        required=True,
        help="API Key n8n"
    )
    parser.add_argument(
        "--bridge-token",
        default="test-bridge-token",
        help="Token d'authentification pour le bridge"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host du serveur"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port du serveur"
    )

    args = parser.parse_args()

    # Set global config
    N8N_URL = args.n8n_url
    N8N_API_KEY = args.n8n_api_key
    BRIDGE_TOKEN = args.bridge_token

    logger.info("="*70)
    logger.info("🌉 n8n MCP Bridge Server")
    logger.info("="*70)
    logger.info(f"   n8n URL: {N8N_URL}")
    logger.info(f"   Bridge URL: http://{args.host}:{args.port}")
    logger.info(f"   MCP Endpoint: http://{args.host}:{args.port}/mcp/sse")
    logger.info("="*70)

    # Start server
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
