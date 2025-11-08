#!/usr/bin/env python3
"""
Claude OAuth API - ULTIMATE Version v4 🔥

Toutes les features possibles du Claude CLI intégrées.

Features:
- Multi-tenant (tokens OAuth externes)
- MCP servers custom avec auth
- Sessions persistantes
- Custom agents via JSON
- System prompts dynamiques
- Fallback models automatique
- Tools control granulaire
- Permission modes
- Debug mode
- Plugin support
- Bidirectional streaming
- Et plus !

Author: Claude Multi-Tenant Team
Version: 4.0 ULTIMATE
"""

import subprocess
import json
import uuid
import tempfile
import os
import shutil
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


# =============================================================================
# Enums & Types
# =============================================================================

class PermissionMode(str, Enum):
    """Permission modes disponibles"""
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    DEFAULT = "default"
    PLAN = "plan"


class OutputFormat(str, Enum):
    """Output formats"""
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"


class InputFormat(str, Enum):
    """Input formats"""
    TEXT = "text"
    STREAM_JSON = "stream-json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MCPServerConfig:
    """Configuration MCP server"""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


@dataclass
class CustomAgent:
    """Custom agent definition"""
    name: str
    description: str
    prompt: str
    tools: Optional[List[str]] = None


@dataclass
class OAuthCredentials:
    """OAuth credentials externes"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    scopes: Optional[List[str]] = None
    subscription_type: str = "Max"


@dataclass
class UltimateConfig:
    """
    Configuration ULTIME avec TOUTES les options CLI.
    """

    # Core
    model: str = "sonnet"
    fallback_model: Optional[str] = None

    # OAuth & Credentials
    oauth_credentials: Optional[OAuthCredentials] = None

    # Session Management
    session_id: Optional[str] = None
    persist_session: bool = False
    continue_recent: bool = False
    fork_session: bool = False

    # MCP Servers
    mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    enable_mcp: bool = True
    skip_mcp_permissions: bool = False
    strict_mcp_config: bool = False

    # System Prompts
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None

    # Tools Control
    allowed_tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = None
    tools: Optional[List[str]] = None  # "default", "", ou liste

    # Permissions
    permission_mode: Optional[PermissionMode] = None

    # Directories
    add_dirs: Optional[List[str]] = None

    # Custom Agents 🔥
    custom_agents: Optional[Dict[str, CustomAgent]] = None

    # Plugins 🔥
    plugin_dirs: Optional[List[str]] = None

    # Settings
    settings_json: Optional[Dict[str, Any]] = None
    setting_sources: Optional[List[str]] = None  # user, project, local

    # Output/Input
    output_format: OutputFormat = OutputFormat.TEXT
    input_format: InputFormat = InputFormat.TEXT
    include_partial_messages: bool = False
    replay_user_messages: bool = False

    # Debug & Logging
    debug: Optional[str] = None  # Filter comme "api,hooks" ou "!statsig"
    verbose: bool = False

    # Misc
    timeout: int = 180
    ide_auto_connect: bool = False


# =============================================================================
# Ultimate API Class
# =============================================================================

class ClaudeOAuthUltimateAPI:
    """
    API Claude OAuth ULTIME.

    Intègre TOUTES les features du CLI Claude.
    """

    def __init__(self, config: Optional[UltimateConfig] = None):
        self.config = config or UltimateConfig()
        self.claude_bin = self._find_claude_binary()
        self._temp_files: List[str] = []
        self._session_used = False

        # Auto-generate session ID si persist_session
        if self.config.persist_session and not self.config.session_id:
            self.config.session_id = str(uuid.uuid4())

    def _find_claude_binary(self) -> str:
        """Trouve binaire Claude CLI"""
        result = subprocess.run(["which", "claude"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Claude CLI not found")
        return result.stdout.strip()

    def _create_temp_credentials(self, credentials: OAuthCredentials) -> str:
        """Crée credentials temporaires pour user"""
        temp_dir = Path(tempfile.mkdtemp(prefix="claude_user_"))
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir()

        creds_data = {
            "claudeAiOauth": {
                "accessToken": credentials.access_token,
                "refreshToken": credentials.refresh_token or "",
                "expiresAt": credentials.expires_at or 0,
                "scopes": credentials.scopes or ["all"],
                "subscriptionType": credentials.subscription_type
            }
        }

        creds_file = claude_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds_data, indent=2))

        self._temp_files.append(str(temp_dir))
        return str(temp_dir)

    def _build_settings_json(self) -> Optional[str]:
        """Build settings JSON avec MCP + permissions + agents"""
        settings = self.config.settings_json or {}

        # MCP servers
        if self.config.mcp_servers:
            settings["mcpServers"] = {}
            for name, config in self.config.mcp_servers.items():
                settings["mcpServers"][name] = {
                    "command": config.command,
                    "args": config.args
                }
                if config.env:
                    settings["mcpServers"][name]["env"] = config.env

        # Permissions
        if self.config.allowed_tools or self.config.disallowed_tools or self.config.permission_mode:
            settings.setdefault("permissions", {})
            if self.config.permission_mode:
                settings["permissions"]["defaultMode"] = self.config.permission_mode.value
            if self.config.allowed_tools:
                settings["permissions"]["allowedTools"] = self.config.allowed_tools
            if self.config.disallowed_tools:
                settings["permissions"]["deny"] = self.config.disallowed_tools

        return json.dumps(settings) if settings else None

    def _build_agents_json(self) -> Optional[str]:
        """Build custom agents JSON"""
        if not self.config.custom_agents:
            return None

        agents = {}
        for name, agent in self.config.custom_agents.items():
            agents[name] = {
                "description": agent.description,
                "prompt": agent.prompt
            }
            if agent.tools:
                agents[name]["tools"] = agent.tools

        return json.dumps(agents)

    def _is_new_session(self) -> bool:
        """Check si c'est une nouvelle session ou reprise"""
        return not self._session_used

    def create_message(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Crée message avec TOUTES les options CLI.

        Args:
            messages: Messages à envoyer
            stream: Enable streaming

        Returns:
            Response dict
        """

        # Build command
        cmd = [self.claude_bin, "--print"]

        # Model
        model_map = {
            "opus": "claude-opus-4-20250514",
            "sonnet": "claude-sonnet-4-5-20250929",
            "haiku": "claude-3-5-haiku-20241022"
        }
        cmd.extend(["--model", model_map.get(self.config.model, self.config.model)])

        # Fallback model
        if self.config.fallback_model:
            fallback = model_map.get(self.config.fallback_model, self.config.fallback_model)
            cmd.extend(["--fallback-model", fallback])

        # Session management
        if self.config.continue_recent:
            cmd.append("--continue")
        elif self.config.session_id:
            if self._is_new_session():
                cmd.extend(["--session-id", self.config.session_id])
                self._session_used = True
            else:
                cmd.extend(["--resume", self.config.session_id])

        if self.config.fork_session:
            cmd.append("--fork-session")

        # System prompts
        if self.config.system_prompt:
            cmd.extend(["--system-prompt", self.config.system_prompt])
        if self.config.append_system_prompt:
            cmd.extend(["--append-system-prompt", self.config.append_system_prompt])

        # Tools control
        if self.config.tools is not None:
            tools_list = self.config.tools if isinstance(self.config.tools, list) else [self.config.tools]
            cmd.extend(["--tools", *tools_list])
        if self.config.allowed_tools:
            cmd.extend(["--allowed-tools", *self.config.allowed_tools])
        if self.config.disallowed_tools:
            cmd.extend(["--disallowed-tools", *self.config.disallowed_tools])

        # Permission mode
        if self.config.permission_mode:
            cmd.extend(["--permission-mode", self.config.permission_mode.value])

        # MCP
        if self.config.skip_mcp_permissions:
            cmd.append("--dangerously-skip-permissions")
        if self.config.strict_mcp_config:
            cmd.append("--strict-mcp-config")

        # Settings JSON
        settings_json = self._build_settings_json()
        if settings_json:
            cmd.extend(["--settings", settings_json])

        # Custom agents 🔥
        agents_json = self._build_agents_json()
        if agents_json:
            cmd.extend(["--agents", agents_json])

        # Directories
        if self.config.add_dirs:
            cmd.extend(["--add-dir", *self.config.add_dirs])

        # Plugins 🔥
        if self.config.plugin_dirs:
            for plugin_dir in self.config.plugin_dirs:
                cmd.extend(["--plugin-dir", plugin_dir])

        # Setting sources
        if self.config.setting_sources:
            cmd.extend(["--setting-sources", ",".join(self.config.setting_sources)])

        # Output format
        if stream or self.config.output_format != OutputFormat.TEXT:
            output_fmt = OutputFormat.STREAM_JSON if stream else self.config.output_format
            cmd.extend(["--output-format", output_fmt.value])

        if self.config.include_partial_messages:
            cmd.append("--include-partial-messages")

        # Input format
        if self.config.input_format != InputFormat.TEXT:
            cmd.extend(["--input-format", self.config.input_format.value])

        if self.config.replay_user_messages:
            cmd.append("--replay-user-messages")

        # Debug & verbose
        if self.config.debug:
            cmd.extend(["--debug", self.config.debug])
        if self.config.verbose:
            cmd.append("--verbose")

        # IDE auto-connect
        if self.config.ide_auto_connect:
            cmd.append("--ide")

        # Build prompt from messages
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

        # Environment avec credentials custom
        env = os.environ.copy()
        temp_home = None

        if self.config.oauth_credentials:
            temp_home = self._create_temp_credentials(self.config.oauth_credentials)
            env["HOME"] = temp_home

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
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
            if stream or self.config.output_format == OutputFormat.STREAM_JSON:
                return {"type": "stream", "stream": result.stdout}
            elif self.config.output_format == OutputFormat.JSON:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {
                        "type": "message",
                        "content": [{"type": "text", "text": result.stdout.strip()}]
                    }
            else:
                return {
                    "type": "message",
                    "content": [{"type": "text", "text": result.stdout.strip()}]
                }

        finally:
            # Cleanup
            if temp_home and temp_home in self._temp_files:
                shutil.rmtree(temp_home, ignore_errors=True)
                self._temp_files.remove(temp_home)

    def cleanup(self):
        """Cleanup temp files"""
        for temp_path in self._temp_files:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
        self._temp_files.clear()

    def __del__(self):
        self.cleanup()


# =============================================================================
# Helper Functions
# =============================================================================

def create_ultimate_client(**kwargs) -> ClaudeOAuthUltimateAPI:
    """
    Crée client ULTIME avec toutes les options.

    Usage:
        client = create_ultimate_client(
            model="sonnet",
            fallback_model="haiku",
            system_prompt="You are a helpful assistant",
            custom_agents={
                "reviewer": CustomAgent(
                    name="reviewer",
                    description="Code reviewer",
                    prompt="You are an expert code reviewer"
                )
            },
            mcp_servers={
                "memory": MCPServerConfig(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-memory"]
                )
            },
            debug="api,mcp",
            verbose=True
        )
    """
    config = UltimateConfig(**kwargs)
    return ClaudeOAuthUltimateAPI(config)


# =============================================================================
# Examples
# =============================================================================

def example_custom_agents():
    """Exemple: Custom agents"""
    client = create_ultimate_client(
        model="sonnet",
        custom_agents={
            "code_reviewer": CustomAgent(
                name="code_reviewer",
                description="Expert code reviewer focusing on security and performance",
                prompt="You are a senior code reviewer. Analyze code for security vulnerabilities, "
                       "performance issues, and best practices. Provide actionable feedback.",
                tools=["Read", "Bash(git:*)"]
            ),
            "bug_hunter": CustomAgent(
                name="bug_hunter",
                description="Finds bugs in code",
                prompt="You are a bug detection specialist. Find potential bugs, edge cases, "
                       "and logic errors. Be thorough and suggest fixes.",
                tools=["Read", "Grep"]
            )
        }
    )

    response = client.create_message(
        messages=[{"role": "user", "content": "Review this code for security issues"}]
    )

    print(response)


def example_fallback_model():
    """Exemple: Fallback automatique"""
    client = create_ultimate_client(
        model="opus",
        fallback_model="sonnet",  # Si Opus overloaded, use Sonnet
    )

    response = client.create_message(
        messages=[{"role": "user", "content": "Complex reasoning task"}]
    )

    print(response)


def example_tools_control():
    """Exemple: Contrôle granulaire des outils"""
    client = create_ultimate_client(
        model="sonnet",
        tools=["Read", "Bash"],  # Uniquement Read et Bash
        allowed_tools=["Bash(git:*)", "Bash(ls:*)"],  # Seulement git et ls
        disallowed_tools=["Bash(rm:*)", "Bash(sudo:*)"]  # Interdire rm et sudo
    )

    response = client.create_message(
        messages=[{"role": "user", "content": "List files and show git status"}]
    )

    print(response)


def example_system_prompts():
    """Exemple: System prompts dynamiques"""
    client = create_ultimate_client(
        model="sonnet",
        system_prompt="You are a Python expert specializing in FastAPI.",
        append_system_prompt="Always provide code examples with type hints and docstrings."
    )

    response = client.create_message(
        messages=[{"role": "user", "content": "How to create a FastAPI endpoint?"}]
    )

    print(response)


def example_debug_mode():
    """Exemple: Debug mode avec filtering"""
    client = create_ultimate_client(
        model="sonnet",
        debug="api,mcp",  # Debug API et MCP uniquement
        verbose=True
    )

    response = client.create_message(
        messages=[{"role": "user", "content": "Test with debug"}]
    )

    print(response)


def example_permission_modes():
    """Exemple: Différents modes permission"""

    # Mode PLAN - Pour planning sans exécution
    client_plan = create_ultimate_client(
        model="sonnet",
        permission_mode=PermissionMode.PLAN
    )

    # Mode BYPASS - Pour automation complète
    client_bypass = create_ultimate_client(
        model="sonnet",
        permission_mode=PermissionMode.BYPASS
    )

    # Mode ACCEPT_EDITS - Auto-accepte éditions
    client_accept = create_ultimate_client(
        model="sonnet",
        permission_mode=PermissionMode.ACCEPT_EDITS
    )


if __name__ == "__main__":
    print("🔥 Claude OAuth API - ULTIMATE Version v4")
    print("=" * 80)

    print("\n✅ Features disponibles:")
    features = [
        "Multi-tenant (OAuth tokens externes)",
        "MCP servers custom avec auth",
        "Sessions persistantes + fork",
        "Custom agents via JSON 🔥",
        "System prompts dynamiques",
        "Fallback models automatique",
        "Tools control granulaire",
        "Permission modes (plan, bypass, etc.)",
        "Debug mode avec filtering",
        "Plugin support",
        "Bidirectional streaming",
        "Add directories",
        "Verbose logging",
        "IDE auto-connect"
    ]

    for i, feature in enumerate(features, 1):
        print(f"   {i}. {feature}")

    print("\n" + "=" * 80)
    print("📚 Voir exemples dans le code pour usage!")
