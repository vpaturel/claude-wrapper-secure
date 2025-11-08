# 🚨 Documentation complète - Erreurs HTTP

**Source** : Captures réelles via `proxy_capture_full.py`
**Date** : 2025-11-05
**API** : Claude OAuth (claude.ai)

---

## 🎯 Vue d'ensemble

L'API Claude retourne des erreurs HTTP standards avec un corps JSON structuré.

**Format général** :
```json
{
  "type": "error",
  "error": {
    "type": "<error_type>",
    "message": "<error_message>"
  },
  "request_id": "req_xxx"
}
```

---

## 📊 Codes d'erreur HTTP

| Code | Type | Description |
|------|------|-------------|
| `400` | `invalid_request_error` | Requête malformée |
| `401` | `authentication_error` | Token invalide/expiré |
| `403` | `permission_error` | Permission insuffisante |
| `404` | `not_found_error` | Ressource introuvable |
| `429` | `rate_limit_error` | Rate limit dépassé |
| `500` | `api_error` | Erreur interne serveur |
| `529` | `overloaded_error` | API surchargée |

---

## 🔍 Détail des erreurs capturées

### 1. Erreur 401 - Authentication Error

**Cause** : Token OAuth invalide ou expiré

**Capture complète** :
```json
{
  "timestamp": "2025-11-05T11:25:53.964556",
  "request": {
    "method": "POST",
    "path": "/v1/messages/count_tokens?beta=true",
    "headers": {
      "authorization": "Bearer sk-ant-oat01-INVALID_TOKEN_FOR_TEST",
      "anthropic-version": "2023-06-01",
      ...
    },
    "body": {
      "model": "claude-opus-4-1-20250805",
      "messages": [...]
    }
  },
  "response": {
    "status": 401,
    "headers": {
      "Content-Type": "application/json",
      "x-should-retry": "false",
      "request-id": "req_011CUpagBjj6MPSyNBqFxwfZ",
      "Server": "cloudflare",
      ...
    },
    "body": {
      "type": "error",
      "error": {
        "type": "authentication_error",
        "message": "Invalid bearer token"
      },
      "request_id": "req_011CUpagBjj6MPSyNBqFxwfZ"
    },
    "error": true
  },
  "metadata": {
    "is_streaming": false,
    "is_error": true,
    "size_bytes": 0
  }
}
```

**Headers clés** :
- `x-should-retry`: `"false"` → Ne pas retenter
- `request-id`: ID unique pour debugging
- `Content-Type`: `application/json` (pas de streaming)

**Action client** :
1. Vérifier que le token est présent
2. Vérifier que le token commence par `sk-ant-oat01-`
3. Tenter refresh token avec le refresh token `sk-ant-ort01-`
4. Si échec, redemander login via `/login`

---

### 2. Erreur 429 - Rate Limit Error

**Cause** : Trop de requêtes par minute

**Structure (non capturée, mais documentée)** :
```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded"
  },
  "request_id": "req_xxx"
}
```

**Headers rate limiting** :
```
x-ratelimit-limit-requests: 1000
x-ratelimit-remaining-requests: 0
x-ratelimit-reset-requests: 2025-11-05T11:26:00Z
x-ratelimit-limit-tokens: 100000
x-ratelimit-remaining-tokens: 0
x-ratelimit-reset-tokens: 2025-11-05T11:26:00Z
```

**Action client** :
1. Lire `x-ratelimit-reset-requests` ou `x-ratelimit-reset-tokens`
2. Attendre jusqu'à ce timestamp
3. Implémenter exponential backoff
4. Réduire le nombre de requêtes parallèles

**Retry strategy** :
```python
import time
from datetime import datetime

def handle_429(response_headers):
    """Gère l'erreur 429 avec retry intelligent"""
    reset_time = response_headers.get('x-ratelimit-reset-requests')

    if reset_time:
        # Attendre jusqu'au reset
        reset_dt = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
        wait_seconds = (reset_dt - datetime.now()).total_seconds()
        time.sleep(max(0, wait_seconds))
    else:
        # Exponential backoff par défaut
        time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, ...
```

---

### 3. Erreur 400 - Invalid Request Error

**Cause** : Payload malformé, champ manquant, type invalide

**Structure (non capturée, mais documentée)** :
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages: field required"
  },
  "request_id": "req_xxx"
}
```

**Cas courants** :
- Champ `messages` manquant
- Champ `model` invalide
- `max_tokens` négatif ou > limite
- `temperature` hors range [0, 1]
- JSON malformé

**Action client** :
1. Valider le payload avec un schéma JSON avant envoi
2. Vérifier tous les champs requis
3. Ne PAS retenter (erreur de code)

---

### 4. Erreur 500 - API Error

**Cause** : Erreur interne du serveur

**Structure** :
```json
{
  "type": "error",
  "error": {
    "type": "api_error",
    "message": "An internal server error occurred"
  },
  "request_id": "req_xxx"
}
```

**Action client** :
1. Retenter avec exponential backoff (3-5 fois max)
2. Logger le `request_id` pour signaler à Anthropic
3. Implémenter circuit breaker après N échecs

---

### 5. Erreur 529 - Overloaded Error

**Cause** : API surchargée (trop de trafic global)

**Structure** :
```json
{
  "type": "error",
  "error": {
    "type": "overloaded_error",
    "message": "API is currently overloaded"
  },
  "request_id": "req_xxx"
}
```

**Action client** :
1. Retenter avec exponential backoff (plus agressif)
2. Attendre 5-60 secondes avant retry
3. Implémenter queue côté client

---

## 🛠️ Gestion des erreurs côté client

### Algorithme de retry

```python
from typing import Optional
import time

class APIError(Exception):
    def __init__(self, status: int, error_type: str, message: str, request_id: str):
        self.status = status
        self.error_type = error_type
        self.message = message
        self.request_id = request_id

def should_retry(error: APIError) -> bool:
    """Détermine si l'erreur justifie un retry"""
    # 401, 403, 404, 400: Ne PAS retenter
    if error.status in [400, 401, 403, 404]:
        return False

    # 429, 500, 529: Retenter
    if error.status in [429, 500, 529]:
        return True

    # Défaut: pas de retry
    return False

def get_retry_delay(attempt: int, error: APIError) -> float:
    """Calcule le délai avant retry (en secondes)"""
    if error.status == 429:
        # Rate limit: exponential backoff agressif
        return min(60, 2 ** attempt)  # 1s, 2s, 4s, ..., 60s max

    elif error.status == 529:
        # Overload: attente plus longue
        return min(120, 5 * (2 ** attempt))  # 5s, 10s, 20s, ..., 120s max

    else:
        # 500 ou autre: exponential backoff standard
        return min(30, 2 ** attempt)  # 1s, 2s, 4s, ..., 30s max

async def call_api_with_retry(request, max_retries=5):
    """Appel API avec retry automatique"""
    for attempt in range(max_retries):
        try:
            response = await make_request(request)
            return response

        except APIError as e:
            if not should_retry(e):
                raise  # Pas de retry, propager l'erreur

            if attempt >= max_retries - 1:
                raise  # Max retries atteint

            delay = get_retry_delay(attempt, e)
            print(f"Retry {attempt+1}/{max_retries} après {delay}s (erreur: {e.status})")
            await asyncio.sleep(delay)
```

---

### Circuit breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func):
        if self.state == "OPEN":
            # Circuit ouvert: vérifier si timeout écoulé
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = func()
            # Succès: réinitialiser les failures
            self.failures = 0
            self.state = "CLOSED"
            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = "OPEN"

            raise
```

---

## 📊 Statistiques d'erreurs

**Fichiers capturés** : 4 erreurs 401

```bash
ls -l captures/errors/
-rw-r--r-- 1 tincenv tincenv 3.1K Nov  5 11:25 20251105_112553_error_401.json
-rw-r--r-- 1 tincenv tincenv 3.0K Nov  5 11:25 20251105_112552_error_401.json
-rw-r--r-- 1 tincenv tincenv 2.8K Nov  5 11:25 20251105_112551_error_401.json
-rw-r--r-- 1 tincenv tincenv 2.8K Nov  5 11:25 20251105_112550_error_401.json
```

---

## 📋 Checklist implémentation client

Pour gérer correctement les erreurs :

- [ ] Parser le JSON d'erreur (type, message, request_id)
- [ ] Implémenter `should_retry(status)` (429, 500, 529 → retry)
- [ ] Implémenter exponential backoff avec jitter
- [ ] Respecter les headers `x-ratelimit-*`
- [ ] Implémenter circuit breaker (5 failures → OPEN)
- [ ] Logger `request_id` pour debugging
- [ ] Gérer spécifiquement 401 → refresh token
- [ ] Gérer spécifiquement 429 → rate limit backoff
- [ ] Timeout côté client (30-60s)
- [ ] Max retries (3-5)
- [ ] Queue côté client pour 529 (overload)

---

## 🔍 Debugging

### Utiliser le request_id

Chaque erreur contient un `request_id` unique :
```json
{
  "request_id": "req_011CUpagBjj6MPSyNBqFxwfZ"
}
```

**Usage** :
1. Logger ce `request_id` côté client
2. Fournir à Anthropic pour investigation
3. Tracer la requête dans les logs serveur

### Headers utiles

```
x-should-retry: false           # Indique si retry est recommandé
request-id: req_xxx             # ID unique de la requête
x-envoy-upstream-service-time: 8  # Temps de traitement (ms)
CF-RAY: xxx-MRS                 # ID Cloudflare pour debugging
```

---

## 📖 Références

- **Captures** : `/home/tincenv/analyse-claude-ai/captures/errors/`
- **Proxy** : `proxy_capture_full.py`
- **API Anthropic** : https://docs.anthropic.com/en/api/errors

---

**Date de capture** : 2025-11-05
**Proxy version** : v2 (capture complète)
**Status** : ✅ Documentation complète des erreurs HTTP (401 capturé, autres documentés)
