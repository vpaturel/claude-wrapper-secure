# 📘 Guide d'utilisation - Proxy Full Capture

**Proxy** : `proxy_capture_full.py`
**Version** : 1.0
**Date** : 2025-11-05

---

## 🚀 Quick Start (3 étapes)

### 1. Lancer le proxy

```bash
cd /home/tincenv/analyse-claude-ai
python3 proxy_capture_full.py
```

Vous devriez voir :
```
======================================================================
🚀 CLAUDE API PROXY - FULL CAPTURE MODE
======================================================================

🔍 Proxy listening on http://localhost:8000
📁 Captures directory: /home/tincenv/analyse-claude-ai/captures
...
```

### 2. Utiliser Claude via le proxy (nouveau terminal)

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'What is 2+2?' | claude
```

### 3. Consulter les captures

```bash
# Lister toutes les captures
tree captures/

# Voir la dernière capture streaming
ls -t captures/streaming/*.json | head -1 | xargs jq .

# Compter les events SSE capturés
jq '.response.body.events_count' captures/streaming/*.json
```

---

## 📚 Exemples d'utilisation

### Capturer une requête simple

```bash
# Terminal 1
python3 proxy_capture_full.py

# Terminal 2
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'Hello!' | claude
```

**Résultat** :
- `captures/streaming/20251105_HHMMSS_stream.json` (réponse SSE complète)
- `captures/requests/20251105_HHMMSS_request.json` (requête)

---

### Capturer erreur 401 (token invalide)

```bash
# Backup credentials
cp ~/.claude/.credentials.json ~/.claude/.credentials.json.bak

# Modifier token pour le rendre invalide
sed -i 's/sk-ant-oat01-.*/sk-ant-oat01-INVALID"/' ~/.claude/.credentials.json

# Lancer proxy
python3 proxy_capture_full.py &

# Faire requête (va échouer avec 401)
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'test' | claude

# Restaurer credentials
mv ~/.claude/.credentials.json.bak ~/.claude/.credentials.json
```

**Résultat** :
- `captures/errors/20251105_HHMMSS_error_401.json`

---

### Capturer erreur 429 (rate limit)

```bash
# Lancer proxy
python3 proxy_capture_full.py &

# Faire beaucoup de requêtes rapides
export ANTHROPIC_BASE_URL=http://localhost:8000
for i in {1..50}; do
  echo "test $i" | claude &
done
wait
```

**Résultat** :
- Plusieurs `captures/errors/20251105_HHMMSS_error_429.json`

---

### Capturer longue réponse (2000+ tokens)

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'Écris un essai de 2000 mots sur la physique quantique' | claude
```

**Résultat** :
- Capture complète (pas de troncature !)
- Tous les events `content_block_delta` capturés

---

### Capturer tool calling

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'Quelle heure est-il à Paris ?' | claude
```

**Résultat** :
- Events `tool_use` capturés
- Format complet des tools

---

## 🔍 Analyser les captures

### Compter les events par type

```bash
jq -r '.response.body.events[].event' captures/streaming/*.json | sort | uniq -c
```

**Output exemple** :
```
  15 content_block_delta
   3 content_block_start
   3 content_block_stop
   3 message_delta
   3 message_start
   3 message_stop
```

### Extraire tous les textes générés

```bash
jq -r '.response.body.events[] | select(.event=="content_block_delta") | .data.delta.text' \
  captures/streaming/*.json
```

### Voir les headers de rate limiting

```bash
jq '.response.headers' captures/streaming/*.json | grep -i "ratelimit"
```

### Calculer taille moyenne des réponses

```bash
jq '.metadata.size_bytes' captures/streaming/*.json | \
  awk '{sum+=$1; count++} END {print "Moyenne:", sum/count, "bytes"}'
```

### Trouver les erreurs

```bash
ls captures/errors/*.json | while read f; do
  echo "=== $f ==="
  jq '{status: .response.status, error: .response.body.error}' "$f"
done
```

---

## 🛠️ Troubleshooting

### Le proxy ne démarre pas

**Erreur** : `Address already in use`

**Solution** :
```bash
# Trouver le process sur port 8000
lsof -i :8000

# Tuer le process
kill -9 <PID>

# Relancer
python3 proxy_capture_full.py
```

---

### Claude ne se connecte pas au proxy

**Symptôme** : Timeout ou connexion refusée

**Vérifications** :
```bash
# 1. Vérifier que le proxy tourne
lsof -i :8000

# 2. Vérifier la variable d'environnement
echo $ANTHROPIC_BASE_URL
# Doit afficher: http://localhost:8000

# 3. Tester avec curl
curl -i http://localhost:8000/health
```

---

### Les captures sont vides

**Cause** : Le proxy n'a pas les droits d'écriture

**Solution** :
```bash
# Vérifier les permissions
ls -ld /home/tincenv/analyse-claude-ai/captures/

# Créer les dossiers si besoin
mkdir -p /home/tincenv/analyse-claude-ai/captures/{streaming,requests,responses,errors}

# Vérifier les permissions
chmod -R u+w /home/tincenv/analyse-claude-ai/captures/
```

---

### Le JSON est mal formaté

**Symptôme** : `jq` renvoie une erreur de parsing

**Solution** :
```bash
# Vérifier la validité du JSON
python3 -m json.tool captures/streaming/FILE.json

# Reformater si besoin
jq . captures/streaming/FILE.json > /tmp/fixed.json
mv /tmp/fixed.json captures/streaming/FILE.json
```

---

## 📊 Structure des fichiers capturés

### Fichier streaming SSE

```json
{
  "timestamp": "2025-11-05T10:58:30.123456",
  "request": {
    "method": "POST",
    "path": "/v1/messages?beta=true",
    "headers": {...},
    "body": {...}
  },
  "response": {
    "status": 200,
    "headers": {
      "content-type": "text/event-stream; charset=utf-8"
    },
    "body": {
      "format": "sse",
      "events_count": 15,
      "events": [
        {"event": "message_start", "data": {...}},
        {"event": "content_block_start", "data": {...}},
        {"event": "content_block_delta", "data": {...}},
        ...
      ],
      "raw": "event: message_start\ndata: {...}\n\n..."
    },
    "size_bytes": 4567,
    "is_streaming": true
  },
  "metadata": {
    "is_streaming": true,
    "is_error": false,
    "size_bytes": 4567
  }
}
```

### Fichier erreur HTTP

```json
{
  "timestamp": "2025-11-05T10:58:30.123456",
  "request": {...},
  "response": {
    "status": 401,
    "headers": {...},
    "body": {
      "type": "error",
      "error": {
        "type": "authentication_error",
        "message": "invalid x-api-key"
      }
    },
    "error": true
  },
  "metadata": {
    "is_streaming": false,
    "is_error": true,
    "size_bytes": 123
  }
}
```

---

## 🎯 Cas d'usage avancés

### Capturer avec différents modèles

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000

# Sonnet 4.5
echo 'test' | claude --model claude-sonnet-4-5-20250929

# Opus 4.5
echo 'test' | claude --model claude-opus-4-5-20250514

# Haiku 4.5
echo 'test' | claude --model claude-haiku-4-5-20251001
```

### Capturer avec thinking mode

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'Résous x^3 + 2x^2 - 5x + 1 = 0' | claude --model opus
```

**Résultat** : Events `thinking` capturés

---

### Capturer upload image

```bash
# Créer image test
convert -size 100x100 xc:red /tmp/test.png

# Capturer
export ANTHROPIC_BASE_URL=http://localhost:8000
echo 'Décris cette image: /tmp/test.png' | claude
```

**Résultat** : Body avec `image` en base64

---

## 📚 Ressources

- **Proxy source** : `proxy_capture_full.py`
- **Documentation améliorations** : `PROXY_IMPROVEMENTS.md`
- **Plan complétion** : `PLAN_COMPLETION.md`
- **Analyse technique** : `analyse_claude_api.md`

---

## ✅ Checklist avant capture

- [ ] Proxy lancé (`python3 proxy_capture_full.py`)
- [ ] Port 8000 libre (`lsof -i :8000`)
- [ ] Variable ANTHROPIC_BASE_URL configurée
- [ ] Dossier captures/ créé et accessible
- [ ] Credentials Claude valides (`~/.claude/.credentials.json`)

---

**Bon capture ! 🎯**
