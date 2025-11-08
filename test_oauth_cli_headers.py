#!/usr/bin/env python3
"""Test OAuth avec TOUS les headers CLI exacts"""

import requests
import json
from pathlib import Path

def test_oauth_with_cli_headers():
    """Test simple avec headers CLI complets"""
    print("🧪 Test OAuth avec Headers CLI Exacts")
    print("=" * 50)

    # Lire token OAuth
    creds_path = Path.home() / ".claude" / ".credentials.json"
    creds = json.loads(creds_path.read_text())
    access_token = creds["claudeAiOauth"]["accessToken"]
    print(f"✅ Token OAuth: {access_token[:30]}...")

    # Headers EXACTS from CLI capture
    headers = {
        "accept": "application/json",
        "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14,fine-grained-tool-streaming-2025-05-14,token-counting-2024-11-01",
        "anthropic-dangerous-direct-browser-access": "true",
        "anthropic-version": "2023-06-01",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "user-agent": "claude-cli/2.0.33 (external, cli)",
        "x-app": "cli",
        "x-stainless-arch": "x64",
        "x-stainless-lang": "js",
        "x-stainless-os": "Linux",
        "x-stainless-package-version": "0.66.0",
        "x-stainless-retry-count": "0",
        "x-stainless-runtime": "node",
        "x-stainless-runtime-version": "v24.3.0"
    }

    # Payload simple
    payload = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 100,
        "messages": [{
            "role": "user",
            "content": "Say 'OAuth works!' if you can read this."
        }]
    }

    print("\n🚀 Test requête simple avec headers CLI...")

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"\n📊 Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCÈS: OAuth fonctionne avec headers CLI !")
            print(f"Réponse: {result['content'][0]['text']}")
            print(f"Usage: input={result['usage']['input_tokens']}, output={result['usage']['output_tokens']}")
            return True
        else:
            error = response.json()
            print(f"❌ Échec: {response.status_code}")
            print(f"Erreur: {json.dumps(error, indent=2)}")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    result = test_oauth_with_cli_headers()
    print("\n" + "=" * 50)
    if result:
        print("✅ OAuth SUPPORTÉ avec headers CLI")
        print("🎯 Conclusion: oauth-2025-04-20 beta flag débloque OAuth")
    else:
        print("❌ OAuth NON SUPPORTÉ même avec headers CLI")
        print("🎯 Conclusion: OAuth exclusif à Claude CLI (endpoint/gateway différent)")
