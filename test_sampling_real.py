#!/usr/bin/env python3
"""
Test REAL usage of sampling parameters by Claude CLI
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

# Patch create_message to add sampling params
import types
import subprocess
from pathlib import Path

def create_message_with_sampling(self, oauth_credentials, messages, model="sonnet", timeout=120, **kwargs):
    """Modified create_message that accepts sampling params"""
    user_id = self._get_user_id_from_token(oauth_credentials.access_token)
    user_workspace = self._setup_user_workspace(user_id)

    claude_dir = user_workspace / ".claude"
    claude_dir.mkdir(mode=0o700, exist_ok=True)

    # Build command
    cmd = [self.claude_bin, "--print"]

    # Model
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-5-20250929",
        "haiku": "claude-3-5-haiku-20241022"
    }
    cmd.extend(["--model", model_map.get(model, model)])

    # Build settings with credentials + sampling params
    settings = {
        "credentials": {
            "access_token": oauth_credentials.access_token,
            "refresh_token": oauth_credentials.refresh_token,
            "expires_at": oauth_credentials.expires_at,
            "scopes": oauth_credentials.scopes,
            "subscription_type": oauth_credentials.subscription_type
        }
    }

    # Add sampling params if provided
    for key in ['temperature', 'top_p', 'top_k', 'max_tokens', 'stop_sequences']:
        if key in kwargs:
            settings[key] = kwargs[key]

    settings_json = json.dumps(settings)
    cmd.extend(["--settings", settings_json])

    # Build prompt
    prompt_parts = []
    for msg in messages:
        content = msg.get("content", "")
        prompt_parts.append(content)

    prompt = "\n\n".join(prompt_parts)
    cmd.append(prompt)

    # Execute
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=user_workspace,
        timeout=timeout
    )

    if result.returncode != 0:
        raise Exception(f"CLI error: {result.stderr}")

    try:
        response_data = json.loads(result.stdout.strip())
        return response_data
    except:
        return {
            "type": "message",
            "content": [{"type": "text", "text": result.stdout.strip()}]
        }

api = SecureMultiTenantAPI(workspaces_root="/tmp/test_sampling_real")
api.create_message = types.MethodType(create_message_with_sampling, api)

print("=" * 80)
print("TEST 1: max_tokens (should truncate response)")
print("=" * 80)

try:
    response = api.create_message(
        oauth_credentials=credentials,
        messages=[{"role": "user", "content": "Write a long story about a cat. Make it at least 200 words."}],
        model="sonnet",
        max_tokens=50,  # Should cut response at ~50 tokens (~37 words)
        timeout=60
    )

    content = response['content'][0]['text']
    word_count = len(content.split())

    print(f"✅ Response received")
    print(f"📊 Word count: {word_count} words")
    print(f"📊 Char count: {len(content)} chars")
    print(f"Response:\n{content}\n")

    if word_count < 60:
        print("✅ max_tokens WORKS (response was truncated)")
    else:
        print("❌ max_tokens NOT working (response too long)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 2: stop_sequences (should stop at '!')")
print("=" * 80)

try:
    response = api.create_message(
        oauth_credentials=credentials,
        messages=[{"role": "user", "content": "Say 'Hello! How are you? I am fine.' exactly."}],
        model="sonnet",
        stop_sequences=["!"],  # Should stop after "Hello!"
        timeout=60
    )

    content = response['content'][0]['text']
    print(f"✅ Response received")
    print(f"Response: '{content}'")

    if "!" not in content or content.count("!") == 0:
        print("✅ stop_sequences WORKS (stopped before '!')")
    elif len(content) < 20:
        print("✅ stop_sequences WORKS (response truncated early)")
    else:
        print("❌ stop_sequences NOT working (full response)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 3: temperature (determinism check)")
print("=" * 80)
print("Running same prompt 3 times with temperature=0.0 (should be identical)")

try:
    responses = []
    for i in range(3):
        response = api.create_message(
            oauth_credentials=credentials,
            messages=[{"role": "user", "content": "Pick a random number between 1 and 100"}],
            model="sonnet",
            temperature=0.0,  # Should always give same answer
            timeout=60
        )
        content = response['content'][0]['text']
        responses.append(content)
        print(f"  Response {i+1}: {content}")

    if responses[0] == responses[1] == responses[2]:
        print("\n✅ temperature=0.0 WORKS (all responses identical)")
    else:
        print("\n❌ temperature=0.0 NOT working (responses differ)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 4: temperature=1.5 (high creativity)")
print("=" * 80)
print("Running same prompt 3 times with temperature=1.5 (should vary)")

try:
    responses = []
    for i in range(3):
        response = api.create_message(
            oauth_credentials=credentials,
            messages=[{"role": "user", "content": "Pick a random number between 1 and 100"}],
            model="sonnet",
            temperature=1.5,  # Should give different answers
            timeout=60
        )
        content = response['content'][0]['text']
        responses.append(content)
        print(f"  Response {i+1}: {content}")

    unique_responses = len(set(responses))
    if unique_responses > 1:
        print(f"\n✅ temperature=1.5 WORKS ({unique_responses}/3 responses unique)")
    else:
        print("\n⚠️ temperature=1.5 unclear (all responses identical - could be chance)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Tests completed!")
print("=" * 80)
