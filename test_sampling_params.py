#!/usr/bin/env python3
"""
Test sampling parameters: temperature, top_p, top_k, max_tokens, stop_sequences
"""
import sys
sys.path.insert(0, '/home/tincenv/wrapper-claude')

from claude_oauth_api_secure_multitenant import SecureMultiTenantAPI, UserOAuthCredentials
import json

credentials = UserOAuthCredentials(
    access_token="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",
    refresh_token="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",
    expires_at=1762671773363,
    scopes=["user:inference", "user:profile"],
    subscription_type="max"
)

# Mock subprocess to see settings
import subprocess
original_run = subprocess.run

def mock_run(cmd, *args, **kwargs):
    for i, arg in enumerate(cmd):
        if arg == "--settings":
            settings = json.loads(cmd[i+1])
            print(f"\n📋 Settings JSON:")
            print(json.dumps(settings, indent=2))

            # Check sampling params
            sampling_keys = ['temperature', 'top_p', 'top_k', 'max_tokens', 'stop_sequences']
            found = {k: k in settings for k in sampling_keys}
            print(f"\n🔍 Sampling params found:")
            for k, v in found.items():
                status = "✅" if v else "❌"
                print(f"  {status} {k}: {settings.get(k, 'not present')}")
            break

    class FakeResult:
        returncode = 0
        stdout = '{"type":"message","content":[{"type":"text","text":"Test"}]}'
        stderr = ''
    return FakeResult()

subprocess.run = mock_run

api = SecureMultiTenantAPI(workspaces_root="/tmp/test_sampling")

print("=" * 80)
print("TEST: Sampling Parameters via --settings")
print("=" * 80)

# Test sampling params
sampling_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_tokens": 500,
    "stop_sequences": ["---", "END"]
}

# Modify create_message to accept sampling params
import types

def create_message_patched(self, oauth_credentials, messages, model="sonnet", timeout=60, **kwargs):
    # Extract sampling params from kwargs
    sampling_params = {}
    for key in ['temperature', 'top_p', 'top_k', 'max_tokens', 'stop_sequences']:
        if key in kwargs:
            sampling_params[key] = kwargs[key]

    # Call original with modified settings
    user_id = self._get_user_id_from_token(oauth_credentials.access_token)
    user_workspace = self._setup_user_workspace(user_id)

    from pathlib import Path
    claude_dir = user_workspace / ".claude"
    claude_dir.mkdir(mode=0o700, exist_ok=True)

    # Build command
    cmd = [self.claude_bin, "--print", "--model", "claude-sonnet-4-5-20250929"]

    # Build settings with credentials + sampling params
    settings = {
        "credentials": {
            "access_token": oauth_credentials.access_token,
            "refresh_token": oauth_credentials.refresh_token,
            "expires_at": oauth_credentials.expires_at,
            "scopes": oauth_credentials.scopes,
            "subscription_type": oauth_credentials.subscription_type
        },
        **sampling_params  # Add sampling params
    }

    cmd.extend(["--settings", json.dumps(settings)])
    cmd.append("Test prompt")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=user_workspace)
    return {"type": "message", "content": [{"type": "text", "text": result.stdout}]}

# Patch the method
api.create_message = types.MethodType(create_message_patched, api)

try:
    response = api.create_message(
        oauth_credentials=credentials,
        messages=[{"role": "user", "content": "Test"}],
        model="sonnet",
        **sampling_config
    )
    print("\n✅ Test completed")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    subprocess.run = original_run

print("\n" + "=" * 80)
