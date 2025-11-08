#!/usr/bin/env python3
"""
Claude OAuth API Wrapper v2 - Production Ready with Sessions + MCP
Utilise Claude CLI comme proxy pour OAuth
Supporte sessions continues et serveurs MCP
"""

import subprocess
import json
import os
import uuid
from typing import Optional, List, Union, Iterator, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Model(str, Enum):
    """Modèles disponibles"""
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"
    SONNET_4_5 = "claude-sonnet-4-5-20250929"
    OPUS_4 = "claude-opus-4-20250514"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"


class OutputFormat(str, Enum):
    """Formats de sortie"""
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"


@dataclass
class ClaudeConfig:
    """Configuration Claude CLI avec sessions + MCP"""
    model: str = "sonnet"
    max_thinking_tokens: Optional[int] = None  # 30000 max pour thinking
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None  # ["Bash", "Edit", "Read"] ou [] pour disable
    output_format: str = "text"
    fallback_model: Optional[str] = None
    verbose: bool = False
    timeout: int = 180

    # 🆕 Session management
    session_id: Optional[str] = None  # UUID de session
    persist_session: bool = False  # Auto-génère UUID si True

    # 🆕 MCP support
    enable_mcp: bool = True  # Active serveurs MCP globaux
    skip_mcp_permissions: bool = False  # Bypass permissions MCP
    mcp_config: Optional[str] = None  # Path vers config MCP custom (si autorisé)


class ClaudeOAuthAPI:
    """
    API-compatible wrapper pour Claude CLI v2
    Interface similaire à anthropic.Anthropic()
    + Sessions continues + MCP servers
    """

    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or ClaudeConfig()

        # Auto-generate session ID si persist_session=True
        if self.config.persist_session and not self.config.session_id:
            self.config.session_id = str(uuid.uuid4())

        self.messages = self.Messages(self)
        self._session_used = False  # Track if session was used before

    class Messages:
        def __init__(self, parent: 'ClaudeOAuthAPI'):
            self.parent = parent

        def create(
            self,
            model: Optional[str] = None,
            messages: List[dict] = None,
            system: Optional[str] = None,
            max_tokens: Optional[int] = None,  # Note: pas supporté directement par CLI
            temperature: Optional[float] = None,  # Note: pas supporté par CLI
            stream: bool = False,
            tools: Optional[List[str]] = None,
            max_thinking_tokens: Optional[int] = None,
            **kwargs
        ) -> Union[dict, Iterator[dict]]:
            """
            Créer message via Claude CLI
            Supporte sessions continues et MCP

            Args:
                model: Modèle à utiliser (opus, sonnet, haiku)
                messages: Liste des messages
                system: System prompt
                max_tokens: Max tokens output (non supporté CLI)
                temperature: Temperature (non supporté CLI)
                stream: Streaming mode
                tools: Tools disponibles
                max_thinking_tokens: Limit thinking tokens (env var)

            Returns:
                dict ou Iterator[dict] si stream=True
            """

            if messages is None:
                messages = []

            # Build command
            cmd = ["claude", "--print"]

            # Model
            model_to_use = model or self.parent.config.model
            cmd.extend(["--model", model_to_use])

            # 🆕 Session management
            if self.parent.config.session_id:
                if self.parent._is_new_session():
                    # Première utilisation : créer session avec ID
                    cmd.extend(["--session-id", self.parent.config.session_id])
                    self.parent._session_used = True
                else:
                    # Session existe déjà : reprendre
                    cmd.extend(["--resume", self.parent.config.session_id])

            # System prompt
            system_prompt = system or self.parent.config.system_prompt
            if system_prompt:
                cmd.extend(["--system-prompt", system_prompt])

            # Append system prompt
            if self.parent.config.append_system_prompt:
                cmd.extend(["--append-system-prompt", self.parent.config.append_system_prompt])

            # 🆕 MCP permissions
            if self.parent.config.enable_mcp and self.parent.config.skip_mcp_permissions:
                cmd.append("--dangerously-skip-permissions")

            # Tools
            tools_to_use = tools if tools is not None else self.parent.config.tools
            if tools_to_use is not None:
                if len(tools_to_use) == 0:
                    cmd.extend(["--tools", '""'])  # Disable all tools
                else:
                    cmd.extend(["--tools", ",".join(tools_to_use)])

            # Output format
            if stream:
                cmd.extend(["--output-format", "stream-json"])
                cmd.append("--include-partial-messages")
            else:
                output_fmt = self.parent.config.output_format
                if output_fmt != "text":
                    cmd.extend(["--output-format", output_fmt])

            # Fallback model
            if self.parent.config.fallback_model:
                cmd.extend(["--fallback-model", self.parent.config.fallback_model])

            # Verbose
            if self.parent.config.verbose:
                cmd.append("--verbose")

            # Build prompt from messages
            prompt = self._build_prompt(messages)
            cmd.append(prompt)

            # Prepare environment
            env = os.environ.copy()

            # Max thinking tokens
            thinking_tokens = max_thinking_tokens or self.parent.config.max_thinking_tokens
            if thinking_tokens:
                env["MAX_THINKING_TOKENS"] = str(thinking_tokens)

            # Execute
            if stream:
                return self._stream_response(cmd, env, model_to_use)
            else:
                return self._execute_sync(cmd, env, model_to_use)

        def _build_prompt(self, messages: List[dict]) -> str:
            """Construire prompt depuis messages"""
            # Si session persistante, n'envoyer que le dernier message
            # (contexte précédent dans session)
            if self.parent.config.session_id and not self.parent._is_new_session():
                # Session continue : dernier message seulement
                last_msg = messages[-1] if messages else {"role": "user", "content": ""}
                return self._format_message_content(last_msg)

            # Nouvelle session ou pas de session : tous les messages
            parts = []
            for msg in messages:
                role = msg["role"].upper()
                content = self._format_message_content(msg)
                parts.append(f"{role}: {content}")

            return "\n\n".join(parts)

        def _format_message_content(self, msg: dict) -> str:
            """Formater contenu d'un message"""
            content = msg.get("content", "")

            # Handle multimodal content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "image":
                        text_parts.append("[IMAGE]")  # CLI doesn't support images
                    elif item.get("type") == "tool_use":
                        text_parts.append(f"[TOOL: {item.get('name')}]")
                    elif item.get("type") == "tool_result":
                        text_parts.append(f"[TOOL RESULT]")
                content = "\n".join(text_parts)

            return content

        def _execute_sync(self, cmd: List[str], env: dict, model: str) -> dict:
            """Exécution synchrone"""
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=self.parent.config.timeout
                )

                if result.returncode != 0:
                    return {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": result.stderr or "Claude CLI error"
                        }
                    }

                # Parse output based on format
                if self.parent.config.output_format == "json":
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        # Fallback to text
                        pass

                # Text format (default)
                return {
                    "id": "msg_cli_wrapper",
                    "type": "message",
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": result.stdout.strip()
                    }],
                    "model": model,
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": 0,  # CLI doesn't provide
                        "output_tokens": 0
                    }
                }

            except subprocess.TimeoutExpired:
                return {
                    "type": "error",
                    "error": {
                        "type": "timeout_error",
                        "message": f"Request timeout after {self.parent.config.timeout}s"
                    }
                }
            except Exception as e:
                return {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e)
                    }
                }

        def _stream_response(self, cmd: List[str], env: dict, model: str) -> Iterator[dict]:
            """Streaming response"""
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    env=env
                )

                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue

                    # Parse stream-json format
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix

                    try:
                        event = json.loads(line)
                        yield event
                    except json.JSONDecodeError:
                        # Text line
                        yield {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": line}
                        }

                process.wait()

                if process.returncode != 0:
                    stderr = process.stderr.read()
                    yield {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": stderr
                        }
                    }

            except Exception as e:
                yield {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e)
                    }
                }

    def _is_new_session(self) -> bool:
        """Check si c'est une nouvelle session"""
        return not self._session_used


# Convenience functions
def create_client(
    model: str = "sonnet",
    max_thinking_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
    verbose: bool = False,
    # 🆕 Session params
    session_id: Optional[str] = None,
    persist_session: bool = False,
    # 🆕 MCP params
    enable_mcp: bool = True,
    skip_mcp_permissions: bool = False,
    **kwargs
) -> ClaudeOAuthAPI:
    """
    Créer client Claude OAuth avec config

    Examples:
        >>> # Simple client
        >>> client = create_client(model="sonnet")

        >>> # With persistent session
        >>> client = create_client(model="sonnet", persist_session=True)
        >>> print(client.config.session_id)  # Auto-generated UUID

        >>> # With MCP enabled
        >>> client = create_client(model="sonnet", enable_mcp=True, skip_mcp_permissions=True)
    """
    config = ClaudeConfig(
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        system_prompt=system_prompt,
        tools=tools,
        verbose=verbose,
        session_id=session_id,
        persist_session=persist_session,
        enable_mcp=enable_mcp,
        skip_mcp_permissions=skip_mcp_permissions,
        **kwargs
    )
    return ClaudeOAuthAPI(config)


def quick_message(
    prompt: str,
    model: str = "sonnet",
    session_id: Optional[str] = None,
    **kwargs
) -> str:
    """
    Envoyer message rapide et récupérer texte
    Supporte session_id pour conversations continues

    Examples:
        >>> # Simple message
        >>> response = quick_message("What is 2+2?")
        >>> print(response)
        '4'

        >>> # With session
        >>> session_id = str(uuid.uuid4())
        >>> response1 = quick_message("Let's talk about Python", session_id=session_id)
        >>> response2 = quick_message("What language?", session_id=session_id)
        >>> print(response2)  # "Python"
    """
    client = create_client(model=model, session_id=session_id, **kwargs)
    response = client.messages.create(
        messages=[{"role": "user", "content": prompt}]
    )

    if response.get("type") == "error":
        raise Exception(response["error"]["message"])

    return response["content"][0]["text"]


# 🆕 MCP utilities
def list_mcp_tools(model: str = "sonnet") -> List[str]:
    """
    Lister tous les outils MCP disponibles

    Returns:
        Liste des noms d'outils MCP
    """
    client = create_client(model=model, enable_mcp=True, skip_mcp_permissions=True)
    response = client.messages.create(
        messages=[{"role": "user", "content": "List all available MCP tools. Output as a simple list of tool names."}]
    )

    if response.get("type") == "error":
        return []

    text = response["content"][0]["text"]
    # Simple parsing (peut être amélioré)
    tools = []
    for line in text.split("\n"):
        if line.strip().startswith("mcp__"):
            tool_name = line.strip().split()[0]
            tools.append(tool_name)

    return tools


# Test CLI availability
def check_cli_available() -> bool:
    """Vérifier que Claude CLI est disponible"""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


if __name__ == "__main__":
    # Tests basiques
    print("🧪 Testing Claude OAuth API Wrapper v2 (Sessions + MCP)\n")

    # Check CLI
    if not check_cli_available():
        print("❌ Claude CLI not found!")
        print("Install: curl -fsSL https://claude.ai/install.sh | sh")
        exit(1)

    print("✅ Claude CLI available\n")

    # Test 1: Simple message
    print("Test 1: Simple message")
    try:
        response = quick_message("What is 2+2? Answer with just the number.")
        print(f"Response: {response}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 2: Session persistence
    print("Test 2: Session persistence")
    try:
        # Create client with persistent session
        client = create_client(model="sonnet", persist_session=True)
        session_id = client.config.session_id
        print(f"Session ID: {session_id}")

        # Message 1
        response1 = client.messages.create(
            messages=[{"role": "user", "content": "Let's talk about Python programming"}]
        )
        print(f"Response 1: {response1['content'][0]['text'][:100]}...")

        # Message 2 (should remember context)
        response2 = client.messages.create(
            messages=[{"role": "user", "content": "What programming language were we discussing?"}]
        )
        print(f"Response 2: {response2['content'][0]['text']}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 3: MCP tools
    print("Test 3: MCP tools (if configured)")
    try:
        client = create_client(
            model="sonnet",
            enable_mcp=True,
            skip_mcp_permissions=True
        )
        response = client.messages.create(
            messages=[{"role": "user", "content": "Use mcp__memory__create_entities to store: name='TestSession', type='demo', observations=['Created during test']"}]
        )
        print(f"MCP Response: {response['content'][0]['text'][:200]}...\n")
    except Exception as e:
        print(f"Error (expected if no MCP configured): {e}\n")

    # Test 4: Streaming with session
    print("Test 4: Streaming with persistent session")
    try:
        client = create_client(model="sonnet", persist_session=True)
        print("Streaming: ", end="", flush=True)
        for chunk in client.messages.create(
            messages=[{"role": "user", "content": "Count from 1 to 3"}],
            stream=True
        ):
            if chunk.get("type") == "content_block_delta":
                text = chunk.get("delta", {}).get("text", "")
                print(text, end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\nError: {e}\n")

    print("✅ All tests completed!")
    print("\n💡 Tip: Check `client.config.session_id` to get the session ID for future use")
