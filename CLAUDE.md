# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **production-ready secure multi-tenant wrapper** for Claude's OAuth API. It wraps the Claude CLI in a FastAPI service with complete user isolation, deployed on GCP Cloud Run at `wrapper.claude.serenity-system.fr`.

**Key Innovation**: Users send their own OAuth tokens (from claude.ai accounts), and the wrapper provides secure isolation so multiple users can safely share the same service without token or data leakage.

## Architecture

### Core Components

1. **`server.py`** (FastAPI server)
   - REST API endpoints (`POST /v1/messages`, `GET /health`, etc.)
   - Request validation via Pydantic models
   - Streaming support (SSE)
   - MCP server configuration handling

2. **`claude_oauth_api_secure_multitenant.py`** (Security layer)
   - User workspace isolation (per-user directories with 0o700 permissions)
   - Credential isolation (temporary files with 0o600 permissions)
   - Claude CLI subprocess management
   - Tool restrictions (3 security levels: PARANOID/BALANCED/DEVELOPER)
   - Secure cleanup (overwrites credentials before deletion)

3. **`mcp_proxy.py`** (MCP bridge)
   - Bridges remote MCP servers (SSE/StreamableHTTP) to stdio
   - Enables Claude CLI to communicate with remote MCP endpoints
   - Supports authentication (JWT/OAuth/Bearer)

### Security Model (5 Layers)

The system achieves 100% isolation between users through:
1. **Workspace Isolation**: Each user gets a unique directory (`/workspaces/{user_hash}/`)
2. **Credentials Isolation**: OAuth tokens stored in temporary files (0o600, owner-only)
3. **Tools Restrictions**: Deny access to sensitive paths (`/tmp/*`, `/proc/*`, `ps` command)
4. **Secure Cleanup**: Overwrite credential files with zeros before deletion
5. **Path Validation**: Prevent path traversal attacks (`..`, `/` in user IDs)

### Request Flow

```
Client → FastAPI (server.py)
  → SecureMultiTenantAPI (validation + workspace setup)
    → Claude CLI subprocess (isolated per user)
      → Anthropic OAuth API
  ← Response (streaming or complete)
```

### Session Management

The wrapper supports two conversation modes:

- **Stateless**: Client sends full message history each time
  - Simple, full control over context
  - Higher bandwidth usage

- **Stateful**: Client provides `session_id` (UUID v4)
  - Claude CLI maintains context automatically via `--resume` flag
  - 97% bandwidth reduction (only send new messages)
  - Automatic context compacting after ~15 turns (50-70% API cost savings)

### OAuth Token Management

**IMPORTANT**: The wrapper is **stateless** and does NOT persist OAuth credentials. Token refresh is the **client's responsibility**.

#### Token Expiration

OAuth tokens from claude.ai typically expire after 24 hours. The wrapper:
- ✅ Creates temporary `.credentials.json` for each request
- ✅ Destroys workspace after response
- ❌ Does NOT refresh expired tokens
- ❌ Does NOT persist refreshed tokens

#### Client Responsibilities

Before calling the wrapper, the client MUST:

1. **Check token expiration**:
   ```javascript
   if (credentials.expiresAt < Date.now() + 5*60*1000) {
     // Token expires in <5 minutes → refresh needed
     credentials = await refreshOAuthToken(credentials.refreshToken);
     await saveCredentials(credentials); // Save to DB
   }
   ```

2. **Call Anthropic refresh endpoint**:
   ```bash
   POST https://api.claude.ai/api/auth/oauth/token
   Content-Type: application/json

   {
     "grant_type": "refresh_token",
     "refresh_token": "sk-ant-ort01-..."
   }

   # Response
   {
     "access_token": "sk-ant-oat01-NEW...",
     "refresh_token": "sk-ant-ort01-NEW...",  # ⚠️ Also updated!
     "expires_at": 1762618418009,
     "expires_in": 86400,
     "scopes": ["user:inference", "user:profile"],
     "subscription_type": "max"
   }
   ```

3. **Save BOTH new tokens** (access_token AND refresh_token change)

4. **Send fresh credentials to wrapper**:
   ```json
   {
     "oauth_credentials": {
       "access_token": "sk-ant-oat01-NEW...",
       "refresh_token": "sk-ant-ort01-NEW...",
       "expires_at": 1762618418009,
       "scopes": ["user:inference", "user:profile"],
       "subscription_type": "max"
     },
     "messages": [...]
   }
   ```

#### Why Stateless Design?

- ✅ **Simpler architecture**: No database, no token storage
- ✅ **Better security**: Tokens never persisted on wrapper server
- ✅ **Client control**: Client manages their own credentials lifecycle
- ✅ **Scalability**: No shared state between wrapper instances

See `CLIENT_REFRESH_GUIDE.md` for complete implementation examples.

### MCP Server Support

The wrapper supports custom MCP (Model Context Protocol) servers:

- **Local MCP**: Subprocess-based servers (e.g., filesystem access)
  - Config: `{command: "npx", args: [...], env: {...}}`

- **Remote MCP**: HTTP/SSE-based servers (e.g., n8n, custom APIs)
  - Config: `{url: "...", transport: "sse"|"streamableHttp", auth_token: "..."}`
  - Uses `mcp_proxy.py` to bridge remote protocols to stdio

## Development Commands

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run server locally (port 8080)
python server.py

# Test health endpoint
curl http://localhost:8080/health

# Test with OAuth credentials
curl -X POST http://localhost:8080/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"oauth_credentials": {...}, "messages": [...]}'
```

### Docker Testing

```bash
# Build image
docker build -t claude-wrapper-secure .

# Run container
docker run -p 8080:8080 claude-wrapper-secure

# Test
curl http://localhost:8080/health
```

## Deployment (GCP Cloud Run)

### Quick Deploy

```bash
# Build and deploy in one command (increments version tag)
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v9 --project=claude-476509 && \
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v9 \
  --project=claude-476509 \
  --region=europe-west1 \
  --platform=managed
```

### Configuration

- **Project**: `claude-476509`
- **Service**: `claude-wrapper-secure`
- **Region**: `europe-west1` (Belgium)
- **Domain**: `wrapper.claude.serenity-system.fr`
- **Resources**: 2 vCPU, 2 Gi RAM, 10 concurrent requests/instance
- **Scaling**: Min 1 instance (always warm), Max 100 instances

### Monitoring

```bash
# View logs (tail mode)
gcloud run services logs tail claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1

# View last 50 log entries
gcloud run services logs read claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1 \
  --limit=50

# Check service status
gcloud run services describe claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1
```

### Rollback

```bash
# List revisions
gcloud run revisions list \
  --service=claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1

# Rollback to specific revision
gcloud run services update-traffic claude-wrapper-secure \
  --to-revisions=claude-wrapper-secure-00009-szv=100 \
  --project=claude-476509 \
  --region=europe-west1
```

## Key Implementation Details

### OAuth Credentials Format

The Claude CLI receives credentials via `--settings` parameter (not files):

```python
{
  "access_token": "sk-ant-oat01-...",     # Required
  "refresh_token": "sk-ant-ort01-...",    # Required
  "expires_at": 1762444195608,            # Unix timestamp (milliseconds)
  "scopes": ["user:inference", "user:profile"],
  "subscription_type": "max"              # Lowercase: "max" or "pro"
}
```

The wrapper passes credentials as JSON string via `--settings '{"credentials": {...}}'` - no temporary files needed.

### Model Selection

Map friendly names to actual model IDs:
- `opus` → `claude-opus-4-20250514`
- `sonnet` → `claude-sonnet-4-5-20250929` (default)
- `haiku` → `claude-3-5-haiku-20241022`

### User Identification

User IDs are derived from SHA256 hash of access token (first 16 chars):
```python
user_id = hashlib.sha256(access_token.encode()).hexdigest()[:16]
```

This ensures consistent workspace paths without storing tokens.

### Settings and MCP Config as JSON Strings

The Claude CLI accepts JSON strings for both settings and MCP config:

```bash
# Credentials via --settings
--settings '{"credentials": {"access_token": "...", ...}}'

# MCP servers via --mcp-config
--mcp-config '{"mcpServers": {"server_name": {...}}}'

# Skip permissions prompt for MCP
--dangerously-skip-permissions
```

No temporary files needed - everything passed as command-line arguments.

## Testing Checklist

When making changes:

1. **Security**: Verify workspace isolation (check permissions, test cross-user access)
2. **Functionality**: Test both streaming and non-streaming responses
3. **Sessions**: Test stateful mode with `session_id`
4. **MCP**: Test local subprocess and remote HTTP/SSE MCP servers
5. **Error Handling**: Test with invalid tokens, malformed requests
6. **Cleanup**: Verify temporary files are deleted and credentials overwritten

## Common Patterns

### Adding New Endpoint

1. Add route in `server.py` with `@app.get()` or `@app.post()`
2. Define Pydantic model for request validation
3. Call `SecureMultiTenantAPI` methods with proper error handling
4. Update API documentation in root endpoint (`GET /`)

### Modifying Security Level

Security levels defined in `SecurityLevel` enum:
- `PARANOID`: Strictest (production public, untrusted users)
- `BALANCED`: Recommended (production standard) - **current default**
- `DEVELOPER`: Relaxed (development/staging only)

Change in `server.py` initialization:
```python
api = SecureMultiTenantAPI(
    workspaces_root="/workspaces",
    security_level=SecurityLevel.BALANCED  # Modify here
)
```

### Adding MCP Server Support

1. Update `MCPServerConfig` dataclass for new transport types
2. Update validation in `MCPServer` Pydantic model
3. If remote transport, ensure `mcp_proxy.py` supports the protocol
4. Update documentation in root endpoint

## Important Notes

- **Claude CLI Required**: The Dockerfile installs Claude CLI during build. It must be in PATH.
- **Node.js Required**: Claude CLI is distributed as npm package, needs Node 20+
- **Non-root User**: Container runs as `appuser` (UID 1000) for security
- **Stateless vs Stateful**: For conversations >15 turns, stateful mode is mandatory (automatic compacting prevents context limit errors)
- **Version Tags**: Use sequential tags (v8, v9, v10...) for deployments to track rollback points
- **No API Key Support**: This wrapper only supports OAuth tokens from claude.ai accounts (not Anthropic API keys)

## Documentation

- **Live API Docs**: `GET https://wrapper.claude.serenity-system.fr/` (comprehensive auto-generated docs)
- **Swagger UI**: `https://wrapper.claude.serenity-system.fr/docs`
- **README.md**: Project overview and research documentation (OAuth reverse engineering)
- **QUICK_START.md**: Usage examples
- **.claude/CLAUDE.md**: Deployment and infrastructure guide

## Files to Review

For understanding the system:
1. `server.py` - API endpoints and request handling
2. `claude_oauth_api_secure_multitenant.py` - Core security and isolation logic
3. `mcp_proxy.py` - MCP protocol bridging
4. `Dockerfile` - Container setup and dependencies

For deployment:
1. `.claude/CLAUDE.md` - Full deployment guide
2. `deploy.sh` - Helper script (if exists)
3. `requirements.txt` - Python dependencies (FastAPI, uvicorn, pydantic)
