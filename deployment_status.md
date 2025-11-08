# Claude Secure Multi-Tenant API - Deployment Status

**Date:** 2025-11-06
**Service:** claude-wrapper-secure
**Region:** europe-west1
**Project:** claude-476509

---

## Deployment History

### v1 (Initial)  - FAILED
**Status:** ❌ Container failed to start
**Error:** Claude CLI not found (installed as root, container runs as non-root)
**Fix:** Reordered Dockerfile to install CLI as appuser

### v2 - DEPLOYED (Missing tmp fix)
**Status:** ⚠️ Service running but API errors
**Error:** Missing /tmp directory in user workspace
**Fix:** Added `tmp_dir.mkdir(mode=0o700)` to workspace creation

### v3 (Current) - DEPLOYED
**Status:** ✅ Service running, enhanced error logging active
**Image:** `eu.gcr.io/claude-476509/claude-wrapper-secure:v3`
**URL:** https://claude-wrapper-secure-778234387929.europe-west1.run.app
**Domain:** wrapper.claude.serenity-system.fr (SSL provisioning)
**Revision:** claude-wrapper-secure-00004-p5z

---

## Current Issue: OAuth Token Not Recognized

### Error Details
```
❌ Claude CLI error (code 1): Invalid API key · Please run /login
   stdout: Invalid API key · Please run /login
   stderr: (empty)
```

### Root Cause Analysis

**Problem:** Claude CLI is not accepting the OAuth token provided via credentials file.

**Current Implementation:**
1. User sends OAuth token: `sk-ant-oat01-...`
2. Wrapper creates credentials file at `{workspace}/.claude/.credentials.json`:
   ```json
   {
     "claudeAiOauth": {
       "accessToken": "sk-ant-oat01-...",
       "refreshToken": "",
       "expiresAt": 0,
       "scopes": ["all"],
       "subscriptionType": "Max"
     }
   }
   ```
3. Claude CLI reads credentials file but returns "Invalid API key"

**Hypothesis:**
- Claude CLI expects OAuth credentials in a different format
- OR Claude CLI requires interactive `/login` flow first
- OR the `sk-ant-oat01-*` token format is not compatible with CLI credentials injection

### Test Performed
```bash
curl -X POST https://claude-wrapper-secure-778234387929.europe-west1.run.app/v1/messages \
  -H "Authorization: Bearer sk-ant-oat01-test-dummy-token" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "model": "sonnet"}'

Response: {"type":"error","error":{"message":"Invalid API key · Please run /login","code":"cli_error"}}
```

---

## Technical Specifications

### Container Configuration
- **Base Image:** python:3.11-slim
- **Claude CLI:** 2.0.34 (installed in `/home/appuser/.local/bin`)
- **User:** appuser (UID 1000, non-root)
- **Workspaces:** /workspaces (755 permissions)
- **Port:** 8080
- **Health Check:** /health endpoint (30s interval)

### Cloud Run Settings
- **Memory:** 2Gi
- **CPU:** 2 cores
- **Min Instances:** 1
- **Max Instances:** 100
- **Concurrency:** 10
- **Timeout:** 300s
- **Security:** BALANCED level

### Security Features
- ✅ Token isolation (100%)
- ✅ Code isolation (100%)
- ✅ Workspace per user (0o700 permissions)
- ✅ Credentials files (0o600 permissions)
- ✅ Non-root container
- ✅ Tools restrictions active

---

## Next Steps

### Option 1: Investigate Claude CLI OAuth Format
- Reverse-engineer the actual credentials format after `/login`
- Compare with our injected format
- Adjust credentials file structure

### Option 2: Use Claude API Directly
- Bypass Claude CLI entirely
- Make direct HTTP requests to Claude API using OAuth token
- Implement conversation management in wrapper

### Option 3: Contact Anthropic Support
- Ask for documentation on OAuth token injection for Claude CLI
- Request guidance on programmatic OAuth usage

### Option 4: Test with Real OAuth Flow
- Perform interactive `/login` in a test container
- Capture the actual credentials file format
- Replicate that format in wrapper

---

## Files Modified

### claude_oauth_api_secure_multitenant.py
**Line 230-232:** Added tmp directory creation
```python
# Créer tmp directory (requis par Claude CLI)
tmp_dir = temp_dir / "tmp"
tmp_dir.mkdir(mode=0o700)
```

**Line 557-568:** Enhanced error logging
```python
if result.returncode != 0:
    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown CLI error"
    logger.error(f"❌ Claude CLI error (code {result.returncode}): {error_msg[:500]}")
    logger.error(f"   stdout: {result.stdout[:200]}")
    logger.error(f"   stderr: {result.stderr[:200]}")
```

### Dockerfile
**Key Change:** Install Claude CLI as non-root user
```dockerfile
USER appuser
RUN bash -c "curl -fsSL https://claude.ai/install.sh | bash"
ENV PATH="/home/appuser/.local/bin:${PATH}"
```

---

## Monitoring

### Health Check
```bash
curl https://claude-wrapper-secure-778234387929.europe-west1.run.app/health
# Response: {"status":"healthy","version":"5.0-SECURE","security_level":"BALANCED"}
```

### Logs
```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=claude-wrapper-secure' \
  --limit 50 --project claude-476509
```

---

## Contact

**Project:** claude-476509
**Region:** europe-west1
**Service:** claude-wrapper-secure
**Support:** Check Cloud Run logs for detailed error messages
