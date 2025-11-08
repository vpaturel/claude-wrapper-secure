# 🎯 Prochaines Actions - Documentation Claude API (60% → 85%)

**Date** : 2025-11-05 15:00
**État actuel** : 60% complété
**Objectif** : 85% (Features + Limites + Modèles)

---

## 📊 Sections Prioritaires

### 1. Features Avancées (10% → 50%) - Priorité HAUTE
**Impact** : +20% documentation totale
**Temps estimé** : 2-3 heures

### 2. Limites et Quotas (0% → 60%) - Priorité MOYENNE
**Impact** : +10% documentation totale
**Temps estimé** : 1-2 heures

### 3. Modèles Disponibles (5% → 70%) - Priorité MOYENNE
**Impact** : +5% documentation totale
**Temps estimé** : 1 heure

---

## 🚀 ACTION 1 : Tool Calling (1h)

### Objectif
Capturer et documenter l'utilisation complète des tools/function calling

### Méthode
```bash
# 1. Lancer proxy capture
cd /home/tincenv/analyse-claude-ai
python3 proxy_capture_full.py > /tmp/proxy_tools.log 2>&1 &

# 2. Créer requête avec tool
cat > /tmp/test_tool.py <<'EOF'
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    tools=[{
        "name": "get_weather",
        "description": "Get weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }],
    messages=[{"role": "user", "content": "What's the weather in Paris?"}]
)

print(response.model_dump_json(indent=2))
EOF

# 3. Exécuter avec proxy
HTTP_PROXY=http://localhost:8000 python3 /tmp/test_tool.py

# 4. Analyser capture
ls -lt captures/requests/ | head -5
```

### À documenter
- [ ] Structure `tools` dans requête
- [ ] Format `input_schema` (JSON Schema)
- [ ] Réponse `tool_use` du modèle
- [ ] Format `tool_result` pour réponse
- [ ] Gestion multi-tools
- [ ] Erreurs tool calling

---

## 🚀 ACTION 2 : Image Upload (45 min)

### Objectif
Capturer requête avec image base64

### Méthode
```bash
# 1. Créer image de test
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" > /tmp/test.b64

# 2. Test avec image
cat > /tmp/test_image.py <<'EOF'
import anthropic
import base64

client = anthropic.Anthropic()

with open("/tmp/test.b64") as f:
    image_data = f.read()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data
                }
            }
        ]
    }]
)

print(response.model_dump_json(indent=2))
EOF

HTTP_PROXY=http://localhost:8000 python3 /tmp/test_image.py
```

### À documenter
- [ ] Format `image` content type
- [ ] Structure `source` (base64)
- [ ] `media_type` supportés (png, jpg, gif, webp)
- [ ] Taille max image
- [ ] Multi-images dans une requête
- [ ] Erreurs image (trop grande, format invalide)

---

## 🚀 ACTION 3 : Rate Limits (30 min)

### Objectif
Déclencher et capturer rate limiting

### Méthode
```bash
# Lancer 100 requêtes rapides
for i in {1..100}; do
  HTTP_PROXY=http://localhost:8000 claude chat "test $i" &
  sleep 0.1
done

# Attendre completion
wait

# Analyser erreurs 429
grep -r "429" captures/errors/
```

### À documenter
- [ ] Headers `x-ratelimit-*` dans réponses
- [ ] Format erreur 429 (rate_limit_error)
- [ ] Message d'erreur exact
- [ ] Retry-After header
- [ ] Limites par plan (Max vs Pro)

---

## 🚀 ACTION 4 : Différents Modèles (30 min)

### Objectif
Tester tous les modèles disponibles via OAuth

### Méthode
```bash
# Tester chaque modèle
for model in "claude-opus-4-20250514" "claude-sonnet-4-5-20250929" "claude-3-5-haiku-20241022" "claude-3-5-sonnet-20241022"; do
  echo "Testing $model..."
  HTTP_PROXY=http://localhost:8000 claude --model $model chat "Hello, what model are you?"
  sleep 2
done
```

### À documenter
- [ ] Liste modèles disponibles OAuth
- [ ] Noms exacts (IDs)
- [ ] Context window par modèle
- [ ] Max tokens output par modèle
- [ ] Différences OAuth vs API Key
- [ ] Erreurs modèle non disponible

---

## 🚀 ACTION 5 : Prompt Caching (20 min)

### Objectif
Tester si prompt caching disponible avec OAuth

### Méthode
```bash
cat > /tmp/test_cache.py <<'EOF'
import anthropic

client = anthropic.Anthropic()

# Large system prompt (should be cached)
large_prompt = "You are a helpful assistant. " * 1000

for i in range(3):
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        system=[{
            "type": "text",
            "text": large_prompt,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": f"Test {i}"}]
    )
    print(f"Request {i}: {response.usage}")
EOF

HTTP_PROXY=http://localhost:8000 python3 /tmp/test_cache.py
```

### À documenter
- [ ] Disponible avec OAuth ? (oui/non)
- [ ] Headers prompt caching
- [ ] Structure `cache_control`
- [ ] Usage response avec cache hits
- [ ] Différences vs API Key

---

## 🚀 ACTION 6 : Long Context (30 min)

### Objectif
Tester limite context window

### Méthode
```bash
# Générer gros contexte (~50K tokens)
python3 -c "print('A' * 200000)" > /tmp/large_context.txt

cat > /tmp/test_context.py <<'EOF'
import anthropic

client = anthropic.Anthropic()

with open("/tmp/large_context.txt") as f:
    large_text = f.read()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=100,
    messages=[{
        "role": "user",
        "content": f"Summarize: {large_text}"
    }]
)

print(response.model_dump_json(indent=2))
EOF

HTTP_PROXY=http://localhost:8000 python3 /tmp/test_context.py
```

### À documenter
- [ ] Context window exact (200K tokens ?)
- [ ] Erreur si dépassement (400 + message)
- [ ] Comptage tokens (approximatif vs exact)
- [ ] Performance (latence avec gros contexte)

---

## 🚀 ACTION 7 : Headers Complets (15 min)

### Objectif
Capturer tous les headers de réponse

### Méthode
```bash
# Analyser captures existantes
jq '.response_headers' captures/requests/*.json | sort -u

# Tester cas spéciaux
HTTP_PROXY=http://localhost:8000 claude chat "Test headers"
```

### À documenter
- [ ] `request-id` (UUID)
- [ ] `anthropic-organization-id` (si présent)
- [ ] `x-ratelimit-*` complets
- [ ] `content-type` (text/event-stream)
- [ ] Headers debug/versioning

---

## 📊 Temps Estimé Total : 4-5 heures

| Action | Temps | Impact |
|--------|-------|--------|
| Tool calling | 1h | +8% |
| Image upload | 45min | +5% |
| Rate limits | 30min | +3% |
| Modèles | 30min | +5% |
| Prompt caching | 20min | +2% |
| Long context | 30min | +2% |
| Headers | 15min | +2% |
| **TOTAL** | **4h30** | **+27%** |

**Progression finale estimée** : 60% + 27% = **87%**

---

## 🎯 Résultat Attendu

### Documentation complète de :
1. ✅ Authentification OAuth (70%)
2. ✅ Streaming SSE (95%)
3. ✅ Erreurs HTTP (70%)
4. 🆕 **Features avancées (50%)** ← Nouveau
5. 🆕 **Limites/Quotas (60%)** ← Nouveau
6. 🆕 **Modèles (70%)** ← Nouveau
7. ⏳ API Messages (35% → 50%)

**Total final** : **85-87%**

---

## 📝 Template Capture

Pour chaque action, créer fichier markdown :

```markdown
# Feature: [NOM]

## Requête

\`\`\`json
{requête capturée}
\`\`\`

## Réponse

\`\`\`json
{réponse capturée}
\`\`\`

## Structure

- **Champ X** : Description
- **Champ Y** : Description

## Erreurs Possibles

- `error_type_1` : Description
- `error_type_2` : Description

## Exemples

\`\`\`python
# Exemple d'utilisation
\`\`\`

## Différences OAuth vs API Key

- OAuth : ...
- API Key : ...
```

---

## 🚀 Quick Start

```bash
# 1. Lancer proxy
cd /home/tincenv/analyse-claude-ai
python3 proxy_capture_full.py > /tmp/proxy_features.log 2>&1 &

# 2. Choisir une action
# Voir détails ci-dessus

# 3. Analyser captures
ls -lt captures/requests/ | head -10
jq '.' captures/requests/[LATEST].json

# 4. Documenter dans markdown
vim FEATURE_[NOM].md
```

---

**Prêt à commencer ?**

Choisis une action (1-7) ou démarre par la plus simple (Action 2 : Images).
