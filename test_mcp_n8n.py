#!/usr/bin/env python3
"""
Test MCP n8n Integration

Ce script teste l'intégration du wrapper Claude avec un serveur MCP n8n.
n8n peut exposer un serveur MCP pour interagir avec ses workflows.

Prérequis:
1. n8n installé et lancé (https://n8n.io/)
2. Serveur MCP n8n configuré
3. OAuth credentials Claude valides

Types d'intégration supportés:
- MCP Local (subprocess): Si n8n expose un MCP server local
- MCP Remote (HTTP/SSE): Si n8n expose un MCP server distant
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# =============================================================================
# Configuration
# =============================================================================

# URL du wrapper Claude
WRAPPER_URL = "https://wrapper.claude.serenity-system.fr"
# WRAPPER_URL = "http://localhost:8080"  # Pour tests locaux

# Configuration n8n MCP
# Option 1: MCP Local (subprocess)
N8N_MCP_LOCAL = {
    "n8n": {
        "command": "npx",
        "args": ["-y", "@n8n/mcp-server"],
        "env": {
            "N8N_API_KEY": "YOUR_N8N_API_KEY",
            "N8N_HOST": "http://localhost:5678",
            "DEBUG": "true"
        }
    }
}

# Option 2: MCP Remote (HTTP/SSE)
N8N_MCP_REMOTE = {
    "n8n": {
        "url": "https://your-n8n-instance.com/mcp/sse",
        "transport": "sse",
        "auth_type": "bearer",
        "auth_token": "YOUR_N8N_MCP_TOKEN"
    }
}


# =============================================================================
# Fonctions de test
# =============================================================================

def test_health():
    """Test 1: Vérifier que le wrapper est accessible"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)

    try:
        response = requests.get(f"{WRAPPER_URL}/health", timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"✅ Wrapper accessible")
        print(f"   Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Security: {data.get('security_level')}")
        return True

    except Exception as e:
        print(f"❌ Wrapper non accessible: {e}")
        return False


def test_mcp_local(oauth_credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Test 2: Test MCP Local avec n8n"""
    print("\n" + "="*70)
    print("TEST 2: MCP Local n8n (subprocess)")
    print("="*70)

    payload = {
        "oauth_credentials": oauth_credentials,
        "messages": [
            {
                "role": "user",
                "content": """Tu as accès à un serveur MCP n8n.

Liste les workflows disponibles et décris-moi le premier workflow trouvé."""
            }
        ],
        "model": "sonnet",
        "stream": False,
        "mcp_servers": N8N_MCP_LOCAL
    }

    print("📤 Envoi requête avec MCP Local...")
    print(f"   MCP Config: {json.dumps(N8N_MCP_LOCAL, indent=2)}")

    try:
        response = requests.post(
            f"{WRAPPER_URL}/v1/messages",
            json=payload,
            timeout=180
        )
        response.raise_for_status()

        data = response.json()

        if data.get("type") == "error":
            print(f"❌ Erreur API: {data.get('error', {}).get('message')}")
            return data

        # Extraire le texte de la réponse
        content = data.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            print(f"✅ Réponse reçue ({len(text)} chars)")
            print(f"\n📝 Réponse Claude:")
            print("-" * 70)
            print(text[:500] + ("..." if len(text) > 500 else ""))
            print("-" * 70)

        # Statistiques
        usage = data.get("usage", {})
        if usage:
            print(f"\n📊 Usage:")
            print(f"   Input tokens: {usage.get('input_tokens', 0)}")
            print(f"   Output tokens: {usage.get('output_tokens', 0)}")

        return data

    except requests.exceptions.Timeout:
        print("❌ Timeout - le serveur MCP n8n ne répond peut-être pas")
        return {"type": "error", "error": {"message": "Timeout"}}

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP: {e}")
        try:
            error_data = e.response.json()
            print(f"   Detail: {error_data.get('detail')}")
        except:
            print(f"   Response: {e.response.text[:200]}")
        return {"type": "error", "error": {"message": str(e)}}

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {"type": "error", "error": {"message": str(e)}}


def test_mcp_remote(oauth_credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Test 3: Test MCP Remote avec n8n (HTTP/SSE)"""
    print("\n" + "="*70)
    print("TEST 3: MCP Remote n8n (HTTP/SSE)")
    print("="*70)

    payload = {
        "oauth_credentials": oauth_credentials,
        "messages": [
            {
                "role": "user",
                "content": """Tu as accès à un serveur MCP n8n distant.

Liste les workflows disponibles et exécute un workflow simple si possible."""
            }
        ],
        "model": "sonnet",
        "stream": False,
        "mcp_servers": N8N_MCP_REMOTE
    }

    print("📤 Envoi requête avec MCP Remote...")
    print(f"   MCP Config: {json.dumps(N8N_MCP_REMOTE, indent=2)}")

    try:
        response = requests.post(
            f"{WRAPPER_URL}/v1/messages",
            json=payload,
            timeout=180
        )
        response.raise_for_status()

        data = response.json()

        if data.get("type") == "error":
            print(f"❌ Erreur API: {data.get('error', {}).get('message')}")
            return data

        # Extraire le texte
        content = data.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            print(f"✅ Réponse reçue ({len(text)} chars)")
            print(f"\n📝 Réponse Claude:")
            print("-" * 70)
            print(text[:500] + ("..." if len(text) > 500 else ""))
            print("-" * 70)

        return data

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {"type": "error", "error": {"message": str(e)}}


def test_mcp_without_n8n(oauth_credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Test 4: Test sans MCP (baseline)"""
    print("\n" + "="*70)
    print("TEST 4: Baseline (sans MCP)")
    print("="*70)

    payload = {
        "oauth_credentials": oauth_credentials,
        "messages": [
            {
                "role": "user",
                "content": "Hello! Dis-moi simplement 'OK' si tu me reçois."
            }
        ],
        "model": "sonnet",
        "stream": False
    }

    print("📤 Envoi requête sans MCP...")

    try:
        response = requests.post(
            f"{WRAPPER_URL}/v1/messages",
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()

        content = data.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            print(f"✅ Réponse reçue: {text[:100]}")

        return data

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {"type": "error", "error": {"message": str(e)}}


# =============================================================================
# Main
# =============================================================================

def main():
    """Exécute la suite de tests MCP n8n"""

    print("="*70)
    print("🔧 Test MCP n8n Integration")
    print("="*70)
    print("\nCe script teste l'intégration MCP entre Claude Wrapper et n8n")
    print("\nPrérequis:")
    print("  1. OAuth credentials Claude valides")
    print("  2. n8n installé et lancé (local ou distant)")
    print("  3. Serveur MCP n8n configuré")

    # Vérifier credentials
    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)

    # Demander credentials OAuth
    print("\n📋 OAuth Credentials requises:")
    print("   Vous avez besoin de:")
    print("   - access_token (sk-ant-oat01-...)")
    print("   - refresh_token (sk-ant-ort01-...)")
    print("   - expires_at (timestamp milliseconds)")

    use_env = input("\nVoulez-vous utiliser les variables d'environnement? (y/n): ")

    if use_env.lower() == 'y':
        import os
        oauth_credentials = {
            "access_token": os.getenv("CLAUDE_ACCESS_TOKEN", ""),
            "refresh_token": os.getenv("CLAUDE_REFRESH_TOKEN", ""),
            "expires_at": int(os.getenv("CLAUDE_EXPIRES_AT", "0")),
            "scopes": ["user:inference", "user:profile"],
            "subscription_type": "max"
        }

        if not oauth_credentials["access_token"]:
            print("\n❌ CLAUDE_ACCESS_TOKEN non défini!")
            print("   Exportez: export CLAUDE_ACCESS_TOKEN='sk-ant-oat01-...'")
            sys.exit(1)
    else:
        print("\n⚠️  Mode interactif désactivé pour sécurité")
        print("   Éditez le script et ajoutez vos credentials dans OAUTH_CREDENTIALS")
        print("   Ou utilisez les variables d'environnement")
        sys.exit(1)

    # Configuration n8n
    print("\n📋 Configuration n8n MCP:")
    print("   Éditez N8N_MCP_LOCAL ou N8N_MCP_REMOTE dans le script")

    mcp_type = input("\nType de MCP à tester? (local/remote/both/skip): ")

    # Run tests
    results = {}

    # Test 1: Health
    if test_health():
        results["health"] = True
    else:
        print("\n❌ Wrapper non accessible - arrêt des tests")
        sys.exit(1)

    # Test 2: Baseline (sans MCP)
    results["baseline"] = test_mcp_without_n8n(oauth_credentials)

    # Test 3: MCP Local
    if mcp_type in ['local', 'both']:
        results["mcp_local"] = test_mcp_local(oauth_credentials)

    # Test 4: MCP Remote
    if mcp_type in ['remote', 'both']:
        results["mcp_remote"] = test_mcp_remote(oauth_credentials)

    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*70)

    for test_name, result in results.items():
        if test_name == "health":
            status = "✅" if result else "❌"
        else:
            status = "✅" if result.get("type") != "error" else "❌"

        print(f"{status} {test_name}")

    print("\n" + "="*70)
    print("✅ Tests terminés!")
    print("="*70)


if __name__ == "__main__":
    main()
