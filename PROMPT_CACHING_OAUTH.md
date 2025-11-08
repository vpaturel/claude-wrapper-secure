# 💾 Prompt Caching - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation depuis API Key + Beta features
**État** : 35% documenté (support OAuth très incertain)

---

## 📋 Vue d'Ensemble

**Prompt Caching** permet de **mettre en cache des parties du prompt** pour :
- Réduire latence (jusqu'à 85%)
- Réduire coût tokens input (jusqu'à 90%)
- Réutiliser contexte long (docs, code, instructions)

**Support OAuth** : ⚠️ **TRÈS INCERTAIN** (beta feature, probablement non disponible)

---

## 🎯 Fonctionnement (Théorique OAuth)

### Concept

**Idée** : Cacher portions du prompt réutilisées fréquemment

**Scénarios** :
- System prompt identique (instructions longues)
- Documentation technique (docs API, codebase)
- Contexte partagé (conversation multi-tours)

---

## 🔧 Structure Requête (Extrapolée)

### Header Beta

```http
anthropic-beta: prompt-caching-2024-07-31=true
```

### Format cache_control

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "system": [
    {
      "type": "text",
      "text": "You are an AI assistant specialized in Python. Here is the complete Python documentation: [LARGE DOC...]",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "How do I use asyncio?"
    }
  ]
}
```

**Confiance** : 30% (structure API Key, support OAuth inconnu)

---

## 📊 Breakpoints Cache

### Règles (Extrapolées)

**Cache créé si** :
- `cache_control` présent
- Contenu > 1024 tokens (minimum)
- Durée : 5 minutes TTL

**Breakpoints** : Points où cache est stocké

```json
{
  "system": [
    {
      "type": "text",
      "text": "[PARTIE 1 - NON CACHÉE]"
    },
    {
      "type": "text",
      "text": "[PARTIE 2 - CACHÉE]",
      "cache_control": {"type": "ephemeral"}
    }
  ]
}
```

**Seule la dernière partie est cachée**

---

## 💰 Économies (Estimées OAuth)

### Coût Tokens

**Sans cache** :
```
Input : 10,000 tokens × $3/M = $0.03
```

**Avec cache (1ère requête)** :
```
Input (write cache) : 10,000 tokens × $3.75/M = $0.0375 (+25% première fois)
```

**Avec cache (requêtes suivantes)** :
```
Input (cache hit) : 10,000 tokens × $0.30/M = $0.003 (90% reduction !)
```

**OAuth forfait** : Coût probablement **inclus** (pas de facturation séparée)

---

## 🎯 Use Cases (Si Supporté OAuth)

### 1. System Prompt Long

```json
{
  "system": [
    {
      "type": "text",
      "text": "You are an expert assistant... [5000 tokens instructions]",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [{"role": "user", "content": "Question 1"}]
}
```

**Requête suivante** : Réutilise cache system prompt

---

### 2. Documentation Technique

```json
{
  "system": [
    {
      "type": "text",
      "text": "Here is the API documentation:\n\n[20,000 tokens doc]",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [{"role": "user", "content": "How do I authenticate?"}]
}
```

---

### 3. Codebase Context

```json
{
  "system": [
    {
      "type": "text",
      "text": "Codebase:\n\n```python\n[15,000 tokens code]\n```",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [{"role": "user", "content": "Where is the auth function?"}]
}
```

---

## 📈 Headers Cache (Extrapolés)

### Request

```http
POST /v1/messages HTTP/2
anthropic-beta: prompt-caching-2024-07-31=true
```

### Response (Extrapolée)

**Headers cache** :
```http
anthropic-cache-creation-input-tokens: 10000
anthropic-cache-read-input-tokens: 0
```

**Usage object** :
```json
{
  "usage": {
    "input_tokens": 50,
    "cache_creation_input_tokens": 10000,
    "cache_read_input_tokens": 0,
    "output_tokens": 200
  }
}
```

**Requête suivante (cache hit)** :
```json
{
  "usage": {
    "input_tokens": 50,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 10000,
    "output_tokens": 180
  }
}
```

---

## 🚨 Limites Cache (Extrapolées)

| Aspect | Limite |
|--------|--------|
| **TTL (Time To Live)** | 5 minutes |
| **Minimum tokens** | 1024 tokens |
| **Maximum tokens** | ~100,000 tokens |
| **Breakpoints max** | ~4 breakpoints |

**Confiance** : 20% (extrapolé depuis API Key)

---

## 🔍 Différences OAuth vs API Key

| Aspect | OAuth | API Key |
|--------|-------|---------|
| **Support** | ❓ **TRÈS INCERTAIN** | ✅ Confirmé (beta) |
| **Header beta** | `anthropic-beta` (extrapolé) | `anthropic-beta: prompt-caching-2024-07-31=true` ✅ |
| **Structure** | Identique (si supporté) | `cache_control: {type: ephemeral}` ✅ |
| **Coût** | Inclus forfait ? | Facturé séparément ✅ |
| **TTL** | 5 min ? | 5 min ✅ |

**Recommandation** : **Tester avec OAuth** pour confirmer (probablement NON disponible)

---

## 🧪 Test Support (À Faire)

### Test Prompt Caching OAuth

```python
import anthropic

client = anthropic.Anthropic()  # OAuth

try:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        system=[
            {
                "type": "text",
                "text": "You are a helpful assistant. " * 500,  # > 1024 tokens
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": "Hello"}],
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31=true"}
    )

    # Vérifier usage
    usage = response.usage
    if hasattr(usage, 'cache_creation_input_tokens'):
        print("✅ Prompt caching supporté OAuth !")
        print(f"Cache created: {usage.cache_creation_input_tokens} tokens")
    else:
        print("❌ Prompt caching NON supporté OAuth")

except Exception as e:
    print(f"❌ Erreur: {e}")
```

---

## 🎯 Alternative si Non Supporté

### Gérer Cache Côté Client

```python
import hashlib

class ClientSideCache:
    def __init__(self):
        self.cache = {}

    def get_cached_response(self, prompt: str):
        key = hashlib.md5(prompt.encode()).hexdigest()
        return self.cache.get(key)

    def cache_response(self, prompt: str, response: str):
        key = hashlib.md5(prompt.encode()).hexdigest()
        self.cache[key] = response

cache = ClientSideCache()

# Utilisation
cached = cache.get_cached_response(user_prompt)
if cached:
    return cached
else:
    response = client.messages.create(...)
    cache.cache_response(user_prompt, response.content[0].text)
    return response
```

**Avantages** :
- Fonctionne toujours
- Contrôle total TTL
- Pas de coût additionnel

**Inconvénients** :
- Latence non réduite (toujours requête API)
- Pas d'économie tokens réels

---

## 📊 Performance Estimée

### Sans Cache

```
Latence : 3000ms
Tokens  : 10,050 input (10K system + 50 user)
```

### Avec Cache (1ère requête)

```
Latence : 3200ms (+7% write cache)
Tokens  : 10,050 input (cache write)
```

### Avec Cache (requêtes suivantes)

```
Latence : 500ms (-85% !)
Tokens  : 50 input (90% reduction)
```

---

## 🎓 Key Takeaways

1. **Support OAuth très incertain** (beta feature)
2. **90% réduction coût** input tokens (si supporté)
3. **85% réduction latence** (cache hit)
4. **TTL 5 minutes** (revalidation après)
5. **Minimum 1024 tokens** pour cache
6. **System prompt** = use case principal
7. **Test recommandé** avant déploiement production
8. **Alternative** : Cache côté client (toujours fonctionnel)

---

## ✅ Checklist (Si Supporté)

- [ ] Tester support OAuth avec header beta
- [ ] Valider portion cachée > 1024 tokens
- [ ] Utiliser `cache_control: {type: ephemeral}`
- [ ] Parser `cache_creation_input_tokens` dans usage
- [ ] Monitorer cache hit rate
- [ ] Documenter TTL (5 min)
- [ ] Fallback si cache non disponible
- [ ] Logger économies tokens

---

## 📚 Ressources

### Documentation Officielle
- Prompt Caching : https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Beta Features : https://docs.anthropic.com/en/api/versioning

### Comparaison
- **OpenAI** : Pas de prompt caching natif
- **Google** : Context caching (similaire)
- **Anthropic** : Prompt caching (beta API Key)

---

**Dernière mise à jour** : 2025-11-05 17:05
**Confiance** : 35% (extrapolé API Key, support OAuth très incertain)
**Action critique** : **TESTER SUPPORT OAUTH** (probablement NON disponible)
**Prochaine étape** : Synthèse finale Session 5
