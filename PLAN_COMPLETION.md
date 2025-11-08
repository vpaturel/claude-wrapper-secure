# 🎯 PLAN DE COMPLÉTION - Documentation Claude OAuth API

**Objectif** : Passer de 25% → 100% de documentation complète
**Temps estimé** : 2-3 jours de travail
**Priorité** : High-value items first

---

## 📊 ÉTAT ACTUEL (25%)

### ✅ Acquis
- Endpoint principal
- Authentification Bearer
- Headers HTTP
- Structure requête basique
- Format réponse SSE (partiel)

### ❌ Manquant (75%)
- Flow OAuth complet
- Streaming détaillé
- Gestion erreurs
- Features avancées
- Rate limits
- Token management

---

## 🚀 PHASE 1 : CAPTURES CRITIQUES (Priorité MAX)

### 1.1 Streaming complet (30 min)
**Objectif** : Capturer événement SSE complet sans troncature

**Action** :
```bash
# Modifier proxy pour capturer full response
cd /home/tincenv/analyse-claude-ai
```

**Script amélioré** :
```python
# proxy_capture_full.py
# - Pas de troncature response
# - Capture tous les events SSE
# - Parse event-stream format
```

**Tests** :
- Requête simple (5 tokens)
- Requête moyenne (500 tokens)
- Requête longue (2000 tokens)
- Avec tools
- Avec thinking mode

**Output attendu** :
```
streaming_simple.json
streaming_medium.json
streaming_long.json
streaming_with_tools.json
streaming_with_thinking.json
```

### 1.2 Erreurs HTTP (45 min)
**Objectif** : Capturer toutes les erreurs possibles

**Tests** :
1. **401 Unauthorized** : Token invalide
   ```bash
   # Modifier token dans credentials.json temporairement
   ```

2. **429 Rate Limit** : Trop de requêtes
   ```bash
   # Faire 100 requêtes rapides
   for i in {1..100}; do claude "test" & done
   ```

3. **400 Bad Request** : Payload invalide
   ```bash
   # Envoyer JSON malformé
   ```

4. **529 Overloaded** : API surchargée (difficile à déclencher)

5. **403 Forbidden** : Scope insuffisant

**Output attendu** :
```
error_401.json
error_429.json
error_400.json
error_403.json
```

### 1.3 Token refresh (20 min)
**Objectif** : Capturer refresh token flow

**Méthode** :
1. Attendre expiration token (~1h)
2. Ou forcer expiration en modifiant `expiresAt`
3. Faire requête qui trigger refresh
4. Capturer requête refresh

**Script** :
```bash
# force_token_refresh.sh
# 1. Modifier expiresAt dans credentials.json (passé)
# 2. Lancer proxy
# 3. Faire requête Claude
# 4. Capturer refresh automatique
```

**Output attendu** :
```
token_refresh_request.json
token_refresh_response.json
```

### 1.4 Features avancées (1h)
**Objectif** : Capturer tool calling, images, thinking

**Test 1 : Tool calling**
```bash
echo "Quelle heure est-il à Paris ?" | ANTHROPIC_BASE_URL=http://localhost:8000 claude
```

**Test 2 : Image**
```bash
# Créer test image
convert -size 100x100 xc:red /tmp/test.png
echo "Décris cette image: /tmp/test.png" | ANTHROPIC_BASE_URL=http://localhost:8000 claude
```

**Test 3 : Extended thinking**
```bash
echo "Résous cette équation complexe: x^3 + 2x^2 - 5x + 1 = 0" | ANTHROPIC_BASE_URL=http://localhost:8000 claude --model opus
```

**Output attendu** :
```
feature_tool_calling.json
feature_image_upload.json
feature_extended_thinking.json
```

---

## 🔍 PHASE 2 : REVERSE ENGINEERING (Priorité HAUTE)

### 2.1 Analyse code Claude CLI (1h)
**Objectif** : Extraire endpoints OAuth, rate limits, error handling

**Actions** :
```bash
# 1. Localiser installation
NPM_ROOT=$(npm root -g)
CLAUDE_PATH="$NPM_ROOT/claude-code"

# 2. Examiner package.json
cat "$CLAUDE_PATH/package.json" | jq .

# 3. Chercher endpoints OAuth
grep -r "oauth" "$CLAUDE_PATH/" --include="*.js"
grep -r "/v1/messages" "$CLAUDE_PATH/" --include="*.js"

# 4. Chercher rate limits
grep -r "rate.limit" "$CLAUDE_PATH/" --include="*.js"
grep -r "x-ratelimit" "$CLAUDE_PATH/" --include="*.js"

# 5. Chercher error handling
grep -r "401\|429\|500" "$CLAUDE_PATH/" --include="*.js"

# 6. Extraire config
find "$CLAUDE_PATH/" -name "*.json" -o -name "*.yaml" | xargs cat
```

**Output attendu** :
```
claude_cli_code_analysis.md
- Endpoints découverts
- Rate limits hardcodés
- Error types
- Retry logic
```

### 2.2 Analyse SDK Stainless (45 min)
**Objectif** : Comprendre implémentation client

**Actions** :
```bash
# Chercher SDK Stainless dans node_modules
find "$NPM_ROOT" -name "*stainless*" -type d

# Examiner OAuth helper
grep -r "Bearer\|oauth\|refresh" "$NPM_ROOT/@anthropic-ai/" --include="*.js"
```

### 2.3 Browser DevTools (30 min)
**Objectif** : Capturer OAuth flow initial (login)

**Actions** :
1. Ouvrir Chrome DevTools
2. Aller sur claude.ai
3. Logout
4. Network tab → Preserve log
5. Login
6. Capturer toutes les requêtes OAuth

**Output attendu** :
```
oauth_authorize_request.har
oauth_token_exchange.har
```

---

## 📖 PHASE 3 : DOCUMENTATION OFFICIELLE (Priorité MOYENNE)

### 3.1 Scraping docs (1h)
**Objectif** : Extraire infos non capturées

**Sources** :
- https://docs.claude.com/en/api/messages
- https://docs.claude.com/en/api/messages-streaming
- https://docs.claude.com/en/api/errors
- https://docs.claude.com/en/api/rate-limits

**Script** :
```python
# scrape_docs.py
import requests
from bs4 import BeautifulSoup

urls = [
    "https://docs.claude.com/en/api/messages",
    "https://docs.claude.com/en/api/messages-streaming",
    # ...
]

for url in urls:
    # Fetch + parse + save
```

### 3.2 GitHub Issues (30 min)
**Objectif** : Trouver bugs connus, edge cases

**Recherche** :
```
site:github.com/anthropics/claude-code oauth
site:github.com/anthropics/claude-code rate limit
site:github.com/anthropics/claude-code 401
site:github.com/anthropics/claude-code token expired
```

---

## 🧪 PHASE 4 : TESTS SYSTÉMATIQUES (Priorité MOYENNE)

### 4.1 Tous les modèles (30 min)
**Test** :
```bash
# Liste des modèles à tester
MODELS=(
  "claude-opus-4-5-20250514"
  "claude-sonnet-4-5-20250929"
  "claude-haiku-4-5-20251001"
  "claude-sonnet-4-20250514"
)

for model in "${MODELS[@]}"; do
  echo "Test $model" | ANTHROPIC_BASE_URL=http://localhost:8000 claude --model "$model"
done
```

### 4.2 Rate limiting (1h)
**Test** :
```bash
# Test 1: Requests/minute
for i in {1..100}; do
  echo "Request $i"
  echo "test" | claude
  sleep 0.1
done

# Test 2: Tokens/minute
for i in {1..10}; do
  echo "Génère exactement 1000 tokens de texte" | claude
done
```

**Capturer headers** : `x-ratelimit-*`

### 4.3 Context window limits (30 min)
**Test** :
```bash
# Générer gros prompt (100K tokens)
python3 -c "print('test ' * 50000)" > /tmp/large_prompt.txt
cat /tmp/large_prompt.txt | claude

# Observer comportement à 180K, 190K, 200K, 210K tokens
```

---

## 📝 PHASE 5 : CONSOLIDATION (Priorité FINALE)

### 5.1 Créer OpenAPI spec (2h)
**Fichier** : `claude_oauth_api.openapi.yaml`

**Structure** :
```yaml
openapi: 3.1.0
info:
  title: Claude OAuth API
  version: 2023-06-01
servers:
  - url: https://api.anthropic.com
paths:
  /v1/messages:
    post:
      security:
        - bearerAuth: []
      requestBody:
        # ...
      responses:
        200:
          description: Success
        401:
          description: Unauthorized
        # ...
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: sk-ant-oat01-*
  schemas:
    # ...
```

### 5.2 Exemples curl (1h)
**Fichier** : `examples/`

```bash
examples/
├── 01_simple_request.sh
├── 02_streaming.sh
├── 03_tool_calling.sh
├── 04_image_upload.sh
├── 05_extended_thinking.sh
├── 06_error_handling.sh
├── 07_rate_limiting.sh
└── 08_token_refresh.sh
```

### 5.3 Guide troubleshooting (1h)
**Fichier** : `TROUBLESHOOTING.md`

**Sections** :
- Token expired → Solution
- Rate limited → Solution
- 401/403 → Solution
- Streaming timeout → Solution
- Large context → Solution

### 5.4 Guide migration (30 min)
**Fichier** : `MIGRATION.md`

**API Key → OAuth** :
- Différences
- Avantages/Inconvénients
- Steps migration
- Code examples

---

## 📋 CHECKLIST ACTIONS IMMÉDIATES

### Aujourd'hui (3-4h)
- [ ] 1. Améliorer proxy (full capture)
- [ ] 2. Capturer streaming complet
- [ ] 3. Capturer erreur 401
- [ ] 4. Capturer erreur 429
- [ ] 5. Capturer tool calling
- [ ] 6. Analyser code Claude CLI
- [ ] 7. Documenter findings

### Demain (3-4h)
- [ ] 8. Capturer OAuth flow (browser)
- [ ] 9. Capturer token refresh
- [ ] 10. Tester tous modèles
- [ ] 11. Tester rate limits
- [ ] 12. Scraper docs officielles
- [ ] 13. Créer OpenAPI spec draft

### Cette semaine (2-3h)
- [ ] 14. Tests edge cases
- [ ] 15. Exemples curl complets
- [ ] 16. Troubleshooting guide
- [ ] 17. Migration guide
- [ ] 18. Review & polish

---

## 🎯 LIVRABLES FINAUX

```
/home/tincenv/analyse-claude-ai/
├── README.md                          # Index
├── PLAN_COMPLETION.md                 # Ce fichier
├── analyse_claude_api.md              # Analyse technique
│
├── specifications/
│   ├── openapi.yaml                   # Spec OpenAPI complète
│   ├── authentication.md              # OAuth flow détaillé
│   ├── streaming.md                   # SSE protocol complet
│   ├── errors.md                      # Error handling
│   ├── rate_limits.md                 # Rate limiting
│   └── models.md                      # Liste modèles + specs
│
├── examples/
│   ├── curl/                          # Exemples curl
│   ├── python/                        # SDK Python custom
│   └── javascript/                    # SDK JS custom
│
├── captures/
│   ├── requests/                      # Requêtes capturées
│   ├── responses/                     # Réponses capturées
│   ├── errors/                        # Erreurs capturées
│   └── oauth/                         # OAuth flow capturé
│
├── guides/
│   ├── QUICKSTART.md                  # Getting started
│   ├── TROUBLESHOOTING.md             # Résolution problèmes
│   ├── MIGRATION.md                   # API Key → OAuth
│   └── BEST_PRACTICES.md              # Best practices
│
└── tools/
    ├── proxy_capture_full.py          # Proxy amélioré
    ├── test_all_features.sh           # Script tests
    └── analyze_cli.sh                 # Analyse Claude CLI
```

---

## ⚡ ACTIONS PRIORITAIRES (NEXT 2H)

### Action 1 : Améliorer proxy (30 min)
**Pourquoi** : Capture actuelle tronquée à 500 chars
**Impact** : HIGH - Bloque toute la documentation streaming

**TODO** :
```python
# Créer proxy_capture_full.py
# - Remove 500 char limit
# - Parse SSE events properly
# - Save each event separately
# - Pretty print JSON
```

### Action 2 : Capturer streaming complet (20 min)
**Pourquoi** : Besoin de voir tous les event types
**Impact** : HIGH

**TODO** :
```bash
# Lancer proxy amélioré
# Faire 3 requêtes : courte, moyenne, longue
# Sauvegarder dans captures/streaming/
```

### Action 3 : Forcer erreur 401 (10 min)
**Pourquoi** : Documenter error format
**Impact** : MEDIUM

**TODO** :
```bash
# Backup credentials
cp ~/.claude/.credentials.json ~/.claude/.credentials.json.bak
# Modifier token
sed -i 's/sk-ant-oat01-.*/sk-ant-oat01-INVALID"/' ~/.claude/.credentials.json
# Test
echo "test" | ANTHROPIC_BASE_URL=http://localhost:8000 claude
# Restore
mv ~/.claude/.credentials.json.bak ~/.claude/.credentials.json
```

### Action 4 : Analyser Claude CLI (40 min)
**Pourquoi** : Trouver endpoints OAuth, rate limits
**Impact** : HIGH

**TODO** :
```bash
# Script analyze_cli.sh
NPM_ROOT=$(npm root -g)
grep -r "oauth\|/v1/" "$NPM_ROOT/claude-code/" > cli_analysis.txt
# Parser et documenter
```

### Action 5 : Documenter findings (20 min)
**Pourquoi** : Consolider ce qu'on apprend
**Impact** : MEDIUM

**TODO** :
- Mettre à jour README.md avec progression
- Créer fichiers manquants
- Structurer captures/

---

## 📊 ESTIMATION COMPLÉTUDE

### Après Phase 1 (Captures critiques)
```
[████████████████░░░░░░░░░░░░] 60%
```

### Après Phase 2 (Reverse engineering)
```
[████████████████████░░░░░░░░] 75%
```

### Après Phase 3 (Docs officielles)
```
[██████████████████████░░░░░░] 85%
```

### Après Phase 4 (Tests)
```
[████████████████████████░░░░] 90%
```

### Après Phase 5 (Consolidation)
```
[████████████████████████████] 100%
```

---

## ❓ QUESTIONS RESTANTES

1. **OAuth authorize endpoint** : Quel est l'URL exact ?
2. **Token expiration** : Exactement combien de temps ?
3. **Scopes disponibles** : Y a-t-il d'autres scopes que inference+profile ?
4. **Rate limits** : Valeurs exactes req/min et tokens/min ?
5. **Organization ID** : Comment est-il assigné ?
6. **Multi-device** : Comment les tokens sont partagés ?
7. **Révocation** : Endpoint et méthode ?

---

## 🎯 SUCCÈS = DOCUMENTATION PERMET

- ✅ Recréer client OAuth from scratch
- ✅ Comprendre tous les error cases
- ✅ Reproduire tout le flow sans Claude CLI
- ✅ Migrer d'API Key vers OAuth
- ✅ Debugger n'importe quel problème
- ✅ Créer SDK custom

---

**READY TO START ?** 🚀
