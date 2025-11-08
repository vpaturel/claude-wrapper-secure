# 📡 Documentation complète - Événements SSE (Server-Sent Events)

**Source** : Captures réelles via `proxy_capture_full.py`
**Date** : 2025-11-05
**API** : Claude OAuth (claude.ai)

---

## 🎯 Vue d'ensemble

L'API Claude utilise le protocole **Server-Sent Events (SSE)** pour le streaming des réponses.

**Format général** :
```
event: <type>
data: <json>

```

**Content-Type** : `text/event-stream; charset=utf-8`

---

## 📊 Types d'événements capturés

Dans une réponse streaming complète, on observe **7 types d'événements** :

| Événement | Count (exemple) | Description |
|-----------|-----------------|-------------|
| `message_start` | 1 | Début du message (métadonnées, usage tokens) |
| `content_block_start` | 2 | Début d'un bloc de contenu (thinking ou text) |
| `content_block_delta` | 168 | Fragments de contenu (thinking ou text) |
| `content_block_stop` | 2 | Fin d'un bloc de contenu |
| `message_delta` | 1 | Mise à jour du message (stop_reason, usage final) |
| `message_stop` | 1 | Fin du message |
| `ping` | 1 | Keep-alive (optionnel) |

**Total** : ~176 événements pour une réponse moyenne

---

## 📝 Détail des événements

### 1. `message_start`

**Premier événement** envoyé, contient les métadonnées du message.

```json
{
  "event": "message_start",
  "data": {
    "type": "message_start",
    "message": {
      "model": "claude-sonnet-4-5-20250929",
      "id": "msg_01XH7kH8Ex6o4o7RwgiBrSuK",
      "type": "message",
      "role": "assistant",
      "content": [],
      "stop_reason": null,
      "stop_sequence": null,
      "usage": {
        "input_tokens": 8,
        "cache_creation_input_tokens": 10426,
        "cache_read_input_tokens": 0,
        "cache_creation": {
          "ephemeral_5m_input_tokens": 10426,
          "ephemeral_1h_input_tokens": 0
        },
        "output_tokens": 2,
        "service_tier": "standard"
      }
    }
  }
}
```

**Champs clés** :
- `message.id` : ID unique du message (ex: `msg_01XH...`)
- `message.model` : Modèle utilisé
- `message.role` : Toujours `"assistant"`
- `message.usage` : Tokens input (avec cache)
- `message.content` : Tableau vide initialement

---

### 2. `content_block_start`

**Début d'un bloc de contenu**. Il peut y avoir **plusieurs blocs** dans un message :
- Bloc 0 : `type: "thinking"` (si extended thinking activé)
- Bloc 1 : `type: "text"` (réponse visible)
- Bloc N : `type: "tool_use"` (si tool calling)

#### Exemple : Bloc thinking

```json
{
  "event": "content_block_start",
  "data": {
    "type": "content_block_start",
    "index": 0,
    "content_block": {
      "type": "thinking",
      "thinking": "",
      "signature": ""
    }
  }
}
```

#### Exemple : Bloc text

```json
{
  "event": "content_block_start",
  "data": {
    "type": "content_block_start",
    "index": 1,
    "content_block": {
      "type": "text",
      "text": ""
    }
  }
}
```

**Champs clés** :
- `data.index` : Index du bloc (0, 1, 2, ...)
- `data.content_block.type` : Type du bloc (`thinking`, `text`, `tool_use`)

---

### 3. `content_block_delta`

**Fragments de contenu** envoyés progressivement. C'est le type d'événement le plus fréquent.

#### Exemple : Thinking delta

```json
{
  "event": "content_block_delta",
  "data": {
    "type": "content_block_delta",
    "index": 0,
    "delta": {
      "type": "thinking_delta",
      "thinking": "The user is asking me to "
    }
  }
}
```

#### Exemple : Text delta

```json
{
  "event": "content_block_delta",
  "data": {
    "type": "content_block_delta",
    "index": 1,
    "delta": {
      "type": "text_delta",
      "text": "I'm ready to assist"
    }
  }
}
```

**Champs clés** :
- `data.index` : Index du bloc concerné
- `data.delta.type` : Type de delta (`thinking_delta`, `text_delta`, `input_json_delta`)
- `data.delta.thinking` ou `data.delta.text` : Fragment de contenu

**Note** : Pour reconstruire le texte complet, il faut **concaténer tous les deltas** du même index.

---

### 4. `content_block_stop`

**Fin d'un bloc de contenu**.

```json
{
  "event": "content_block_stop",
  "data": {
    "type": "content_block_stop",
    "index": 0
  }
}
```

**Champs clés** :
- `data.index` : Index du bloc qui se termine

**Ordre** : Un `content_block_stop` est envoyé pour chaque `content_block_start` (même index).

---

### 5. `message_delta`

**Mise à jour du message** avec la raison d'arrêt et l'usage final des tokens.

```json
{
  "event": "message_delta",
  "data": {
    "type": "message_delta",
    "delta": {
      "stop_reason": "end_turn",
      "stop_sequence": null
    },
    "usage": {
      "input_tokens": 8,
      "cache_creation_input_tokens": 10426,
      "cache_read_input_tokens": 0,
      "output_tokens": 501
    }
  }
}
```

**Champs clés** :
- `data.delta.stop_reason` : Raison d'arrêt
  - `"end_turn"` : Fin naturelle
  - `"max_tokens"` : Limite de tokens atteinte
  - `"stop_sequence"` : Séquence stop rencontrée
  - `"tool_use"` : Tool calling demandé
- `data.usage.output_tokens` : **Tokens de sortie finaux**

---

### 6. `message_stop`

**Dernier événement** du stream, indique la fin du message.

```json
{
  "event": "message_stop",
  "data": {
    "type": "message_stop"
  }
}
```

**Note** : Aucun champ supplémentaire. Signal de fermeture du stream.

---

### 7. `ping`

**Keep-alive optionnel** envoyé périodiquement pour maintenir la connexion.

```json
{
  "event": "ping",
  "data": {
    "type": "ping"
  }
}
```

**Note** : Peut être ignoré par le client. Sert uniquement à éviter les timeouts.

---

## 🔄 Séquence complète (exemple)

Voici l'ordre typique des événements pour une réponse avec thinking mode :

```
1. message_start              (métadonnées, id, usage initial)
2. content_block_start (0)    (début bloc thinking)
3. content_block_delta (0)    (thinking fragment 1)
4. content_block_delta (0)    (thinking fragment 2)
   ...
   content_block_delta (0)    (thinking fragment N)
5. content_block_stop (0)     (fin bloc thinking)
6. content_block_start (1)    (début bloc text)
7. content_block_delta (1)    (text fragment 1)
8. content_block_delta (1)    (text fragment 2)
   ...
   content_block_delta (1)    (text fragment M)
9. content_block_stop (1)     (fin bloc text)
10. message_delta             (stop_reason, usage final)
11. message_stop              (fin)
12. ping                      (optionnel, keep-alive)
```

---

## 🧩 Reconstruction du contenu

### Algorithme de reconstruction

```python
def reconstruct_message(events: list) -> dict:
    """Reconstruit le message complet depuis les événements SSE"""
    message_id = None
    blocks = {}  # {index: {type, content}}

    for event in events:
        if event['event'] == 'message_start':
            message_id = event['data']['message']['id']

        elif event['event'] == 'content_block_start':
            index = event['data']['index']
            block_type = event['data']['content_block']['type']
            blocks[index] = {'type': block_type, 'content': ''}

        elif event['event'] == 'content_block_delta':
            index = event['data']['index']
            delta = event['data']['delta']

            if delta['type'] == 'thinking_delta':
                blocks[index]['content'] += delta['thinking']
            elif delta['type'] == 'text_delta':
                blocks[index]['content'] += delta['text']

        elif event['event'] == 'message_delta':
            stop_reason = event['data']['delta']['stop_reason']
            output_tokens = event['data']['usage']['output_tokens']

    return {
        'id': message_id,
        'blocks': blocks,
        'stop_reason': stop_reason,
        'output_tokens': output_tokens
    }
```

---

## 📊 Statistiques (capture réelle)

**Fichier** : `20251105_112245_stream.json`

```
Total événements     : 176
message_start        : 1
content_block_start  : 2
content_block_delta  : 168
  - thinking_delta   : 81  (index 0)
  - text_delta       : 87  (index 1)
content_block_stop   : 2
message_delta        : 1
message_stop         : 1
ping                 : 1

Taille totale        : 25 KB
Output tokens        : 501
```

---

## 🔍 Extended Thinking Mode

**Détection** : Présence d'un `content_block_start` avec `type: "thinking"`

**Structure** :
1. Bloc 0 = thinking (raisonnement interne)
2. Bloc 1 = text (réponse visible)

**Exemple de thinking** :
```
"The user is asking me to do a \"warmup\" - this seems like they want me to..."
```

**Activation** : Automatique avec modèle `opus` ou paramètre `thinking: {type: "enabled"}`

---

## 🛠️ Tool Calling

**Structure** (non capturé encore, mais extrapolé) :

```json
{
  "event": "content_block_start",
  "data": {
    "type": "content_block_start",
    "index": 1,
    "content_block": {
      "type": "tool_use",
      "id": "toolu_xxx",
      "name": "get_weather",
      "input": {}
    }
  }
}
```

Suivi de `content_block_delta` avec `type: "input_json_delta"`.

---

## 📋 Checklist implémentation client

Pour implémenter un client SSE complet :

- [ ] Parser format `event: xxx` + `data: {...}`
- [ ] Gérer `message_start` (récupérer ID, usage)
- [ ] Gérer `content_block_start` (initialiser blocs)
- [ ] Gérer `content_block_delta` (concaténer contenu)
- [ ] Gérer `content_block_stop` (finaliser blocs)
- [ ] Gérer `message_delta` (stop_reason, usage final)
- [ ] Gérer `message_stop` (fermer stream)
- [ ] Ignorer `ping` (ou rafraîchir timeout)
- [ ] Supporter plusieurs blocs (thinking + text + tools)
- [ ] Gérer les erreurs (event `error`)

---

## 🚨 Gestion des erreurs

**Format erreur SSE** (non capturé, mais standard) :

```json
{
  "event": "error",
  "data": {
    "type": "error",
    "error": {
      "type": "overloaded_error",
      "message": "API is currently overloaded"
    }
  }
}
```

**Types d'erreurs possibles** :
- `invalid_request_error`
- `authentication_error`
- `permission_error`
- `not_found_error`
- `rate_limit_error`
- `api_error`
- `overloaded_error`

---

## 📖 Références

- **Captures** : `/home/tincenv/analyse-claude-ai/captures/streaming/`
- **Proxy** : `proxy_capture_full.py`
- **API Anthropic** : https://docs.anthropic.com/en/api/messages-streaming

---

**Date de capture** : 2025-11-05
**Proxy version** : v2 (capture complète)
**Status** : ✅ Documentation complète des événements SSE
