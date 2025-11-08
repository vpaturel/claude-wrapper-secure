#!/bin/bash
#
# Exemples curl pour tester MCP n8n
# Usage: source examples_mcp_n8n.sh
#

# =============================================================================
# Configuration
# =============================================================================

export WRAPPER_URL="https://wrapper.claude.serenity-system.fr"
export BRIDGE_URL="http://localhost:8000"

# OAuth credentials (à définir)
export CLAUDE_ACCESS_TOKEN="${CLAUDE_ACCESS_TOKEN:-sk-ant-oat01-YOUR-TOKEN}"
export CLAUDE_REFRESH_TOKEN="${CLAUDE_REFRESH_TOKEN:-sk-ant-ort01-YOUR-TOKEN}"
export CLAUDE_EXPIRES_AT="${CLAUDE_EXPIRES_AT:-1762444195608}"

# =============================================================================
# Fonctions utilitaires
# =============================================================================

test_wrapper_health() {
    echo "🔍 Test Claude Wrapper health..."
    curl -s "$WRAPPER_URL/health" | jq '.'
}

test_bridge_health() {
    echo "🔍 Test MCP Bridge health..."
    curl -s "$BRIDGE_URL/health" | jq '.'
}

test_bridge_list_workflows() {
    echo "📋 Test MCP Bridge - List workflows..."
    curl -s -X POST "$BRIDGE_URL/mcp/tools/call" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer test-bridge-token" \
      -d '{
        "tool": "list_workflows",
        "arguments": {}
      }' | jq '.'
}

test_bridge_get_workflow() {
    local workflow_id="$1"
    if [ -z "$workflow_id" ]; then
        echo "Usage: test_bridge_get_workflow <workflow_id>"
        return 1
    fi

    echo "📄 Test MCP Bridge - Get workflow $workflow_id..."
    curl -s -X POST "$BRIDGE_URL/mcp/tools/call" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer test-bridge-token" \
      -d "{
        \"tool\": \"get_workflow\",
        \"arguments\": {
          \"workflow_id\": \"$workflow_id\"
        }
      }" | jq '.'
}

test_bridge_execute_workflow() {
    local workflow_id="$1"
    local data="${2:-{}}"

    if [ -z "$workflow_id" ]; then
        echo "Usage: test_bridge_execute_workflow <workflow_id> [data_json]"
        return 1
    fi

    echo "▶️  Test MCP Bridge - Execute workflow $workflow_id..."
    curl -s -X POST "$BRIDGE_URL/mcp/tools/call" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer test-bridge-token" \
      -d "{
        \"tool\": \"execute_workflow\",
        \"arguments\": {
          \"workflow_id\": \"$workflow_id\",
          \"data\": $data
        }
      }" | jq '.'
}

test_claude_list_workflows() {
    echo "🤖 Test Claude - List n8n workflows..."
    curl -s -X POST "$WRAPPER_URL/v1/messages" \
      -H "Content-Type: application/json" \
      -d "{
        \"oauth_credentials\": {
          \"access_token\": \"$CLAUDE_ACCESS_TOKEN\",
          \"refresh_token\": \"$CLAUDE_REFRESH_TOKEN\",
          \"expires_at\": $CLAUDE_EXPIRES_AT,
          \"scopes\": [\"user:inference\", \"user:profile\"],
          \"subscription_type\": \"max\"
        },
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": \"Tu as accès à n8n. Liste tous les workflows disponibles et résume chacun en une phrase.\"
          }
        ],
        \"model\": \"sonnet\",
        \"mcp_servers\": {
          \"n8n\": {
            \"url\": \"$BRIDGE_URL/mcp/sse\",
            \"transport\": \"sse\",
            \"auth_type\": \"bearer\",
            \"auth_token\": \"test-bridge-token\"
          }
        }
      }" | jq '.'
}

test_claude_execute_workflow() {
    local workflow_name="$1"
    if [ -z "$workflow_name" ]; then
        echo "Usage: test_claude_execute_workflow <workflow_name>"
        return 1
    fi

    echo "🤖 Test Claude - Execute workflow '$workflow_name'..."
    curl -s -X POST "$WRAPPER_URL/v1/messages" \
      -H "Content-Type: application/json" \
      -d "{
        \"oauth_credentials\": {
          \"access_token\": \"$CLAUDE_ACCESS_TOKEN\",
          \"refresh_token\": \"$CLAUDE_REFRESH_TOKEN\",
          \"expires_at\": $CLAUDE_EXPIRES_AT,
          \"scopes\": [\"user:inference\", \"user:profile\"],
          \"subscription_type\": \"max\"
        },
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": \"Exécute le workflow n8n nommé '$workflow_name' et montre-moi le résultat.\"
          }
        ],
        \"model\": \"sonnet\",
        \"mcp_servers\": {
          \"n8n\": {
            \"url\": \"$BRIDGE_URL/mcp/sse\",
            \"transport\": \"sse\",
            \"auth_type\": \"bearer\",
            \"auth_token\": \"test-bridge-token\"
          }
        }
      }" | jq '.'
}

test_claude_analyze_workflows() {
    echo "🤖 Test Claude - Analyze all workflows..."
    curl -s -X POST "$WRAPPER_URL/v1/messages" \
      -H "Content-Type: application/json" \
      -d "{
        \"oauth_credentials\": {
          \"access_token\": \"$CLAUDE_ACCESS_TOKEN\",
          \"refresh_token\": \"$CLAUDE_REFRESH_TOKEN\",
          \"expires_at\": $CLAUDE_EXPIRES_AT,
          \"scopes\": [\"user:inference\", \"user:profile\"],
          \"subscription_type\": \"max\"
        },
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": \"Analyse tous mes workflows n8n et identifie: 1) Les workflows inactifs, 2) Les plus complexes, 3) Suggestions d'optimisation.\"
          }
        ],
        \"model\": \"sonnet\",
        \"mcp_servers\": {
          \"n8n\": {
            \"url\": \"$BRIDGE_URL/mcp/sse\",
            \"transport\": \"sse\",
            \"auth_type\": \"bearer\",
            \"auth_token\": \"test-bridge-token\"
          }
        }
      }" | jq '.content[0].text'
}

# =============================================================================
# Help
# =============================================================================

show_help() {
    cat <<'EOF'
📚 Exemples MCP n8n - Fonctions disponibles:

Health Checks:
  test_wrapper_health           - Vérifie Claude Wrapper
  test_bridge_health            - Vérifie MCP Bridge

MCP Bridge (direct):
  test_bridge_list_workflows    - Liste workflows
  test_bridge_get_workflow ID   - Détails workflow
  test_bridge_execute_workflow ID [DATA] - Exécute workflow

Claude (via MCP):
  test_claude_list_workflows          - Liste workflows via Claude
  test_claude_execute_workflow NAME   - Exécute workflow via Claude
  test_claude_analyze_workflows       - Analyse complète

Configuration:
  WRAPPER_URL="https://wrapper.claude.serenity-system.fr"
  BRIDGE_URL="http://localhost:8000"
  CLAUDE_ACCESS_TOKEN="sk-ant-oat01-..."
  CLAUDE_REFRESH_TOKEN="sk-ant-ort01-..."
  CLAUDE_EXPIRES_AT="1762444195608"

Usage:
  source examples_mcp_n8n.sh
  test_wrapper_health
  test_bridge_list_workflows
  test_claude_list_workflows

EOF
}

# =============================================================================
# Affichage au source
# =============================================================================

echo "✅ Fonctions MCP n8n chargées!"
echo ""
echo "Configuration actuelle:"
echo "  WRAPPER_URL: $WRAPPER_URL"
echo "  BRIDGE_URL: $BRIDGE_URL"
echo "  OAuth configured: $([ ! -z "$CLAUDE_ACCESS_TOKEN" ] && [ "$CLAUDE_ACCESS_TOKEN" != "sk-ant-oat01-YOUR-TOKEN" ] && echo "✅" || echo "❌")"
echo ""
echo "Pour voir toutes les fonctions: show_help"
echo "Pour tester rapidement: test_wrapper_health"
echo ""
