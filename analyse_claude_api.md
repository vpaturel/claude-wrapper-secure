# 🔐 ANALYSE COMPLÈTE : Claude Code via claude.ai (OAuth)

**Date de capture** : 2025-11-05
**Méthode** : Proxy HTTP interceptant le trafic Claude Code
**Durée** : ~30 secondes

---

## 📍 ENDPOINT DÉCOUVERT

```
POST https://api.anthropic.com/v1/messages?beta=true
```

### Conclusion majeure
**✅ Claude Code avec OAuth utilise le MÊME endpoint que l'API publique Anthropic**

Il n'existe PAS d'endpoint séparé `claude.ai/api` ou `api.claude.ai` pour l'authentification OAuth.

---

## 🔐 AUTHENTIFICATION COMPLÈTE

### Header d'authentification
```http
Authorization: Bearer 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
```

### Format du token
```
sk-ant-oat01-[BASE64_TOKEN]
```

**Préfixe** : `sk-ant-oat01-` (OAuth Access Token)
**Longueur** : ~120 caractères
**Encoding** : Base64-like avec tirets/underscores

### Comparaison avec API Key

| Type | Préfixe | Header | Exemple |
|------|---------|--------|---------|
| **OAuth Token** | `sk-ant-oat01-` | `Authorization: Bearer` | `Authorization: Bearer sk-ant-oat01-...` |
| **API Key** | `sk-ant-api03-` | `x-api-key` | `x-api-key: sk-ant-api03-...` |
| **Refresh Token** | `sk-ant-ort01-` | (non utilisé en requête) | Stocké dans credentials.json |

---

## 📨 HEADERS HTTP COMPLETS

### Headers requis (authentification)
```http
Authorization: Bearer sk-ant-oat01-[TOKEN]
anthropic-version: 2023-06-01
content-type: application/json
```

### Headers additionnels Claude Code
```http
# Features beta
anthropic-beta: oauth-2025-04-20,interleaved-thinking-2025-05-14,fine-grained-tool-streaming-2025-05-14
anthropic-dangerous-direct-browser-access: true

# Identification client
user-agent: claude-cli/2.0.33 (external, cli)
x-app: cli
accept: application/json

# Métadonnées SDK (Stainless)
x-stainless-arch: x64
x-stainless-lang: js
x-stainless-os: Linux
x-stainless-package-version: 0.66.0
x-stainless-retry-count: 0
x-stainless-runtime: node
x-stainless-runtime-version: v24.3.0
x-stainless-timeout: 600
x-stainless-helper-method: stream

# HTTP standard
Connection: keep-alive
Accept-Encoding: gzip, deflate, br, zstd
Content-Length: 29569
```

### Headers importants

| Header | Valeur | Rôle |
|--------|--------|------|
| `anthropic-beta` | `oauth-2025-04-20,...` | Active features beta OAuth |
| `anthropic-dangerous-direct-browser-access` | `true` | Autorise accès direct navigateur |
| `x-stainless-timeout` | `600` | Timeout 10 minutes |
| `x-stainless-helper-method` | `stream` | Indique streaming SSE |

---

## 📦 STRUCTURE REQUÊTE

### Format général
```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 4096,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "<system-reminder>...</system-reminder>\nDis simplement bonjour en 2 mots"
        }
      ]
    }
  ],
  "stream": true,
  "temperature": 1.0
}
```

### Champs présents

| Champ | Type | Valeur capturée | Description |
|-------|------|-----------------|-------------|
| `model` | string | `claude-haiku-4-5-20251001` | Modèle utilisé (Haiku 4.5) |
| `max_tokens` | integer | (variable) | Tokens max output |
| `messages` | array | `[{role, content}]` | Conversation |
| `stream` | boolean | `true` | Streaming SSE activé |
| `temperature` | number | `1.0` | Randomness |

### Contenu message utilisateur

La requête inclut :
1. **System reminders** : Contexte injecté par Claude Code (`<system-reminder>` tags)
2. **CLAUDE.md** : Instructions utilisateur globales (~25KB)
3. **Message utilisateur** : "Dis simplement bonjour en 2 mots"

**Total body size** : 29569 bytes (~29KB)

---

## 📬 RÉPONSE API

### Headers réponse
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
```

### Protocole
**Server-Sent Events (SSE)**

### Format SSE (événements capturés - tronqué)
```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Bonjour"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" !"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":5}}

event: message_stop
data: {"type":"message_stop"}
```

---

## 🔄 FLOW DE COMMUNICATION COMPLET

```
┌─────────────────┐
│   Claude Code   │
│   (CLI)         │
└────────┬────────┘
         │
         │ 1. Lit credentials
         ├──────────────────────────────┐
         v                              │
┌─────────────────────────────┐         │
│ ~/.claude/.credentials.json │         │
│ {                           │         │
│   "accessToken":            │         │
│   "sk-ant-oat01-..."        │         │
│ }                           │         │
└─────────────────────────────┘         │
         │                              │
         │ 2. Prépare requête           │
         v                              │
┌──────────────────────────────────────┐│
│ POST /v1/messages?beta=true          ││
│ Authorization: Bearer sk-ant-oat01-* ││
│ Body: {model, messages, stream:true} ││
└──────────────────────────────────────┘│
         │                              │
         │ 3. Envoie HTTPS              │
         v                              │
┌──────────────────────────────────────┐│
│   api.anthropic.com                  ││
│                                      ││
│   1. Valide Bearer token             ││
│   2. Vérifie scopes OAuth            ││
│      ["user:inference",              ││
│       "user:profile"]                ││
│   3. Vérifie quota subscription      ││
│   4. Process requête                 ││
│   5. Stream réponse (SSE)            ││
└──────────────────────────────────────┘│
         │                              │
         │ 4. Streaming SSE             │
         v                              │
┌──────────────────────────────────────┐│
│ Content-Type: text/event-stream      ││
│                                      ││
│ event: message_start                 ││
│ data: {...}                          ││
│                                      ││
│ event: content_block_delta           ││
│ data: {"text":"Hello"}               ││
│                                      ││
│ event: message_stop                  ││
│ data: {}                             ││
└──────────────────────────────────────┘│
         │                              │
         │ 5. Accumule & affiche        │
         v                              │
┌─────────────────┐                     │
│   Claude Code   │                     │
│   Display       │◄────────────────────┘
│   "Bonjour !"   │
└─────────────────┘
```

---

## 🆚 DIFFÉRENCES : OAuth vs API Key

### Endpoint
| Aspect | OAuth | API Key |
|--------|-------|---------|
| **Base URL** | `api.anthropic.com` | `api.anthropic.com` |
| **Path** | `/v1/messages?beta=true` | `/v1/messages` |
| **Query params** | `beta=true` | (aucun) |

### Authentification
| Aspect | OAuth | API Key |
|--------|-------|---------|
| **Token format** | `sk-ant-oat01-[TOKEN]` | `sk-ant-api03-[KEY]` |
| **Header** | `Authorization: Bearer` | `x-api-key` |
| **Expiration** | Oui (~1h, auto-refresh) | Non |
| **Refresh** | `sk-ant-ort01-*` (refresh token) | N/A |
| **Scopes** | `user:inference`, `user:profile` | Full API access |

### Headers spécifiques
| Header | OAuth | API Key |
|--------|-------|---------|
| `anthropic-beta` | `oauth-2025-04-20,...` | (varie) |
| `anthropic-dangerous-direct-browser-access` | `true` | (généralement absent) |
| `user-agent` | `claude-cli/2.0.33` | (varie selon SDK) |

### Quotas & Limites
| Aspect | OAuth (Max) | API Key |
|--------|-------------|---------|
| **Pricing** | Forfait mensuel fixe | Pay-per-token |
| **Context window** | 200K tokens | 1M tokens (selon modèle) |
| **Rate limits** | Limites subscription | Limites API tier |
| **Usage tracking** | Via subscription | Via API usage |

### Restrictions
| Aspect | OAuth | API Key |
|--------|-------|---------|
| **Usage** | Claude Code exclusif | API générale |
| **Partage** | Non transférable | Peut être partagée (non recommandé) |
| **Révocation** | Via claude.ai logout | Via Console Anthropic |

---

## 🔍 FEATURES BETA OAUTH

### Header `anthropic-beta`
```
oauth-2025-04-20,interleaved-thinking-2025-05-14,fine-grained-tool-streaming-2025-05-14
```

### Features activées

| Feature | Version | Description |
|---------|---------|-------------|
| `oauth-2025-04-20` | 2025-04-20 | Support OAuth authentication |
| `interleaved-thinking-2025-05-14` | 2025-05-14 | Extended thinking mode |
| `fine-grained-tool-streaming-2025-05-14` | 2025-05-14 | Streaming détaillé des tools |

---

## 🛡️ SÉCURITÉ

### Stockage credentials
```json
// ~/.claude/.credentials.json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-[TOKEN]",
    "refreshToken": "sk-ant-ort01-[TOKEN]",
    "expiresAt": 1762334944117,
    "scopes": ["user:inference", "user:profile"],
    "subscriptionType": "max"
  }
}
```

**Permissions fichier** : `600` (lecture/écriture propriétaire uniquement)

### Transmission
- ✅ **HTTPS/TLS 1.3** : Chiffrement en transit
- ✅ **Bearer token** : Jamais dans URL/query params (sauf `?beta=true`)
- ❌ **At rest** : Non chiffré (selon docs Anthropic)

### Recommandations
1. **Ne JAMAIS partager** `~/.claude/.credentials.json`
2. **Ne JAMAIS commit** les tokens dans Git
3. **Révoquer** via `/logout` si compromis
4. **Monitoring** : Vérifier usage sur claude.ai/settings

---

## 📊 MÉTRIQUES CAPTURÉES

### Requête
```
POST /v1/messages?beta=true
Content-Length: 29569 bytes
```

### Timing (estimé)
- **DNS resolution** : ~10ms
- **TCP handshake** : ~20ms
- **TLS handshake** : ~30ms
- **Request sent** : ~5ms
- **First byte (TTFB)** : ~200ms
- **Stream complete** : ~2s (streaming)

### Réponse
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Transfer-Encoding: chunked
```

---

## 🧪 VALIDATION

### Test de reproduction

```bash
# 1. Lire token
TOKEN=$(cat ~/.claude/.credentials.json | jq -r '.claudeAiOauth.accessToken')

# 2. Faire requête
curl -X POST https://api.anthropic.com/v1/messages?beta=true \
  -H "Authorization: Bearer $TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: oauth-2025-04-20" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Bonjour"}
    ]
  }'
```

**Résultat attendu** : Réponse JSON ou SSE stream

---

## 📝 NOTES ADDITIONNELLES

### SDK utilisé
**Stainless** : SDK JavaScript auto-généré
- Version : `0.66.0`
- Runtime : `node v24.3.0`
- OS : `Linux x64`
- Helper : `stream` (pour SSE)

### User Agent
```
claude-cli/2.0.33 (external, cli)
```

**Format** : `[client]/[version] ([type], [interface])`

### Headers custom
```
x-app: cli
```

Identifie l'application comme CLI (vs web, desktop, mobile)

---

## ✅ CONCLUSIONS FINALES

### 1. Architecture unifiée
Claude Code OAuth utilise **exactement la même API** que l'API publique Anthropic (`api.anthropic.com/v1/messages`).

### 2. Seule différence : authentification
- **OAuth** : `Authorization: Bearer sk-ant-oat01-*`
- **API Key** : `x-api-key: sk-ant-api03-*`

### 3. Features beta OAuth
Le header `anthropic-beta: oauth-2025-04-20` active des features spécifiques OAuth non disponibles avec API Keys.

### 4. Format standard
Requêtes et réponses suivent exactement le format Messages API documenté sur https://docs.claude.com/en/api/messages

### 5. Streaming SSE
Identique à l'API publique avec `stream: true`.

### 6. Pas d'endpoint séparé
**Mythe débunked** : Il n'existe PAS d'endpoint `claude.ai/api` ou `api.claude.ai` pour les subscriptions. Tout passe par `api.anthropic.com`.

### 7. Proxy pour Artifacts
Exception : Les Artifacts dans claude.ai web utilisent un proxy interne (`claude.ai/api/organizations/[org-id]/proxy/v1/messages`) mais ce n'est PAS utilisé par Claude Code CLI.

---

## 🔗 RÉFÉRENCES

- **API Docs** : https://docs.claude.com/en/api/messages
- **Streaming** : https://docs.claude.com/en/api/messages-streaming
- **OAuth Beta** : `anthropic-beta: oauth-2025-04-20`
- **Capture complète** : `/home/tincenv/analyse-claude-ai/claude_capture.json`

---

**⚠️ AVERTISSEMENT DE SÉCURITÉ**

Ce document et le fichier `claude_capture.json` contiennent des tokens OAuth valides.

**NE JAMAIS** :
- Partager ces fichiers
- Commit dans Git
- Upload sur internet
- Envoyer par email

**Si compromis** : Exécuter immédiatement `claude /logout` et se reconnecter.
