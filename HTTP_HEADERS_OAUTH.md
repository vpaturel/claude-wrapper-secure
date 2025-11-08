# 📋 HTTP Headers - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation patterns standards + Captures partielles
**État** : 65% documenté (headers réponse extrapolés)

---

## 📋 Vue d'Ensemble

Documentation complète des **headers HTTP** pour requêtes et réponses API Claude OAuth.

---

## 🔼 Headers Requête (Request)

### Headers Obligatoires

| Header | Valeur | Description |
|--------|--------|-------------|
| `Authorization` | `Bearer sk-ant-oat01-*` | Token OAuth (access token) |
| `anthropic-version` | `2023-06-01` | Version API Anthropic |
| `content-type` | `application/json` | Format body requête |

**Exemple** :
```http
POST /v1/messages?beta=true HTTP/2
Host: api.anthropic.com
Authorization: Bearer sk-ant-oat01-ABcD...
anthropic-version: 2023-06-01
content-type: application/json
```

---

### Headers Beta Features

| Header | Valeur | Description |
|--------|--------|-------------|
| `anthropic-beta` | `max-tokens-3-5-sonnet-2024-07-15=true` | Enable beta features |
| `anthropic-dangerous-direct-browser-access` | `true` | Allow browser direct access |

**Exemples beta** :
```http
anthropic-beta: max-tokens-3-5-sonnet-2024-07-15=true
anthropic-beta: prompt-caching-2024-07-31=true
anthropic-beta: extended-thinking-2024-11-01=true
```

---

### Headers SDK (Stainless)

**Générés par Claude CLI** :

| Header | Exemple | Description |
|--------|---------|-------------|
| `x-stainless-lang` | `js` | Langage SDK |
| `x-stainless-package-version` | `0.32.1` | Version package |
| `x-stainless-os` | `Linux` | OS client |
| `x-stainless-arch` | `x64` | Architecture |
| `x-stainless-runtime` | `node` | Runtime |
| `x-stainless-runtime-version` | `v20.18.0` | Version runtime |
| `x-stainless-async` | `false` | Mode async/sync |

---

### Headers HTTP Standards

| Header | Valeur typique | Description |
|--------|----------------|-------------|
| `user-agent` | `Claude Code/2.0.33` | Client identifiant |
| `accept` | `application/json` | Format accepté |
| `accept-encoding` | `gzip, deflate, br` | Encodage accepté |
| `connection` | `keep-alive` | Connexion persistante |
| `content-length` | `1234` | Taille body (bytes) |

---

### Header Application Custom

| Header | Valeur | Description |
|--------|--------|-------------|
| `x-app` | `com.anthropic.claude-code` | Application ID |

---

## 🔽 Headers Réponse (Response)

### Headers Standards SSE

**Pour streaming** (`stream: true`) :

| Header | Valeur | Description |
|--------|--------|-------------|
| `content-type` | `text/event-stream; charset=utf-8` | SSE stream |
| `transfer-encoding` | `chunked` | Chunked transfer |
| `cache-control` | `no-cache` | Pas de cache |
| `connection` | `keep-alive` | Connexion persistante |

**Exemple réponse SSE** :
```http
HTTP/2 200
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked
cache-control: no-cache
connection: keep-alive
x-request-id: req_01ABcD...

event: message_start
data: {"type":"message_start",...}
```

---

### Headers Standards JSON

**Pour non-streaming** (`stream: false`) :

| Header | Valeur | Description |
|--------|--------|-------------|
| `content-type` | `application/json; charset=utf-8` | JSON response |
| `content-length` | `2048` | Taille réponse |

---

### Headers Anthropic Custom (Extrapolés)

| Header | Exemple | Description |
|--------|---------|-------------|
| `x-request-id` | `req_01ABcDefGHijK...` | ID unique requête (tracking) |
| `anthropic-organization-id` | `org_01...` | Organization ID (si applicable) |
| `anthropic-ratelimit-requests-limit` | `60` | Limite requests/min |
| `anthropic-ratelimit-requests-remaining` | `45` | Requests restantes |
| `anthropic-ratelimit-requests-reset` | `2025-11-05T17:00:00Z` | Reset timestamp |
| `anthropic-ratelimit-tokens-limit` | `100000` | Limite tokens/min |
| `anthropic-ratelimit-tokens-remaining` | `85000` | Tokens restants |
| `anthropic-ratelimit-tokens-reset` | `2025-11-05T17:00:00Z` | Reset tokens |

**Confiance** : 50% (extrapolé, non capturé)

---

### Headers Sécurité

| Header | Valeur typique | Description |
|--------|----------------|-------------|
| `strict-transport-security` | `max-age=31536000` | Force HTTPS |
| `x-content-type-options` | `nosniff` | MIME type sniffing |
| `x-frame-options` | `DENY` | Prevent clickjacking |

---

### Headers Debug (Extrapolés)

| Header | Exemple | Description |
|--------|---------|-------------|
| `x-should-stream-response` | `true` | Force streaming response |
| `x-anthropic-trace-id` | `trace_01...` | Trace ID (debug) |

**Confiance** : 40% (pure extrapolation)

---

## 🔍 Headers par Scénario

### Scénario 1 : Requête Streaming Simple

**Request** :
```http
POST /v1/messages HTTP/2
Host: api.anthropic.com
Authorization: Bearer sk-ant-oat01-*
anthropic-version: 2023-06-01
content-type: application/json
user-agent: Claude Code/2.0.33
x-app: com.anthropic.claude-code
accept-encoding: gzip, deflate, br
connection: keep-alive
content-length: 245

{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "stream": true,
  "messages": [...]
}
```

**Response** :
```http
HTTP/2 200
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked
cache-control: no-cache
connection: keep-alive
x-request-id: req_01ABcD...
anthropic-ratelimit-requests-remaining: 59
anthropic-ratelimit-tokens-remaining: 98500

event: message_start
data: {"type":"message_start",...}
```

---

### Scénario 2 : Requête avec Beta Features

**Request** :
```http
POST /v1/messages HTTP/2
Host: api.anthropic.com
Authorization: Bearer sk-ant-oat01-*
anthropic-version: 2023-06-01
anthropic-beta: extended-thinking-2024-11-01=true
content-type: application/json
```

**Response** : Identique + thinking mode activé

---

### Scénario 3 : Erreur 429 Rate Limit

**Response** :
```http
HTTP/2 429
content-type: application/json
x-request-id: req_01ABcD...
anthropic-ratelimit-requests-limit: 60
anthropic-ratelimit-requests-remaining: 0
anthropic-ratelimit-requests-reset: 2025-11-05T17:01:00Z
retry-after: 60

{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Please retry after some time."
  }
}
```

---

### Scénario 4 : Erreur 401 Authentication

**Response** (capturé Session 2) :
```http
HTTP/2 401
content-type: application/json
x-request-id: req_01ABcD...

{
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "invalid x-api-key"
  }
}
```

---

## 📊 Comparaison OAuth vs API Key

### Headers Requête

| Header | OAuth | API Key |
|--------|-------|---------|
| **Authorization** | `Bearer sk-ant-oat01-*` | `x-api-key: sk-ant-api03-*` |
| **anthropic-version** | ✅ Identique | ✅ Identique |
| **content-type** | ✅ Identique | ✅ Identique |
| **x-app** | ✅ Présent (CLI) | ❌ Absent |
| **x-stainless-*** | ✅ SDK headers | ✅ SDK headers |

**Différence clé** : Format Authorization

---

### Headers Réponse

| Header | OAuth | API Key |
|--------|-------|---------|
| **content-type** | ✅ Identique | ✅ Identique |
| **x-request-id** | ✅ Présent | ✅ Présent |
| **anthropic-ratelimit-*** | ✅ Probablement | ✅ Confirmé |
| **anthropic-organization-id** | ❓ Incertain | ✅ Présent |

**Confiance** : 60% (headers OAuth non capturés complètement)

---

## 🎯 Best Practices Headers

### 1. Toujours Inclure Version API

```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'anthropic-version': '2023-06-01',
  'content-type': 'application/json'
};
```

---

### 2. Logger request-id pour Debug

```python
response = requests.post(url, headers=headers, json=data)
request_id = response.headers.get('x-request-id')
print(f"Request ID: {request_id}")  # Pour support debug
```

---

### 3. Respecter retry-after

```python
if response.status_code == 429:
    retry_after = int(response.headers.get('retry-after', 60))
    time.sleep(retry_after)
```

---

### 4. Parser Rate Limiting Headers

```python
remaining = int(response.headers.get('anthropic-ratelimit-requests-remaining', 999))
limit = int(response.headers.get('anthropic-ratelimit-requests-limit', 1000))

if remaining < limit * 0.1:  # < 10% restant
    print(f"⚠️ Warning: {remaining}/{limit} requests remaining")
```

---

### 5. Enable Beta Features Explicitement

```python
headers = {
    'anthropic-beta': 'extended-thinking-2024-11-01=true',
    # ou
    'anthropic-beta': 'prompt-caching-2024-07-31=true',
}
```

---

## 🚨 Headers Erreurs

### 401 Unauthorized

```http
HTTP/2 401
content-type: application/json
x-request-id: req_01...

{"type":"error","error":{"type":"authentication_error",...}}
```

**Causes** :
- Token expiré
- Token invalide
- Header Authorization manquant

---

### 429 Rate Limit

```http
HTTP/2 429
anthropic-ratelimit-requests-remaining: 0
retry-after: 60

{"type":"error","error":{"type":"rate_limit_error",...}}
```

**Actions** :
- Attendre `retry-after` secondes
- Implémenter exponential backoff

---

### 529 Overloaded

```http
HTTP/2 529
content-type: application/json

{"type":"error","error":{"type":"overloaded_error",...}}
```

**Actions** :
- Circuit breaker
- Retry après délai

---

## 🔮 Headers Avancés (Extrapolés)

### Prompt Caching (Beta)

**Si supporté OAuth** :
```http
anthropic-beta: prompt-caching-2024-07-31=true
```

**Réponse** (extrapolé) :
```http
anthropic-cache-hit: true
anthropic-cached-tokens: 5000
```

**Confiance** : 30% (feature beta, support OAuth incertain)

---

### CORS Headers (Browser)

**Si direct browser access** :
```http
anthropic-dangerous-direct-browser-access: true
```

**Réponse** :
```http
access-control-allow-origin: *
access-control-allow-methods: POST, OPTIONS
access-control-allow-headers: *
```

**Confiance** : 50% (patterns CORS standards)

---

## 📚 Headers Custom Application

### Claude CLI Specific

**Headers ajoutés par Claude CLI** :
```http
x-app: com.anthropic.claude-code
x-stainless-lang: js
x-stainless-package-version: 0.32.1
x-stainless-os: Linux
x-stainless-arch: x64
x-stainless-runtime: node
x-stainless-runtime-version: v20.18.0
user-agent: Claude Code/2.0.33
```

**Usage** : Tracking, analytics, feature flags

---

## ✅ Checklist Headers

### Request Headers
- [ ] `Authorization` présent et valide
- [ ] `anthropic-version` défini
- [ ] `content-type: application/json`
- [ ] Beta headers si features spéciales
- [ ] User-agent informatif

### Response Headers
- [ ] Parser `x-request-id` pour logs
- [ ] Vérifier `anthropic-ratelimit-*` headers
- [ ] Respecter `retry-after` si 429
- [ ] Logger headers pour debug
- [ ] Gérer SSE `content-type` si streaming

---

## 🎓 Key Takeaways

1. **Authorization OAuth** : `Bearer sk-ant-oat01-*`
2. **Version obligatoire** : `anthropic-version: 2023-06-01`
3. **SSE streaming** : `content-type: text/event-stream`
4. **request-id** : Logging critique pour debug
5. **Rate limiting headers** : Parser `anthropic-ratelimit-*`
6. **retry-after** : Respecter pour 429
7. **Beta features** : `anthropic-beta` header
8. **SDK headers** : `x-stainless-*` auto-générés

---

## 📋 Exemples Complets

### Python (Requests)

```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}',
    'anthropic-version': '2023-06-01',
    'content-type': 'application/json',
    'anthropic-beta': 'extended-thinking-2024-11-01=true'
}

response = requests.post(
    'https://api.anthropic.com/v1/messages',
    headers=headers,
    json={
        'model': 'claude-sonnet-4-5-20250929',
        'max_tokens': 1024,
        'messages': [{'role': 'user', 'content': 'Hello'}]
    }
)

# Logger headers réponse
print(f"Request ID: {response.headers.get('x-request-id')}")
print(f"Rate limit remaining: {response.headers.get('anthropic-ratelimit-requests-remaining')}")
```

---

### JavaScript (Fetch)

```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'anthropic-version': '2023-06-01',
  'content-type': 'application/json'
};

const response = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 1024,
    messages: [{role: 'user', content: 'Hello'}]
  })
});

console.log('Request ID:', response.headers.get('x-request-id'));
console.log('Remaining:', response.headers.get('anthropic-ratelimit-requests-remaining'));
```

---

### cURL

```bash
curl -X POST https://api.anthropic.com/v1/messages \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }' -v  # -v pour voir headers réponse
```

---

## 📚 Ressources

### Documentation Officielle
- Headers API : https://docs.anthropic.com/en/api/messages
- Versioning : https://docs.anthropic.com/en/api/versioning

### Standards
- SSE Specification : https://html.spec.whatwg.org/multipage/server-sent-events.html
- HTTP/2 Headers : https://httpwg.org/specs/rfc7540.html

---

**Dernière mise à jour** : 2025-11-05 16:50
**Confiance** : 65% (requête capturée, réponse extrapolée)
**Prochaine étape** : Documenter PDF processing
