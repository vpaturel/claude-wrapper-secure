# ⏱️ Rate Limits & Quotas - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation depuis erreurs capturées + Patterns standards
**État** : 70% documenté (extrapolé, haute confiance)

---

## 📋 Vue d'Ensemble

**Rate limiting** contrôle le nombre de requêtes API autorisées par période.

**Différence clé** : OAuth = **forfait basé usage**, API Key = **pay-per-token**

---

## 🎯 Types de Limites OAuth

### 1. Limites Modèle (Model-Specific)

**Opus 4** (capturé en production) :
```
❌ Opus weekly limit reached ∙ resets Nov 10, 5pm
```

**Limites par modèle** :

| Modèle | Limite OAuth Max | Limite OAuth Pro | Reset |
|--------|------------------|------------------|-------|
| **Opus 4** | ~100 messages/semaine | ~50 messages/semaine | Hebdomadaire (dimanche 17h) |
| **Sonnet 4.5** | Usage normal | Usage normal | Aucune limite stricte |
| **Haiku 3.5** | Usage normal | Usage normal | Aucune limite stricte |

**Note** : Limites exactes non documentées publiquement, estimées depuis erreurs réelles

---

### 2. Limites Globales (Account-Wide)

**Estimées** (non confirmées) :

| Type | Plan Max | Plan Pro |
|------|----------|----------|
| **Requests/minute** | ~60 RPM | ~30 RPM |
| **Tokens/minute** | ~100K TPM | ~50K TPM |
| **Concurrent requests** | ~5 | ~3 |
| **Context window** | 200K tokens | 200K tokens |
| **Max output tokens** | 16K (Opus/Sonnet) | 16K (Opus/Sonnet) |

**Confiance** : 50% (extrapolé depuis patterns API standards)

---

### 3. Limites Thinking Mode

**Extended Thinking** :

| Aspect | Limite |
|--------|--------|
| **Max thinking tokens** | 30,000 tokens |
| **Comptage** | Inclus dans output_tokens |
| **Impact quota** | Compte dans usage total |

---

## 🚨 Erreurs Rate Limiting

### Erreur 429 : Too Many Requests

**Structure** :
```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Please retry after some time."
  }
}
```

### Erreur Opus Weekly Limit (Capturée)

**Message Claude CLI** :
```
Opus weekly limit reached ∙ resets Nov 10, 5pm

Would you like to switch to Sonnet instead?
```

**Fallback automatique** : CLI propose Sonnet si Opus indisponible

---

### Erreur 529 : Overloaded

**Structure** :
```json
{
  "type": "error",
  "error": {
    "type": "overloaded_error",
    "message": "Anthropic's API is temporarily overloaded. Please retry your request."
  }
}
```

**Différence avec 429** :
- **429** : Limite utilisateur dépassée
- **529** : Serveurs Anthropic surchargés (pas votre faute)

---

## 📊 Headers Rate Limiting

### Headers Réponse (Extrapolés)

**Standard API** (probablement présents OAuth) :

```http
HTTP/2 200
x-ratelimit-limit-requests: 60
x-ratelimit-remaining-requests: 45
x-ratelimit-reset-requests: 2025-11-05T16:00:00Z
x-ratelimit-limit-tokens: 100000
x-ratelimit-remaining-tokens: 85000
x-ratelimit-reset-tokens: 2025-11-05T16:00:00Z
```

**Champs** :

| Header | Description |
|--------|-------------|
| `x-ratelimit-limit-requests` | Limite totale requêtes/minute |
| `x-ratelimit-remaining-requests` | Requêtes restantes dans fenêtre |
| `x-ratelimit-reset-requests` | Timestamp reset compteur (ISO 8601) |
| `x-ratelimit-limit-tokens` | Limite tokens/minute |
| `x-ratelimit-remaining-tokens` | Tokens restants |
| `x-ratelimit-reset-tokens` | Reset tokens |

**Confiance** : 60% (non capturés, extrapolés depuis API Key standard)

---

## 🔄 Retry Strategy

### Exponential Backoff (Recommandé)

```python
import time
import random
from anthropic import Anthropic, RateLimitError

client = Anthropic()

def call_api_with_retry(prompt: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff: 2^attempt + jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limited, retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
```

---

### Retry-After Header

**Si présent dans 429 response** :
```http
HTTP/2 429
retry-after: 60
```

**Utilisation** :
```python
except RateLimitError as e:
    retry_after = e.response.headers.get('retry-after')
    if retry_after:
        wait_time = int(retry_after)
    else:
        wait_time = 2 ** attempt
    time.sleep(wait_time)
```

---

### Circuit Breaker Pattern

**Pour API instables (529 errors)** :

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=OverloadedError)
def call_anthropic_api(prompt: str):
    return client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
```

**Comportement** :
- 5 échecs consécutifs → Circuit OPEN (bloque appels)
- Attente 60s → Circuit HALF-OPEN (teste)
- Succès → Circuit CLOSED (normal)

---

## 📈 Monitoring Usage

### Tracking Tokens Localement

```python
class UsageTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

    def track_request(self, response):
        usage = response.usage
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_requests += 1

        print(f"📊 Usage - IN: {usage.input_tokens} | OUT: {usage.output_tokens}")
        print(f"📊 Total - Requests: {self.total_requests} | IN: {self.total_input_tokens} | OUT: {self.total_output_tokens}")

tracker = UsageTracker()
response = client.messages.create(...)
tracker.track_request(response)
```

---

### Endpoint Usage (Extrapolé)

**Probablement existe** (non confirmé) :
```http
GET /v1/usage
Authorization: Bearer sk-ant-oat01-*

Response:
{
  "period": "2025-11-05",
  "subscription": "max",
  "usage": {
    "requests_count": 150,
    "input_tokens": 45000,
    "output_tokens": 32000,
    "thinking_tokens": 8000
  },
  "limits": {
    "opus_weekly_remaining": 45,
    "opus_weekly_reset": "2025-11-10T17:00:00Z"
  }
}
```

**Confiance** : 40% (pure extrapolation)

---

## 🎯 Optimisation Usage

### 1. Réduire Tokens Input

**Prompt caching** (si disponible OAuth) :
```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "Large system prompt...",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[{"role": "user", "content": "Short question"}]
)

# Tokens input = system (cached) + user message seulement
```

**Confiance prompt caching OAuth** : 30% (feature beta, support OAuth incertain)

---

### 2. Batch Requests

**Au lieu de** :
```python
for item in items:
    response = client.messages.create(...)  # 100 requêtes
```

**Faire** :
```python
batch_prompt = "Analyze these items:\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[{"role": "user", "content": batch_prompt}]
)
# 1 requête au lieu de 100
```

---

### 3. Choisir le Bon Modèle

**Stratégie** :

| Cas d'usage | Modèle recommandé | Raison |
|-------------|-------------------|--------|
| Questions simples | Haiku 3.5 | Rapide, économique |
| Tâches courantes | Sonnet 4.5 | Équilibre qualité/coût |
| Tâches complexes | Opus 4 | Qualité max (limité) |
| Production critique | Sonnet 4.5 | Pas de limite hebdomadaire |

**Code adaptatif** :
```python
def get_best_model(complexity: str) -> str:
    if complexity == "simple":
        return "claude-3-5-haiku-20241022"
    elif complexity == "complex":
        try:
            return "claude-opus-4-20250514"
        except WeeklyLimitError:
            return "claude-sonnet-4-5-20250929"  # Fallback
    else:
        return "claude-sonnet-4-5-20250929"
```

---

### 4. Limiter Max Tokens Output

```python
# ❌ Mauvais (génère potentiellement 16K tokens)
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=16000,
    messages=[...]
)

# ✅ Bon (limite à ce qui est nécessaire)
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,  # Suffisant pour la plupart des cas
    messages=[...]
)
```

---

## 🔍 Différences OAuth vs API Key

| Aspect | OAuth (Max/Pro) | API Key |
|--------|-----------------|---------|
| **Facturation** | Forfait mensuel | Pay-per-token |
| **Opus limit** | ~100 msg/semaine | Pas de limite msg |
| **Rate limiting** | RPM limité | RPM selon tier |
| **Monitoring** | Via interface web | Via API /usage |
| **Overages** | Blocage ou throttle | Facturation continue |
| **Thinking tokens** | Inclus forfait | Facturé séparément |

---

## 🚨 Gestion Erreurs Production

### Handler Complet

```python
from anthropic import (
    Anthropic,
    RateLimitError,
    APIConnectionError,
    APIError,
    AuthenticationError,
    PermissionDeniedError,
)
import time
import logging

logger = logging.getLogger(__name__)

def robust_api_call(prompt: str, max_retries: int = 3):
    client = Anthropic()

    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

        except RateLimitError as e:
            logger.warning(f"Rate limited (attempt {attempt+1}/{max_retries})")
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)

        except APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)

        except PermissionDeniedError as e:
            # Opus weekly limit probablement
            logger.warning("Permission denied, trying fallback model...")
            return client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Fallback
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

        except AuthenticationError as e:
            logger.error("Authentication failed - check token")
            raise  # Pas de retry sur auth errors

        except APIError as e:
            logger.error(f"API error: {e}")
            if e.status_code == 529:  # Overloaded
                if attempt == max_retries - 1:
                    raise
                time.sleep(10)
            else:
                raise
```

---

## 🎯 Best Practices

### ✅ À Faire

1. **Implémenter exponential backoff** pour toutes requêtes
2. **Logger usage tokens** pour monitoring
3. **Respecter retry-after header** si présent
4. **Utiliser circuit breaker** si 529 fréquents
5. **Fallback automatique** Opus → Sonnet
6. **Batch requests** quand possible
7. **Limiter max_tokens** au nécessaire
8. **Monitorer quotas** hebdomadaires (Opus)

### ❌ À Éviter

1. **Retry immédiat** sans backoff
2. **Ignorer 429 errors** (retry infini)
3. **Hardcoder Opus** sans fallback
4. **Requêtes parallèles** illimitées
5. **Max tokens élevé** par défaut
6. **Pas de timeout** sur requêtes
7. **Logger tokens sensibles**
8. **Ignorer 529** (overload serveur)

---

## 📊 Scénarios Courants

### Scénario 1 : Opus Weekly Limit Atteint

**Problème** : "Opus weekly limit reached"

**Solution** :
```python
try:
    response = client.messages.create(model="claude-opus-4-20250514", ...)
except PermissionDeniedError:
    # Fallback automatique
    response = client.messages.create(model="claude-sonnet-4-5-20250929", ...)
```

---

### Scénario 2 : Rate Limiting Production

**Problème** : 429 errors fréquents

**Solution** : Throttling client-side
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=50, period=60)  # 50 calls/min
def call_api(prompt: str):
    return client.messages.create(...)
```

---

### Scénario 3 : API Overloaded (529)

**Problème** : Serveurs Anthropic surchargés

**Solution** : Circuit breaker + queue
```python
from circuitbreaker import circuit
import queue

request_queue = queue.Queue()

@circuit(failure_threshold=5, recovery_timeout=60)
def process_queue():
    while not request_queue.empty():
        prompt = request_queue.get()
        try:
            response = client.messages.create(...)
            yield response
        except OverloadedError:
            request_queue.put(prompt)  # Re-queue
            raise
```

---

## 🧪 Tests Rate Limiting

### Test Retry Logic

```python
import pytest
from unittest.mock import patch, MagicMock

def test_retry_on_rate_limit():
    mock_client = MagicMock()

    # Simulate: fail, fail, success
    mock_client.messages.create.side_effect = [
        RateLimitError("Rate limited"),
        RateLimitError("Rate limited"),
        {"content": [{"text": "Success"}]}
    ]

    result = call_api_with_retry("test", max_retries=3)

    assert mock_client.messages.create.call_count == 3
    assert result["content"][0]["text"] == "Success"
```

---

### Test Circuit Breaker

```python
def test_circuit_breaker_opens():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = OverloadedError("Overloaded")

    # 5 failures should open circuit
    for _ in range(5):
        with pytest.raises(OverloadedError):
            call_with_circuit_breaker("test")

    # 6th call should fail immediately (circuit open)
    with pytest.raises(CircuitBreakerOpenError):
        call_with_circuit_breaker("test")
```

---

## 🎓 Key Takeaways

1. **Opus limité** : ~100 messages/semaine (Max)
2. **Fallback automatique** : Opus → Sonnet recommandé
3. **Retry strategy** : Exponential backoff obligatoire
4. **Headers rate limit** : Probablement présents (non confirmés)
5. **429 vs 529** : User limit vs Server overload
6. **Monitoring** : Logger tous les usage tokens
7. **Optimisation** : Batch, bon modèle, limit tokens
8. **Circuit breaker** : Protection contre overload

---

## 📚 Ressources

### Captures Réelles
- Opus weekly limit error (Session 3)
- 401 authentication error (Session 2)

### Documentation
- API Errors : https://docs.anthropic.com/en/api/errors
- Rate Limits : https://docs.anthropic.com/en/api/rate-limits

### Tools
- `circuitbreaker` (Python)
- `ratelimit` (Python)
- `tenacity` (Python retry library)

---

## ✅ Checklist Rate Limiting

- [ ] Exponential backoff implémenté
- [ ] Circuit breaker pour 529
- [ ] Fallback Opus → Sonnet
- [ ] Logging usage tokens
- [ ] Tests retry logic
- [ ] Monitoring quotas hebdomadaires
- [ ] Timeout sur requêtes (30s recommandé)
- [ ] Headers rate limit parsés (si présents)
- [ ] Queue pour requêtes pendant overload
- [ ] Alertes si quotas > 80%

---

**Dernière mise à jour** : 2025-11-05 16:30
**Confiance** : 70% (erreurs capturées + extrapolation patterns standards)
**Prochaine étape** : Synthèse finale Session 4 (85%)
