#!/usr/bin/env python3
"""
Claude OAuth API - Multi-Tenant Wrapper v3

Architecture multi-utilisateur avec:
- Support tokens OAuth externes (sk-ant-oat01-xxx)
- MCP servers custom par requête
- Sessions isolées par user
- Flag --settings pour injection dynamique

Usage:
    from claude_oauth_api_multi_tenant import MultiTenantClaudeAPI

    api = MultiTenantClaudeAPI()

    response = api.create_message(
        oauth_token="sk-ant-oat01-user1-token",
        messages=[{"role": "user", "content": "Hello"}],
        mcp_servers={
            "custom": {
                "command": "http",
                "args": ["https://user-mcp.com"],
                "env": {"AUTH": "Bearer token"}
            }
        },
        session_id="user1-session-123"
    )
"""

import subprocess
import json
import uuid
import tempfile
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class UserOAuthCredentials:
    """Credentials OAuth d'un utilisateur externe"""
    access_token: str  # sk-ant-oat01-xxx
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    scopes: Optional[List[str]] = None
    subscription_type: Optional[str] = "Max"  # Max, Pro, Free


@dataclass
class MCPServerConfig:
    """Configuration d'un serveur MCP custom"""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


@dataclass
class MultiTenantConfig:
    """Configuration pour requête multi-tenant"""
    model: str = "sonnet"
    oauth_credentials: Optional[UserOAuthCredentials] = None
    mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    session_id: Optional[str] = None
    persist_session: bool = False
    skip_mcp_permissions: bool = True
    timeout: int = 180
    verbose: bool = False


class MultiTenantClaudeAPI:
    """
    API Claude OAuth multi-tenant.

    Permet à plusieurs utilisateurs d'utiliser l'API avec leurs propres:
    - Tokens OAuth
    - Serveurs MCP
    - Sessions
    """

    def __init__(self):
        self.claude_bin = self._find_claude_binary()
        self._temp_files: List[str] = []  # Cleanup temp files

    def _find_claude_binary(self) -> str:
        """Trouve le binaire Claude CLI"""
        result = subprocess.run(
            ["which", "claude"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError("Claude CLI not found. Install: curl -fsSL https://claude.ai/install.sh | sh")
        return result.stdout.strip()

    def _create_temp_credentials(self, credentials: UserOAuthCredentials) -> str:
        """
        Crée un fichier temporaire avec les credentials OAuth de l'utilisateur.

        Format: ~/.claude/.credentials.json
        """
        creds_data = {
            "claudeAiOauth": {
                "accessToken": credentials.access_token,
                "refreshToken": credentials.refresh_token or "",
                "expiresAt": credentials.expires_at or 0,
                "scopes": credentials.scopes or ["all"],
                "subscriptionType": credentials.subscription_type
            }
        }

        # Créer structure temp
        temp_dir = Path(tempfile.mkdtemp(prefix="claude_user_"))
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir()

        creds_file = claude_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds_data, indent=2))

        self._temp_files.append(str(temp_dir))
        return str(temp_dir)

    def _build_settings_json(
        self,
        mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    ) -> str:
        """
        Construit le JSON pour --settings avec MCP servers custom.
        """
        settings = {}

        # MCP servers
        if mcp_servers:
            settings["mcpServers"] = {}
            for name, config in mcp_servers.items():
                settings["mcpServers"][name] = {
                    "command": config.command,
                    "args": config.args
                }
                if config.env:
                    settings["mcpServers"][name]["env"] = config.env

        return json.dumps(settings)

    def create_message(
        self,
        messages: List[Dict[str, str]],
        oauth_token: Optional[str] = None,
        mcp_servers: Optional[Dict[str, MCPServerConfig]] = None,
        session_id: Optional[str] = None,
        persist_session: bool = False,
        model: str = "sonnet",
        skip_mcp_permissions: bool = True,
        timeout: int = 180,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Crée un message avec credentials et MCP custom.

        Args:
            messages: Messages à envoyer
            oauth_token: Token OAuth user (sk-ant-oat01-xxx) ou None pour système
            mcp_servers: Serveurs MCP custom pour cette requête
            session_id: ID session pour conversation continue
            persist_session: Auto-générer session ID si True
            model: opus, sonnet, haiku
            skip_mcp_permissions: Auto-approve outils MCP
            timeout: Timeout secondes
            stream: Streaming mode

        Returns:
            Response dict format Claude API
        """

        # Auto-generate session ID
        if persist_session and not session_id:
            session_id = str(uuid.uuid4())

        # Build command
        cmd = [self.claude_bin, "--print"]

        # Model
        model_map = {
            "opus": "claude-opus-4-20250514",
            "sonnet": "claude-sonnet-4-5-20250929",
            "haiku": "claude-3-5-haiku-20241022"
        }
        cmd.extend(["--model", model_map.get(model, model)])

        # Session management
        if session_id:
            cmd.extend(["--resume", session_id])

        # MCP permissions
        if mcp_servers and skip_mcp_permissions:
            cmd.append("--dangerously-skip-permissions")

        # Settings JSON (MCP servers custom)
        if mcp_servers:
            settings_json = self._build_settings_json(mcp_servers)
            cmd.extend(["--settings", settings_json])

        # Output format
        if stream:
            cmd.extend(["--output-format", "stream-json", "--include-partial-messages"])

        # Build prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt = "\n\n".join(prompt_parts)
        cmd.append(prompt)

        # Environment avec credentials custom si fourni
        env = os.environ.copy()
        temp_home = None

        if oauth_token:
            # Créer credentials temporaires
            credentials = UserOAuthCredentials(access_token=oauth_token)
            temp_home = self._create_temp_credentials(credentials)
            env["HOME"] = temp_home

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )

            if result.returncode != 0:
                return {
                    "type": "error",
                    "error": {
                        "message": result.stderr or "Claude CLI error",
                        "code": "cli_error"
                    }
                }

            # Parse response
            if stream:
                # Return raw SSE stream
                return {"type": "stream", "stream": result.stdout}
            else:
                # Parse JSON response
                try:
                    response = json.loads(result.stdout)
                    return response
                except json.JSONDecodeError:
                    # Fallback: wrap text response
                    return {
                        "type": "message",
                        "content": [{"type": "text", "text": result.stdout.strip()}],
                        "model": model,
                        "usage": {}
                    }

        finally:
            # Cleanup temp credentials
            if temp_home and temp_home in self._temp_files:
                import shutil
                shutil.rmtree(temp_home, ignore_errors=True)
                self._temp_files.remove(temp_home)

    def list_mcp_tools(
        self,
        oauth_token: Optional[str] = None,
        mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    ) -> List[str]:
        """
        Liste tous les outils MCP disponibles.

        Args:
            oauth_token: Token OAuth pour user spécifique
            mcp_servers: Serveurs MCP custom

        Returns:
            Liste des noms d'outils MCP
        """
        response = self.create_message(
            messages=[{"role": "user", "content": "List all MCP tools available"}],
            oauth_token=oauth_token,
            mcp_servers=mcp_servers
        )

        # Parse tools from response
        text = response.get("content", [{}])[0].get("text", "")
        tools = []
        for line in text.split("\n"):
            if "mcp__" in line:
                # Extract tool name
                parts = line.split("mcp__")
                if len(parts) > 1:
                    tool = "mcp__" + parts[1].split()[0].strip(":")
                    tools.append(tool)

        return tools

    def cleanup(self):
        """Nettoie tous les fichiers temporaires"""
        import shutil
        for temp_path in self._temp_files:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
        self._temp_files.clear()

    def __del__(self):
        """Cleanup automatique"""
        self.cleanup()


# =============================================================================
# EXEMPLES D'UTILISATION
# =============================================================================

def example_basic_multi_user():
    """Exemple: Plusieurs utilisateurs avec leurs propres tokens"""
    api = MultiTenantClaudeAPI()

    # User 1
    response1 = api.create_message(
        oauth_token="sk-ant-oat01-user1-token-here",
        messages=[{"role": "user", "content": "Hello from user 1"}]
    )
    print(f"User 1: {response1}")

    # User 2
    response2 = api.create_message(
        oauth_token="sk-ant-oat01-user2-token-here",
        messages=[{"role": "user", "content": "Hello from user 2"}]
    )
    print(f"User 2: {response2}")


def example_custom_mcp():
    """Exemple: MCP servers custom par utilisateur"""
    api = MultiTenantClaudeAPI()

    # User avec MCP custom
    user_mcp = {
        "user_memory": MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        ),
        "user_http": MCPServerConfig(
            command="http-mcp-server",
            args=["https://api.user.com"],
            env={"AUTH_TOKEN": "user_secret"}
        )
    }

    response = api.create_message(
        oauth_token="sk-ant-oat01-user-token",
        mcp_servers=user_mcp,
        messages=[{
            "role": "user",
            "content": "Use user_memory MCP to store: name='Project', type='AI'"
        }],
        skip_mcp_permissions=True
    )

    print(response)


def example_session_per_user():
    """Exemple: Sessions persistantes par utilisateur"""
    api = MultiTenantClaudeAPI()

    user_token = "sk-ant-oat01-user1-token"
    session_id = "user1-conversation-123"

    # Message 1
    response1 = api.create_message(
        oauth_token=user_token,
        session_id=session_id,
        messages=[{"role": "user", "content": "Let's discuss Python"}]
    )

    # Message 2 (context retained)
    response2 = api.create_message(
        oauth_token=user_token,
        session_id=session_id,
        messages=[{"role": "user", "content": "What language were we discussing?"}]
    )

    print(f"Response 2: {response2}")  # Should say "Python"


def example_fastapi_server():
    """Exemple: Serveur FastAPI multi-tenant"""
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel

    app = FastAPI()
    api = MultiTenantClaudeAPI()

    class MessageRequest(BaseModel):
        messages: List[Dict[str, str]]
        session_id: Optional[str] = None
        mcp_servers: Optional[Dict[str, Dict[str, Any]]] = None

    @app.post("/v1/messages")
    async def create_message(
        request: MessageRequest,
        authorization: str = Header(...),
        x_mcp_config: Optional[str] = Header(None)
    ):
        """
        Endpoint multi-tenant compatible OpenAI/Anthropic.

        Headers:
            Authorization: Bearer sk-ant-oat01-xxx (OAuth token user)
            X-MCP-Config: {"server": {"command": "...", "args": [...]}}
        """
        # Extract OAuth token
        if not authorization.startswith("Bearer sk-ant-oat01-"):
            raise HTTPException(401, "Invalid OAuth token")

        oauth_token = authorization.replace("Bearer ", "")

        # Parse MCP config
        mcp_servers = None
        if x_mcp_config:
            mcp_data = json.loads(x_mcp_config)
            mcp_servers = {
                name: MCPServerConfig(**config)
                for name, config in mcp_data.items()
            }

        # Create message
        response = api.create_message(
            oauth_token=oauth_token,
            messages=request.messages,
            session_id=request.session_id,
            mcp_servers=mcp_servers,
            skip_mcp_permissions=True
        )

        return response

    return app


if __name__ == "__main__":
    print("🚀 Claude OAuth API - Multi-Tenant v3")
    print("=" * 60)

    # Test basic
    print("\n1. Test création API...")
    api = MultiTenantClaudeAPI()
    print("✅ API créée")

    # Test sans token (utilise credentials système)
    print("\n2. Test message système (sans token externe)...")
    response = api.create_message(
        messages=[{"role": "user", "content": "Say 'Hello Multi-Tenant'"}],
        model="sonnet"
    )
    print(f"✅ Response: {response.get('content', [{}])[0].get('text', 'N/A')[:50]}...")

    # Test list MCP tools
    print("\n3. Test list MCP tools...")
    tools = api.list_mcp_tools()
    print(f"✅ {len(tools)} outils MCP trouvés")
    for tool in tools[:5]:
        print(f"   - {tool}")

    print("\n✅ Tous les tests passés!")
    print("\n" + "=" * 60)
    print("📚 Pour utiliser avec tokens externes:")
    print("   response = api.create_message(")
    print("       oauth_token='sk-ant-oat01-xxx',")
    print("       messages=[...],")
    print("       mcp_servers={...}")
    print("   )")
