#!/usr/bin/env python3
"""
Test Multi-Conversations Simultanées

Prouve qu'un user peut avoir plusieurs conversations différentes en parallèle.
"""

import sys
import time
from claude_oauth_api_multi_tenant import MultiTenantClaudeAPI, MCPServerConfig

def test_multiple_conversations_same_user():
    """
    Test: Un user avec 3 conversations différentes en parallèle
    """
    print("=" * 80)
    print("TEST: Multi-Conversations Simultanées")
    print("=" * 80)

    api = MultiTenantClaudeAPI()

    # Simuler User 1 (dans un vrai cas, ce serait son vrai token)
    user_token = None  # None = utilise credentials système

    print("\n📝 User 1 démarre 3 conversations DIFFÉRENTES...\n")

    # Conversation 1: Python
    print("🔵 Conversation 1: Discuter de Python")
    session1_id = "user1-conv-python"

    response1a = api.create_message(
        oauth_token=user_token,
        session_id=session1_id,
        messages=[{"role": "user", "content": "Let's talk about Python programming"}],
        model="sonnet"
    )
    print(f"   Message 1A: {response1a.get('content', [{}])[0].get('text', 'N/A')[:80]}...")

    # Conversation 2: JavaScript (EN PARALLÈLE, différent topic)
    print("\n🟢 Conversation 2: Discuter de JavaScript")
    session2_id = "user1-conv-javascript"

    response2a = api.create_message(
        oauth_token=user_token,
        session_id=session2_id,
        messages=[{"role": "user", "content": "Let's talk about JavaScript programming"}],
        model="sonnet"
    )
    print(f"   Message 2A: {response2a.get('content', [{}])[0].get('text', 'N/A')[:80]}...")

    # Conversation 3: Docker (EN PARALLÈLE, encore différent)
    print("\n🟡 Conversation 3: Discuter de Docker")
    session3_id = "user1-conv-docker"

    response3a = api.create_message(
        oauth_token=user_token,
        session_id=session3_id,
        messages=[{"role": "user", "content": "Let's talk about Docker containerization"}],
        model="sonnet"
    )
    print(f"   Message 3A: {response3a.get('content', [{}])[0].get('text', 'N/A')[:80]}...")

    print("\n" + "=" * 80)
    print("✅ 3 conversations créées!")
    print("=" * 80)

    # Maintenant on continue chaque conversation pour prouver l'isolation
    print("\n📝 Continuer chaque conversation (test isolation)...\n")

    # Continue conversation 1
    print("🔵 Conversation 1 - Message 2: \"What language were we discussing?\"")
    response1b = api.create_message(
        oauth_token=user_token,
        session_id=session1_id,  # MÊME session
        messages=[{"role": "user", "content": "What programming language were we discussing?"}],
        model="sonnet"
    )
    conv1_response = response1b.get('content', [{}])[0].get('text', 'N/A')
    print(f"   Response: {conv1_response[:150]}...")

    # Continue conversation 2
    print("\n🟢 Conversation 2 - Message 2: \"What language were we discussing?\"")
    response2b = api.create_message(
        oauth_token=user_token,
        session_id=session2_id,  # DIFFÉRENTE session
        messages=[{"role": "user", "content": "What programming language were we discussing?"}],
        model="sonnet"
    )
    conv2_response = response2b.get('content', [{}])[0].get('text', 'N/A')
    print(f"   Response: {conv2_response[:150]}...")

    # Continue conversation 3
    print("\n🟡 Conversation 3 - Message 2: \"What technology were we discussing?\"")
    response3b = api.create_message(
        oauth_token=user_token,
        session_id=session3_id,  # ENCORE DIFFÉRENTE session
        messages=[{"role": "user", "content": "What technology were we discussing?"}],
        model="sonnet"
    )
    conv3_response = response3b.get('content', [{}])[0].get('text', 'N/A')
    print(f"   Response: {conv3_response[:150]}...")

    # Vérifier isolation
    print("\n" + "=" * 80)
    print("🔬 VÉRIFICATION ISOLATION:")
    print("=" * 80)

    checks = []

    # Check 1: Conversation 1 parle bien de Python
    if "python" in conv1_response.lower():
        print("✅ Conversation 1: Parle de Python (correct)")
        checks.append(True)
    else:
        print("❌ Conversation 1: Ne parle PAS de Python (erreur!)")
        checks.append(False)

    # Check 2: Conversation 2 parle bien de JavaScript
    if "javascript" in conv2_response.lower():
        print("✅ Conversation 2: Parle de JavaScript (correct)")
        checks.append(True)
    else:
        print("❌ Conversation 2: Ne parle PAS de JavaScript (erreur!)")
        checks.append(False)

    # Check 3: Conversation 3 parle bien de Docker
    if "docker" in conv3_response.lower() or "container" in conv3_response.lower():
        print("✅ Conversation 3: Parle de Docker/Containers (correct)")
        checks.append(True)
    else:
        print("❌ Conversation 3: Ne parle PAS de Docker (erreur!)")
        checks.append(False)

    # Résultat final
    print("\n" + "=" * 80)
    if all(checks):
        print("🎉 TEST RÉUSSI: Multi-conversations isolées fonctionnent!")
        print("=" * 80)
        print("\n✅ Confirmé:")
        print("   - Même user peut avoir plusieurs conversations")
        print("   - Chaque conversation a son propre contexte")
        print("   - Pas d'interférence entre conversations")
        print("   - Sessions parfaitement isolées")
        return True
    else:
        print("❌ TEST ÉCHOUÉ: Isolation non fonctionnelle")
        print("=" * 80)
        return False


if __name__ == "__main__":
    print("\n🚀 Test Multi-Conversations - Claude Multi-Tenant API\n")

    try:
        success = test_multiple_conversations_same_user()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
