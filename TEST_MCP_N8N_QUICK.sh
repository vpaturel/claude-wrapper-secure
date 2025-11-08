#!/bin/bash
#
# Test rapide MCP n8n
# Ce script teste l'intégration complète Claude Wrapper + MCP Bridge + n8n
#

set -e

echo "=========================================================================="
echo "🧪 Test MCP n8n Integration - Quick Start"
echo "=========================================================================="

# =============================================================================
# Configuration
# =============================================================================

WRAPPER_URL="${WRAPPER_URL:-https://wrapper.claude.serenity-system.fr}"
BRIDGE_URL="${BRIDGE_URL:-http://localhost:8000}"
N8N_URL="${N8N_URL:-http://localhost:5678}"

echo ""
echo "📋 Configuration:"
echo "   Claude Wrapper: $WRAPPER_URL"
echo "   MCP Bridge: $BRIDGE_URL"
echo "   n8n Instance: $N8N_URL"
echo ""

# =============================================================================
# Vérifications
# =============================================================================

echo "1️⃣  Vérification des prérequis..."
echo ""

# Check Claude Wrapper
echo -n "   ▶ Claude Wrapper accessible... "
if curl -sf "$WRAPPER_URL/health" > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
    echo ""
    echo "   Erreur: Claude Wrapper non accessible à $WRAPPER_URL"
    echo "   Vérifiez que le service est lancé"
    exit 1
fi

# Check MCP Bridge
echo -n "   ▶ MCP Bridge accessible... "
if curl -sf "$BRIDGE_URL/health" > /dev/null 2>&1; then
    echo "✅"
    BRIDGE_HEALTHY=$(curl -s "$BRIDGE_URL/health" | jq -r '.n8n_accessible')
    if [ "$BRIDGE_HEALTHY" = "true" ]; then
        echo "   ✅ Bridge connecté à n8n"
    else
        echo "   ⚠️  Bridge lancé mais n8n non accessible"
    fi
else
    echo "❌"
    echo ""
    echo "   Erreur: MCP Bridge non accessible à $BRIDGE_URL"
    echo "   Lancez le bridge:"
    echo "     python n8n_mcp_bridge.py --n8n-url $N8N_URL --n8n-api-key YOUR_KEY"
    exit 1
fi

# Check n8n
echo -n "   ▶ n8n accessible... "
if curl -sf "$N8N_URL/healthz" > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
    echo ""
    echo "   Erreur: n8n non accessible à $N8N_URL"
    echo "   Lancez n8n:"
    echo "     n8n start"
    exit 1
fi

echo ""
echo "✅ Tous les prérequis sont OK!"
echo ""

# =============================================================================
# Test 1: Test direct MCP Bridge
# =============================================================================

echo "2️⃣  Test direct MCP Bridge (sans Claude)..."
echo ""

echo "   ▶ Appel direct list_workflows..."
RESPONSE=$(curl -s -X POST "$BRIDGE_URL/mcp/tools/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-bridge-token" \
  -d '{
    "tool": "list_workflows",
    "arguments": {}
  }')

SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
if [ "$SUCCESS" = "true" ]; then
    COUNT=$(echo "$RESPONSE" | jq -r '.result.count')
    echo "   ✅ MCP Bridge fonctionne!"
    echo "   📊 Workflows trouvés: $COUNT"

    # Afficher premiers workflows
    if [ "$COUNT" -gt 0 ]; then
        echo ""
        echo "   📋 Workflows disponibles:"
        echo "$RESPONSE" | jq -r '.result.workflows[] | "      - \(.name) (ID: \(.id), Active: \(.active))"' | head -5
    fi
else
    echo "   ❌ Erreur MCP Bridge"
    echo "   Detail: $(echo $RESPONSE | jq -r '.error')"
    exit 1
fi

echo ""

# =============================================================================
# Test 2: Test avec Claude Wrapper
# =============================================================================

echo "3️⃣  Test avec Claude Wrapper (intégration complète)..."
echo ""

# Vérifier OAuth credentials
if [ -z "$CLAUDE_ACCESS_TOKEN" ]; then
    echo "   ⚠️  CLAUDE_ACCESS_TOKEN non défini"
    echo ""
    echo "   Pour tester l'intégration complète, exportez vos credentials:"
    echo "     export CLAUDE_ACCESS_TOKEN='sk-ant-oat01-...'"
    echo "     export CLAUDE_REFRESH_TOKEN='sk-ant-ort01-...'"
    echo "     export CLAUDE_EXPIRES_AT='1762444195608'"
    echo ""
    echo "   Puis relancez ce script"
    exit 0
fi

echo "   ▶ Envoi requête à Claude avec MCP n8n..."

PAYLOAD=$(cat <<EOF
{
  "oauth_credentials": {
    "access_token": "$CLAUDE_ACCESS_TOKEN",
    "refresh_token": "${CLAUDE_REFRESH_TOKEN:-}",
    "expires_at": ${CLAUDE_EXPIRES_AT:-0},
    "scopes": ["user:inference", "user:profile"],
    "subscription_type": "max"
  },
  "messages": [
    {
      "role": "user",
      "content": "Tu as accès à n8n via MCP. Liste les workflows disponibles et résume-les en une phrase chacun."
    }
  ],
  "model": "sonnet",
  "mcp_servers": {
    "n8n": {
      "url": "$BRIDGE_URL/mcp/sse",
      "transport": "sse",
      "auth_type": "bearer",
      "auth_token": "test-bridge-token"
    }
  }
}
EOF
)

RESPONSE=$(curl -s -X POST "$WRAPPER_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

TYPE=$(echo "$RESPONSE" | jq -r '.type')

if [ "$TYPE" = "error" ]; then
    echo "   ❌ Erreur Claude"
    echo "   Message: $(echo $RESPONSE | jq -r '.error.message')"
    exit 1
else
    echo "   ✅ Réponse reçue de Claude!"
    echo ""

    # Extraire et afficher la réponse
    TEXT=$(echo "$RESPONSE" | jq -r '.content[0].text')
    echo "   📝 Réponse Claude:"
    echo "   ─────────────────────────────────────────────────────────────"
    echo "$TEXT" | fold -s -w 70 | sed 's/^/   /'
    echo "   ─────────────────────────────────────────────────────────────"
    echo ""

    # Usage stats
    INPUT_TOKENS=$(echo "$RESPONSE" | jq -r '.usage.input_tokens // 0')
    OUTPUT_TOKENS=$(echo "$RESPONSE" | jq -r '.usage.output_tokens // 0')
    echo "   📊 Usage:"
    echo "      Input: $INPUT_TOKENS tokens"
    echo "      Output: $OUTPUT_TOKENS tokens"
fi

echo ""
echo "=========================================================================="
echo "✅ Tests terminés avec succès!"
echo "=========================================================================="
echo ""
echo "🎉 L'intégration MCP n8n fonctionne correctement!"
echo ""
echo "Prochaines étapes:"
echo "  1. Créez des workflows dans n8n"
echo "  2. Testez l'exécution de workflows via Claude"
echo "  3. Automatisez vos tâches avec n8n + Claude"
echo ""
echo "Documentation:"
echo "  - Setup: docs/N8N_MCP_BRIDGE_SETUP.md"
echo "  - Integration: docs/MCP_N8N_INTEGRATION.md"
echo ""
