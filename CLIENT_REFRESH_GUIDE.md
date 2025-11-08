# Client OAuth Token Refresh Guide

This guide explains how to properly manage OAuth token refresh when using the Claude Wrapper API.

## Overview

The wrapper is **stateless** and does NOT:
- ❌ Store OAuth credentials
- ❌ Refresh expired tokens automatically
- ❌ Persist refreshed tokens

**You (the client) are responsible for**:
- ✅ Checking token expiration before each request
- ✅ Refreshing tokens via Anthropic's OAuth endpoint
- ✅ Storing new credentials securely
- ✅ Sending fresh credentials to the wrapper

## Token Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│ Client Application                                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  1. Check if token expires soon                          │
│     ↓                                                     │
│  2. If yes: Call Anthropic refresh endpoint              │
│     ↓                                                     │
│  3. Save new tokens (access + refresh) to DB             │
│     ↓                                                     │
│  4. Call wrapper with fresh credentials                  │
│                                                           │
└─────────────────────────────────────────────────────────┘
                            ↓
                ┌───────────────────────┐
                │ Wrapper (Stateless)   │
                │ - Creates workspace   │
                │ - Runs Claude CLI     │
                │ - Destroys workspace  │
                └───────────────────────┘
```

## Anthropic OAuth Refresh Endpoint

### Request

```http
POST https://api.claude.ai/api/auth/oauth/token
Content-Type: application/json

{
  "grant_type": "refresh_token",
  "refresh_token": "sk-ant-ort01-..."
}
```

### Response

```json
{
  "access_token": "sk-ant-oat01-NEW...",
  "refresh_token": "sk-ant-ort01-NEW...",
  "expires_at": 1762618418009,
  "expires_in": 86400,
  "token_type": "Bearer",
  "scopes": ["user:inference", "user:profile"],
  "subscription_type": "max"
}
```

**⚠️ CRITICAL**: Both `access_token` AND `refresh_token` are updated! You MUST save both.

## Implementation Examples

### JavaScript/TypeScript (Node.js or Browser)

```javascript
class ClaudeOAuthClient {
  constructor(credentials, storage) {
    this.credentials = credentials;
    this.storage = storage; // DB, localStorage, etc.
    this.wrapperUrl = 'https://wrapper.claude.serenity-system.fr';
  }

  /**
   * Check if token expires in less than 5 minutes
   */
  isTokenExpiringSoon() {
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;
    return this.credentials.expiresAt < (now + fiveMinutes);
  }

  /**
   * Refresh OAuth token via Anthropic API
   */
  async refreshToken() {
    const response = await fetch('https://api.claude.ai/api/auth/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grant_type: 'refresh_token',
        refresh_token: this.credentials.refreshToken
      })
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token refresh failed: ${error}`);
    }

    const newTokens = await response.json();

    // Update credentials (BOTH tokens change!)
    this.credentials = {
      accessToken: newTokens.access_token,
      refreshToken: newTokens.refresh_token,
      expiresAt: newTokens.expires_at,
      scopes: newTokens.scopes || this.credentials.scopes,
      subscriptionType: newTokens.subscription_type || this.credentials.subscriptionType
    };

    // Save to storage
    await this.storage.saveCredentials(this.credentials);

    console.log('✅ Token refreshed successfully');
    return this.credentials;
  }

  /**
   * Send message to Claude via wrapper
   */
  async sendMessage(messages, options = {}) {
    // ALWAYS check and refresh if needed
    if (this.isTokenExpiringSoon()) {
      console.log('🔄 Token expiring soon, refreshing...');
      await this.refreshToken();
    }

    const response = await fetch(`${this.wrapperUrl}/v1/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        oauth_credentials: {
          access_token: this.credentials.accessToken,
          refresh_token: this.credentials.refreshToken,
          expires_at: this.credentials.expiresAt,
          scopes: this.credentials.scopes,
          subscription_type: this.credentials.subscriptionType
        },
        messages: messages,
        model: options.model || 'sonnet',
        stream: options.stream || false,
        session_id: options.sessionId,
        mcp_servers: options.mcpServers
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Wrapper request failed: ${JSON.stringify(error)}`);
    }

    return response.json();
  }
}

// Usage example
const storage = {
  async saveCredentials(creds) {
    // Save to database
    await db.users.updateOne(
      { userId: currentUser.id },
      { $set: { claudeCredentials: creds } }
    );
  }
};

const client = new ClaudeOAuthClient({
  accessToken: 'sk-ant-oat01-...',
  refreshToken: 'sk-ant-ort01-...',
  expiresAt: 1762532018009,
  scopes: ['user:inference', 'user:profile'],
  subscriptionType: 'max'
}, storage);

// Send message (automatic refresh if needed)
const response = await client.sendMessage([
  { role: 'user', content: 'Hello Claude!' }
]);
console.log(response.content[0].text);
```

### Python

```python
import time
import requests
from typing import Dict, Any, Optional

class ClaudeOAuthClient:
    def __init__(self, credentials: Dict[str, Any], storage):
        self.credentials = credentials
        self.storage = storage
        self.wrapper_url = 'https://wrapper.claude.serenity-system.fr'

    def is_token_expiring_soon(self) -> bool:
        """Check if token expires in less than 5 minutes"""
        now_ms = int(time.time() * 1000)
        five_minutes_ms = 5 * 60 * 1000
        return self.credentials['expires_at'] < (now_ms + five_minutes_ms)

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh OAuth token via Anthropic API"""
        response = requests.post(
            'https://api.claude.ai/api/auth/oauth/token',
            json={
                'grant_type': 'refresh_token',
                'refresh_token': self.credentials['refresh_token']
            }
        )
        response.raise_for_status()

        new_tokens = response.json()

        # Update credentials (BOTH tokens change!)
        self.credentials = {
            'access_token': new_tokens['access_token'],
            'refresh_token': new_tokens['refresh_token'],
            'expires_at': new_tokens['expires_at'],
            'scopes': new_tokens.get('scopes', self.credentials['scopes']),
            'subscription_type': new_tokens.get('subscription_type', self.credentials['subscription_type'])
        }

        # Save to storage
        self.storage.save_credentials(self.credentials)

        print('✅ Token refreshed successfully')
        return self.credentials

    def send_message(
        self,
        messages: list,
        model: str = 'sonnet',
        stream: bool = False,
        session_id: Optional[str] = None,
        mcp_servers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send message to Claude via wrapper"""
        # ALWAYS check and refresh if needed
        if self.is_token_expiring_soon():
            print('🔄 Token expiring soon, refreshing...')
            self.refresh_token()

        response = requests.post(
            f'{self.wrapper_url}/v1/messages',
            json={
                'oauth_credentials': {
                    'access_token': self.credentials['access_token'],
                    'refresh_token': self.credentials['refresh_token'],
                    'expires_at': self.credentials['expires_at'],
                    'scopes': self.credentials['scopes'],
                    'subscription_type': self.credentials['subscription_type']
                },
                'messages': messages,
                'model': model,
                'stream': stream,
                'session_id': session_id,
                'mcp_servers': mcp_servers
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
from my_db import UserStorage

storage = UserStorage(user_id='abc123')
client = ClaudeOAuthClient({
    'access_token': 'sk-ant-oat01-...',
    'refresh_token': 'sk-ant-ort01-...',
    'expires_at': 1762532018009,
    'scopes': ['user:inference', 'user:profile'],
    'subscription_type': 'max'
}, storage)

# Send message (automatic refresh if needed)
response = client.send_message([
    {'role': 'user', 'content': 'Hello Claude!'}
])
print(response['content'][0]['text'])
```

### PHP

```php
<?php

class ClaudeOAuthClient {
    private array $credentials;
    private object $storage;
    private string $wrapperUrl = 'https://wrapper.claude.serenity-system.fr';

    public function __construct(array $credentials, object $storage) {
        $this->credentials = $credentials;
        $this->storage = $storage;
    }

    public function isTokenExpiringSoon(): bool {
        $nowMs = round(microtime(true) * 1000);
        $fiveMinutesMs = 5 * 60 * 1000;
        return $this->credentials['expires_at'] < ($nowMs + $fiveMinutesMs);
    }

    public function refreshToken(): array {
        $response = file_get_contents(
            'https://api.claude.ai/api/auth/oauth/token',
            false,
            stream_context_create([
                'http' => [
                    'method' => 'POST',
                    'header' => 'Content-Type: application/json',
                    'content' => json_encode([
                        'grant_type' => 'refresh_token',
                        'refresh_token' => $this->credentials['refresh_token']
                    ])
                ]
            ])
        );

        $newTokens = json_decode($response, true);

        // Update credentials (BOTH tokens change!)
        $this->credentials = [
            'access_token' => $newTokens['access_token'],
            'refresh_token' => $newTokens['refresh_token'],
            'expires_at' => $newTokens['expires_at'],
            'scopes' => $newTokens['scopes'] ?? $this->credentials['scopes'],
            'subscription_type' => $newTokens['subscription_type'] ?? $this->credentials['subscription_type']
        ];

        // Save to storage
        $this->storage->saveCredentials($this->credentials);

        error_log('✅ Token refreshed successfully');
        return $this->credentials;
    }

    public function sendMessage(
        array $messages,
        string $model = 'sonnet',
        bool $stream = false,
        ?string $sessionId = null,
        ?array $mcpServers = null
    ): array {
        // ALWAYS check and refresh if needed
        if ($this->isTokenExpiringSoon()) {
            error_log('🔄 Token expiring soon, refreshing...');
            $this->refreshToken();
        }

        $response = file_get_contents(
            "{$this->wrapperUrl}/v1/messages",
            false,
            stream_context_create([
                'http' => [
                    'method' => 'POST',
                    'header' => 'Content-Type: application/json',
                    'content' => json_encode([
                        'oauth_credentials' => [
                            'access_token' => $this->credentials['access_token'],
                            'refresh_token' => $this->credentials['refresh_token'],
                            'expires_at' => $this->credentials['expires_at'],
                            'scopes' => $this->credentials['scopes'],
                            'subscription_type' => $this->credentials['subscription_type']
                        ],
                        'messages' => $messages,
                        'model' => $model,
                        'stream' => $stream,
                        'session_id' => $sessionId,
                        'mcp_servers' => $mcpServers
                    ])
                ]
            ])
        );

        return json_decode($response, true);
    }
}

// Usage
$storage = new DatabaseStorage($userId);
$client = new ClaudeOAuthClient([
    'access_token' => 'sk-ant-oat01-...',
    'refresh_token' => 'sk-ant-ort01-...',
    'expires_at' => 1762532018009,
    'scopes' => ['user:inference', 'user:profile'],
    'subscription_type' => 'max'
], $storage);

$response = $client->sendMessage([
    ['role' => 'user', 'content' => 'Hello Claude!']
]);
echo $response['content'][0]['text'];
```

## Security Best Practices

### 1. Store Tokens Securely

**Backend (Recommended)**:
```javascript
// Store in encrypted database
const encryptedToken = encrypt(credentials.refreshToken, SECRET_KEY);
await db.users.updateOne(
  { userId: user.id },
  { $set: { encryptedRefreshToken: encryptedToken } }
);
```

**Frontend (Avoid if possible)**:
```javascript
// If you MUST store on frontend, use httpOnly cookies
// Never store in localStorage (XSS risk)
document.cookie = `refresh_token=${token}; Secure; HttpOnly; SameSite=Strict`;
```

### 2. Handle Refresh Failures

```javascript
async refreshToken() {
  try {
    // Attempt refresh
    const response = await fetch('https://api.claude.ai/api/auth/oauth/token', {
      method: 'POST',
      body: JSON.stringify({
        grant_type: 'refresh_token',
        refresh_token: this.credentials.refreshToken
      })
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Refresh token invalid → user must re-authenticate
        throw new Error('REAUTH_REQUIRED');
      }
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error.message === 'REAUTH_REQUIRED') {
      // Redirect user to OAuth flow
      window.location.href = '/login/claude';
    }
    throw error;
  }
}
```

### 3. Implement Retry Logic

```javascript
async sendMessage(messages, retries = 1) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (this.isTokenExpiringSoon()) {
        await this.refreshToken();
      }

      return await this._callWrapper(messages);
    } catch (error) {
      if (error.message.includes('Invalid API key') && attempt < retries) {
        // Token might have expired between check and call
        console.log('🔄 Retry with fresh token...');
        await this.refreshToken();
        continue;
      }
      throw error;
    }
  }
}
```

## Common Issues

### Issue 1: "Invalid API key" despite fresh token

**Cause**: Token refreshed between expiration check and wrapper call (race condition)

**Solution**: Implement retry logic (see above)

### Issue 2: Refresh token expired

**Cause**: User hasn't used the app in >90 days (typical refresh token lifetime)

**Solution**: Redirect user to re-authenticate via OAuth flow

### Issue 3: Both tokens not saved

**Cause**: Only saving `access_token`, forgetting `refresh_token` also changes

**Solution**: Always save BOTH tokens from refresh response

## Testing

Test your refresh implementation:

```bash
# 1. Set token to expire in 1 minute
credentials.expiresAt = Date.now() + 60000

# 2. Wait 30 seconds, send message
await sleep(30000)
await client.sendMessage([...])  # Should auto-refresh

# 3. Verify new tokens saved
const saved = await storage.loadCredentials()
assert(saved.accessToken !== oldAccessToken)
assert(saved.refreshToken !== oldRefreshToken)
```

## Support

For issues or questions:
- GitHub: https://github.com/your-repo/wrapper-claude
- Email: support@example.com

## References

- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [Anthropic OAuth Documentation](https://docs.anthropic.com/oauth) (if available)
- [Wrapper API Documentation](https://wrapper.claude.serenity-system.fr/)
