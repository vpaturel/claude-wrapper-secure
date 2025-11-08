#!/usr/bin/env python3
"""
MCP Remote Proxy: SSE/Streamable HTTP → stdio
Generic proxy for connecting Claude CLI to remote MCP servers

Supports:
- SSE (Server-Sent Events) transport
- Streamable HTTP (ndjson over persistent HTTP)
- OAuth2 Bearer authentication
- Custom headers
"""
import sys
import json
import asyncio
import logging
import argparse
from typing import Dict, Any, Optional, AsyncIterator
from enum import Enum
import httpx


class Transport(Enum):
    """Supported MCP transport protocols."""
    SSE = "sse"
    STREAMABLE_HTTP = "streamableHttp"


class MCPProxyServer:
    """
    Proxy server that bridges remote MCP servers to local stdio.

    This allows Claude CLI (which only supports stdio MCP) to communicate
    with remote MCP servers using SSE or Streamable HTTP.
    """

    def __init__(
        self,
        transport: Transport,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        oauth2_bearer: Optional[str] = None,
        protocol_version: str = "2024-11-05",
        log_level: str = "info",
        streamable_http_path: str = "/mcp"
    ):
        self.transport = transport
        self.url = url
        self.streamable_http_path = streamable_http_path
        self.headers = headers or {}

        # Add authentication header if provided
        if oauth2_bearer:
            self.headers["Authorization"] = f"Bearer {oauth2_bearer}"

        self.protocol_version = protocol_version

        # Setup logging (stderr only, stdout is for MCP protocol)
        log_levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "none": logging.CRITICAL + 10
        }
        logging.basicConfig(
            level=log_levels.get(log_level, logging.INFO),
            format='[%(asctime)s] [MCP-Proxy] %(levelname)s: %(message)s',
            stream=sys.stderr
        )
        self.logger = logging.getLogger(__name__)

        # State
        self.tools: Dict[str, Any] = {}
        self.resources: Dict[str, Any] = {}
        self.prompts: Dict[str, Any] = {}
        self.next_id = 1

        # HTTP client for persistent connections
        self.http_client: Optional[httpx.AsyncClient] = None
        self.http_stream: Optional[httpx.Response] = None

    # ==================== SSE Transport ====================

    async def initialize_sse(self):
        """Initialize connection using SSE transport."""
        self.logger.info(f"Connecting via SSE: {self.url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream("GET", self.url, headers=self.headers) as response:
                    response.raise_for_status()
                    self.logger.info(f"SSE connected (status {response.status_code})")

                    # Parse SSE events to get connection status
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix

                                if data.get("type") == "connection":
                                    status = data.get("status", "unknown")
                                    tools_count = data.get("tools", 0)
                                    self.logger.info(f"Server status: {status}, tools: {tools_count}")
                                    break  # Connection established

                            except json.JSONDecodeError as e:
                                self.logger.warning(f"Invalid JSON in SSE event: {e}")

            except httpx.HTTPError as e:
                self.logger.error(f"SSE connection failed: {e}")
                raise

        # Request capabilities (tools, resources, prompts)
        await self.request_capabilities_sse()

    async def request_capabilities_sse(self):
        """Request server capabilities via SSE/POST."""
        # Request tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list",
            "params": {}
        }

        message_url = self.url.replace("/sse", "/message")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                message_url,
                json=tools_request,
                headers=self.headers
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result and "tools" in result["result"]:
                    self.tools = {tool["name"]: tool for tool in result["result"]["tools"]}
                    self.logger.info(f"Discovered {len(self.tools)} tools: {list(self.tools.keys())}")

    async def call_tool_sse(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool using SSE/POST transport."""
        self.logger.debug(f"Calling tool '{tool_name}' with args: {arguments}")

        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        message_url = self.url.replace("/sse", "/message")

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    message_url,
                    json=request,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                self.logger.debug(f"Tool result: {result}")
                return result.get("result", {})

            except httpx.HTTPError as e:
                self.logger.error(f"Tool call failed: {e}")
                raise

    # ==================== Streamable HTTP Transport ====================

    async def initialize_streamable_http(self):
        """Initialize connection using Streamable HTTP transport."""
        full_url = f"{self.url}{self.streamable_http_path}"
        self.logger.info(f"Connecting via Streamable HTTP: {full_url}")

        # Create persistent HTTP client
        self.http_client = httpx.AsyncClient(timeout=None)  # No timeout for streams

        # Open bidirectional stream
        self.http_stream = await self.http_client.stream(
            "POST",
            full_url,
            headers={**self.headers, "Content-Type": "application/json"},
            content=self._streamable_http_request_generator()
        ).__aenter__()

        self.logger.info("Streamable HTTP stream opened")

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-proxy",
                    "version": "1.0.0"
                }
            }
        }

        await self._send_streamable_request(init_request)
        init_response = await self._read_streamable_response()

        server_info = init_response.get("result", {}).get("serverInfo", {})
        self.logger.info(f"Server initialized: {server_info.get('name', 'unknown')}")

        # Request tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list",
            "params": {}
        }

        await self._send_streamable_request(tools_request)
        tools_response = await self._read_streamable_response()

        if "result" in tools_response and "tools" in tools_response["result"]:
            self.tools = {tool["name"]: tool for tool in tools_response["result"]["tools"]}
            self.logger.info(f"Discovered {len(self.tools)} tools: {list(self.tools.keys())}")

    async def _streamable_http_request_generator(self) -> AsyncIterator[bytes]:
        """Generator that yields ndjson requests for Streamable HTTP."""
        # This is managed externally via _send_streamable_request
        while True:
            await asyncio.sleep(0.01)  # Keep stream alive

    async def _send_streamable_request(self, request: dict):
        """Send a request over Streamable HTTP stream."""
        line = json.dumps(request) + "\n"
        await self.http_stream.awrite(line.encode('utf-8'))

    async def _read_streamable_response(self) -> dict:
        """Read one response from Streamable HTTP stream."""
        async for line in self.http_stream.aiter_lines():
            if line.strip():
                return json.loads(line)
        raise ConnectionError("Stream closed unexpectedly")

    async def call_tool_streamable_http(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool using Streamable HTTP transport."""
        self.logger.debug(f"Calling tool '{tool_name}' with args: {arguments}")

        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        await self._send_streamable_request(request)
        response = await self._read_streamable_response()

        self.logger.debug(f"Tool result: {response}")
        return response.get("result", {})

    # ==================== Generic Methods ====================

    def _get_next_id(self) -> int:
        """Get next request ID."""
        request_id = self.next_id
        self.next_id += 1
        return request_id

    async def initialize(self):
        """Initialize connection based on transport type."""
        if self.transport == Transport.SSE:
            await self.initialize_sse()
        else:
            await self.initialize_streamable_http()

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool based on transport type."""
        if self.transport == Transport.SSE:
            return await self.call_tool_sse(tool_name, arguments)
        else:
            return await self.call_tool_streamable_http(tool_name, arguments)

    async def cleanup(self):
        """Cleanup resources."""
        if self.http_stream:
            await self.http_stream.aclose()
        if self.http_client:
            await self.http_client.aclose()

    # ==================== stdio MCP Server ====================

    async def run_stdio_server(self):
        """
        Run MCP server over stdio for Claude CLI.

        This method implements the MCP protocol over stdin/stdout,
        forwarding requests to the remote MCP server.
        """
        self.logger.info("Starting stdio MCP server...")

        try:
            # Initialize remote connection
            await self.initialize()
            self.logger.info("Remote MCP server initialized, waiting for Claude CLI requests...")

            # Main request loop
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    self.logger.info("EOF received, shutting down")
                    break

                try:
                    request = json.loads(line.strip())
                    method = request.get("method", "unknown")
                    request_id = request.get("id")
                    self.logger.debug(f"Received request: {method} (id={request_id})")

                    # Handle different MCP methods
                    if method == "initialize":
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "protocolVersion": self.protocol_version,
                                "capabilities": {
                                    "tools": {
                                        "listChanged": False
                                    }
                                },
                                "serverInfo": {
                                    "name": "mcp-proxy",
                                    "version": "1.0.0"
                                }
                            }
                        }
                        self.logger.info(f"Sent initialize response to Claude CLI")

                    elif method == "tools/list":
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "tools": list(self.tools.values())
                            }
                        }

                    elif method == "tools/call":
                        tool_name = request["params"]["name"]
                        arguments = request["params"].get("arguments", {})

                        result = await self.call_tool(tool_name, arguments)

                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": result
                        }

                    else:
                        self.logger.warning(f"Unsupported method: {method}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        }

                    self._write_response(response)

                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON request: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            await self.cleanup()

    def _write_response(self, response: dict):
        """Write a response to stdout."""
        print(json.dumps(response), flush=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Remote Proxy: Bridge remote MCP servers to stdio"
    )

    # Transport (mutually exclusive)
    transport_group = parser.add_mutually_exclusive_group(required=True)
    transport_group.add_argument(
        "--sse",
        help="SSE URL to connect to (e.g., https://server/sse)"
    )
    transport_group.add_argument(
        "--streamableHttp",
        help="Streamable HTTP base URL (e.g., https://server)"
    )

    # Streamable HTTP specific
    parser.add_argument(
        "--streamableHttpPath",
        default="/mcp",
        help="Path for Streamable HTTP endpoint (default: /mcp)"
    )

    # Authentication
    parser.add_argument(
        "--oauth2Bearer",
        help="OAuth2 Bearer token for authentication"
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Custom header in format 'Key: Value' (can be repeated)"
    )

    # Protocol
    parser.add_argument(
        "--protocolVersion",
        default="2024-11-05",
        help="MCP protocol version (default: 2024-11-05)"
    )

    # Logging
    parser.add_argument(
        "--logLevel",
        choices=["debug", "info", "none"],
        default="info",
        help="Logging level (default: info)"
    )

    args = parser.parse_args()

    # Determine transport and URL
    if args.streamableHttp:
        transport = Transport.STREAMABLE_HTTP
        url = args.streamableHttp
    else:
        transport = Transport.SSE
        url = args.sse

    # Parse custom headers
    headers = {}
    for header in args.header:
        if ":" in header:
            key, value = header.split(":", 1)
            headers[key.strip()] = value.strip()

    # Create and run proxy
    proxy = MCPProxyServer(
        transport=transport,
        url=url,
        headers=headers,
        oauth2_bearer=args.oauth2Bearer,
        protocol_version=args.protocolVersion,
        log_level=args.logLevel,
        streamable_http_path=args.streamableHttpPath
    )

    try:
        asyncio.run(proxy.run_stdio_server())
    except KeyboardInterrupt:
        print("\n[MCP-Proxy] Interrupted by user", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
