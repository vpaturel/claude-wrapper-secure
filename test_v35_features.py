#!/usr/bin/env python3
"""
Test script for v35 features: Extended Thinking & Fallback Model
"""
import sys
sys.path.insert(0, '/home/tincenv/wrapper-claude')

from claude_oauth_api_secure_multitenant import SecureMultiTenantAPI, UserOAuthCredentials
import json

# Your credentials
credentials = UserOAuthCredentials(
    access_token="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",
    refresh_token="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",
    expires_at=1762671773363,
    scopes=["user:inference", "user:profile"],
    subscription_type="max"
)

# Initialize API
api = SecureMultiTenantAPI(workspaces_root="/tmp/test_workspaces_v35")

print("=" * 80)
print("TEST 1: Extended Thinking")
print("=" * 80)
print("Prompt: Complex reasoning task (should trigger thinking mode)")
print()

# Test Extended Thinking
thinking_config = {
    "type": "enabled",
    "budget_tokens": 3000
}

messages_thinking = [
    {
        "role": "user",
        "content": "Solve this logic puzzle: You have 12 balls. One is heavier or lighter than the others (you don't know which). You have a balance scale. What's the MINIMUM number of weighings needed to identify the odd ball AND determine if it's heavier or lighter? Explain your reasoning step by step."
    }
]

try:
    print("Calling API with Extended Thinking (budget: 3000 tokens)...")
    response = api.create_message(
        oauth_credentials=credentials,
        messages=messages_thinking,
        model="sonnet",
        thinking=thinking_config,
        timeout=120
    )

    print("\n✅ Response received:")
    print(f"Type: {response.get('type', 'unknown')}")
    if 'content' in response:
        content_text = response['content'][0]['text'] if response['content'] else 'No content'
        print(f"Content length: {len(content_text)} chars")
        print(f"First 500 chars:\n{content_text[:500]}...")
    else:
        print(f"Full response: {json.dumps(response, indent=2)}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 2: Fallback Model")
print("=" * 80)
print("Primary: sonnet, Fallback: haiku")
print("Note: Fallback only triggers if sonnet returns 529 (overloaded)")
print()

messages_simple = [
    {"role": "user", "content": "What is 2+2? Answer in one word."}
]

try:
    print("Calling API with Fallback Model...")
    response = api.create_message(
        oauth_credentials=credentials,
        messages=messages_simple,
        model="sonnet",
        fallback_model="haiku",
        timeout=60
    )

    print("\n✅ Response received:")
    print(f"Type: {response.get('type', 'unknown')}")
    if 'content' in response:
        content_text = response['content'][0]['text'] if response['content'] else 'No content'
        print(f"Response: {content_text}")
        print(f"Model used: {response.get('model', 'unknown')}")
    else:
        print(f"Full response: {json.dumps(response, indent=2)}")

    print("\n⚠️ Note: Fallback to haiku only happens if sonnet is overloaded (529)")
    print("If you see sonnet response, it means sonnet was available (normal behavior)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 3: Both features combined")
print("=" * 80)

messages_combined = [
    {
        "role": "user",
        "content": "Write a Python function to check if a number is prime. Use extended thinking to consider edge cases."
    }
]

try:
    print("Calling API with Extended Thinking + Fallback Model...")
    response = api.create_message(
        oauth_credentials=credentials,
        messages=messages_combined,
        model="sonnet",
        fallback_model="haiku",
        thinking={"type": "enabled", "budget_tokens": 2000},
        timeout=120
    )

    print("\n✅ Response received:")
    if 'content' in response:
        content_text = response['content'][0]['text'] if response['content'] else 'No content'
        print(f"Content length: {len(content_text)} chars")
        print(f"First 300 chars:\n{content_text[:300]}...")
    else:
        print(f"Full response: {json.dumps(response, indent=2)}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Tests completed!")
print("=" * 80)
