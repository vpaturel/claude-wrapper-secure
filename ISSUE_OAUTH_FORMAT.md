# Issue: OAuth Credentials Format Mismatch

**Date:** 2025-11-06
**Status:** ROOT CAUSE IDENTIFIED ✅

---

## Problem Summary

Claude CLI returns: **"Invalid API key · Please run /login"**

This occurs because the wrapper is creating credentials with **incomplete OAuth data**.

---

## Root Cause

### Real OAuth Credentials Format (Working)
After `/login`, Claude CLI stores:
```json
{
  "claudeAiOauth": {
    "accessToken": "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",
    "refreshToken": "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",
    "expiresAt": 1762444195608,
    "scopes": ["user:inference", "user:profile"],
    "subscriptionType": "max"
  }
}
```

### Wrapper's Current Format (Broken)
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "",                    // ❌ EMPTY
    "expiresAt": 0,                        // ❌ ZERO
    "scopes": ["all"],                     // ❌ WRONG
    "subscriptionType": "Max"              // ❌ WRONG CASE
  }
}
```

---

## Critical Differences

| Field | Real Value | Wrapper Value | Impact |
|-------|------------|---------------|---------|
| `refreshToken` | `sk-ant-ort01-...` | `""` (empty) | ❌ **CRITICAL** - CLI needs refresh token |
| `expiresAt` | `1762444195608` | `0` | ⚠️ **HIGH** - Token appears expired |
| `scopes` | `["user:inference", "user:profile"]` | `["all"]` | ⚠️ **MEDIUM** - Invalid scopes |
| `subscriptionType` | `"max"` | `"Max"` | ⚠️ **LOW** - Case mismatch |

---

## Why It Fails

1. **Claude CLI validates refresh token**: Without a valid refresh token (sk-ant-ort01-*), CLI rejects authentication
2. **Expired timestamp**: `expiresAt: 0` indicates token is expired since epoch
3. **Invalid scopes**: CLI expects specific scopes like "user:inference", not generic "all"
4. **Case sensitivity**: "Max" vs "max" may cause validation failures

---

## Solution Options

### Option 1: Require Both Tokens (RECOMMENDED)
**Modify API to accept both access + refresh tokens:**

**API Request Format:**
```json
{
  "oauth_credentials": {
    "access_token": "sk-ant-oat01-...",
    "refresh_token": "sk-ant-ort01-...",  // NEW: Required
    "expires_at": 1762444195608,           // NEW: Real timestamp
    "scopes": ["user:inference", "user:profile"],  // NEW: Real scopes
    "subscription_type": "max"             // lowercase
  },
  "messages": [...]
}
```

**Pros:**
- ✅ Works exactly like real Claude CLI
- ✅ Supports token refresh automatically
- ✅ Full OAuth flow compatibility

**Cons:**
- ⚠️ Breaking API change (requires all users to provide refresh token)
- ⚠️ Users need to extract refresh token from their OAuth flow

---

### Option 2: Token Exchange Service
**Create a service to exchange access tokens for full OAuth credentials:**

1. User provides only access token
2. Wrapper calls internal service to get refresh token + metadata
3. Service stores mapping: access_token → full_credentials

**Pros:**
- ✅ Simpler user API (only access token needed)
- ✅ Centralized token management

**Cons:**
- ❌ Requires additional infrastructure
- ❌ Security risk (storing refresh tokens centrally)
- ❌ Complex implementation

---

### Option 3: Use Anthropic API Directly (ALTERNATIVE)
**Bypass Claude CLI entirely:**

- Make direct HTTP requests to Anthropic API
- Use access token in Authorization header
- Implement conversation management in wrapper

**Pros:**
- ✅ No CLI dependency
- ✅ Only access token needed
- ✅ More control over API calls

**Cons:**
- ❌ Major rewrite required
- ❌ Lose Claude CLI features (MCP servers, settings, etc.)
- ❌ More complex implementation

---

## Recommended Fix: Option 1

### Step 1: Update UserOAuthCredentials class
```python
@dataclass
class UserOAuthCredentials:
    """Credentials OAuth d'un utilisateur externe"""
    access_token: str  # sk-ant-oat01-xxx
    refresh_token: str  # sk-ant-ort01-xxx (REQUIRED)
    expires_at: int  # Timestamp milliseconds
    scopes: List[str] = field(default_factory=lambda: ["user:inference", "user:profile"])
    subscription_type: str = "max"  # lowercase!
```

### Step 2: Update API Endpoint
```python
class OAuthCredentialsRequest(BaseModel):
    access_token: str = Field(..., description="OAuth access token (sk-ant-oat01-*)")
    refresh_token: str = Field(..., description="OAuth refresh token (sk-ant-ort01-*)")
    expires_at: int = Field(..., description="Token expiration timestamp (milliseconds)")
    scopes: Optional[List[str]] = Field(default=["user:inference", "user:profile"])
    subscription_type: Optional[str] = Field(default="max")

class MessageRequest(BaseModel):
    oauth_credentials: OAuthCredentialsRequest
    messages: List[Message]
    model: str = "sonnet"
```

### Step 3: Update create_message()
```python
credentials = UserOAuthCredentials(
    access_token=request.oauth_credentials.access_token,
    refresh_token=request.oauth_credentials.refresh_token,
    expires_at=request.oauth_credentials.expires_at,
    scopes=request.oauth_credentials.scopes,
    subscription_type=request.oauth_credentials.subscription_type
)
```

### Step 4: Update Documentation
Inform users they need to provide:
1. Access token (sk-ant-oat01-*)
2. Refresh token (sk-ant-ort01-*)
3. Expiration timestamp
4. Scopes (optional, defaults to ["user:inference", "user:profile"])

---

## Testing Plan

### Test 1: With Real Credentials
```bash
curl -X POST https://claude-wrapper-secure-778234387929.europe-west1.run.app/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {
      "access_token": "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",
      "refresh_token": "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",
      "expires_at": 1762444195608,
      "scopes": ["user:inference", "user:profile"],
      "subscription_type": "max"
    },
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "sonnet"
  }'
```

**Expected:** ✅ Success - Claude responds

---

## Impact Assessment

**Breaking Change:** YES
**Severity:** HIGH
**Migration Required:** YES

**All existing users must:**
1. Update their API calls to include refresh token
2. Provide expiration timestamp
3. Specify scopes (or use defaults)

---

## Alternative: Backward Compatibility

**Support both formats temporarily:**

```python
# Try new format first
if hasattr(request, 'oauth_credentials'):
    # Full OAuth credentials provided
    credentials = UserOAuthCredentials(**request.oauth_credentials.dict())
else:
    # Legacy: only access token in Authorization header
    # WARNING: This will fail with CLI
    credentials = UserOAuthCredentials(
        access_token=oauth_token,
        refresh_token="",  # Will fail
        expires_at=0,
        scopes=["user:inference", "user:profile"],
        subscription_type="max"
    )
```

Return clear error for legacy format:
```json
{
  "error": {
    "code": "incomplete_oauth_credentials",
    "message": "Claude CLI requires both access_token and refresh_token. Please update your request to include full OAuth credentials.",
    "documentation": "https://docs.example.com/oauth-migration"
  }
}
```

---

## Files to Modify

1. **claude_oauth_api_secure_multitenant.py**
   - Line 66-70: Update UserOAuthCredentials defaults
   - Line 484: Update credentials creation

2. **server.py**
   - Lines 53-80: Update MessageRequest model
   - Line 210-217: Update credentials extraction

3. **requirements.txt**
   - No changes needed

4. **Dockerfile**
   - No changes needed

---

## Timeline

1. **Immediate:** Document the issue ✅
2. **Next:** Implement Option 1 (30 min)
3. **Then:** Build and deploy v4 (15 min)
4. **Finally:** Test with real credentials (5 min)

**Total Time:** ~50 minutes

---

## Conclusion

The wrapper is currently **unusable** because it only accepts access tokens, but Claude CLI requires **both access and refresh tokens** to authenticate.

**Action Required:** Implement Option 1 to accept full OAuth credentials, or switch to Option 3 (direct API calls).
