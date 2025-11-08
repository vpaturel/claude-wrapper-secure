#!/bin/bash
# Script de test pour proxy_capture_full.py

set -euo pipefail

echo "================================"
echo "🧪 TEST PROXY CAPTURE FULL"
echo "================================"
echo ""

# Variables
PROXY_SCRIPT="/home/tincenv/analyse-claude-ai/proxy_capture_full.py"
CAPTURES_DIR="/home/tincenv/analyse-claude-ai/captures"
PROXY_PID_FILE="/tmp/proxy_capture.pid"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction cleanup
cleanup() {
    if [ -f "$PROXY_PID_FILE" ]; then
        PID=$(cat "$PROXY_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${YELLOW}🛑 Arrêt du proxy (PID: $PID)${NC}"
            kill "$PID"
            rm -f "$PROXY_PID_FILE"
        fi
    fi
}

trap cleanup EXIT

# 1. Vérifier que le proxy existe
if [ ! -f "$PROXY_SCRIPT" ]; then
    echo -e "${RED}❌ Proxy script not found: $PROXY_SCRIPT${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Proxy script found${NC}"

# 2. Lancer le proxy en background
echo ""
echo "🚀 Lancement du proxy..."
python3 "$PROXY_SCRIPT" > /tmp/proxy.log 2>&1 &
PROXY_PID=$!
echo "$PROXY_PID" > "$PROXY_PID_FILE"
echo -e "${GREEN}✅ Proxy started (PID: $PROXY_PID)${NC}"

# Attendre que le proxy soit prêt
sleep 2

# Vérifier que le proxy tourne
if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    echo -e "${RED}❌ Proxy failed to start. Check /tmp/proxy.log${NC}"
    cat /tmp/proxy.log
    exit 1
fi

# 3. Tester une requête simple
echo ""
echo "📡 Test 1: Simple request (streaming)"
echo "Command: echo 'Hello, what is 2+2?' | ANTHROPIC_BASE_URL=http://localhost:8000 claude"

export ANTHROPIC_BASE_URL=http://localhost:8000

# Faire la requête
echo 'Hello, what is 2+2?' | claude 2>&1 | head -20

# Attendre que la capture soit écrite
sleep 1

# 4. Vérifier les captures
echo ""
echo "📊 Vérification des captures..."

# Compter les fichiers
STREAMING_COUNT=$(find "$CAPTURES_DIR/streaming/" -name "*.json" 2>/dev/null | wc -l)
REQUESTS_COUNT=$(find "$CAPTURES_DIR/requests/" -name "*.json" 2>/dev/null | wc -l)

echo -e "${GREEN}✅ Streaming captures: $STREAMING_COUNT${NC}"
echo -e "${GREEN}✅ Request captures: $REQUESTS_COUNT${NC}"

# Afficher le dernier fichier streaming
if [ "$STREAMING_COUNT" -gt 0 ]; then
    LAST_STREAM=$(find "$CAPTURES_DIR/streaming/" -name "*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    echo ""
    echo "📄 Dernière capture streaming: $(basename "$LAST_STREAM")"

    # Vérifier qu'il n'y a pas de troncature
    FILE_SIZE=$(stat -c%s "$LAST_STREAM")
    echo "   Taille: $FILE_SIZE bytes"

    # Compter les events SSE
    EVENTS_COUNT=$(jq '.response.body.events | length' "$LAST_STREAM" 2>/dev/null || echo "0")
    echo "   Events SSE: $EVENTS_COUNT"

    # Afficher le premier et dernier event
    if [ "$EVENTS_COUNT" -gt 0 ]; then
        echo ""
        echo "   📌 Premier event:"
        jq -r '.response.body.events[0].event' "$LAST_STREAM" 2>/dev/null || echo "   (parse error)"

        echo ""
        echo "   📌 Dernier event:"
        jq -r '.response.body.events[-1].event' "$LAST_STREAM" 2>/dev/null || echo "   (parse error)"
    fi

    # Vérifier qu'il n'y a PAS de troncature
    TRUNCATED=$(grep -c '"\.\.\."' "$LAST_STREAM" || true)
    if [ "$TRUNCATED" -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ PAS DE TRONCATURE DÉTECTÉE !${NC}"
    else
        echo ""
        echo -e "${RED}⚠️  TRONCATURE DÉTECTÉE (...)${NC}"
    fi
fi

# 5. Résumé
echo ""
echo "================================"
echo "📊 RÉSUMÉ DU TEST"
echo "================================"
echo "Proxy PID: $PROXY_PID"
echo "Captures dir: $CAPTURES_DIR"
echo "Streaming captures: $STREAMING_COUNT"
echo "Request captures: $REQUESTS_COUNT"
echo ""
echo -e "${GREEN}✅ Test terminé avec succès !${NC}"
echo ""
echo "Pour voir les captures:"
echo "  ls -lh $CAPTURES_DIR/streaming/"
echo "  jq . $CAPTURES_DIR/streaming/*.json | head -50"
echo ""
