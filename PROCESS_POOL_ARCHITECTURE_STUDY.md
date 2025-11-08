# 🔄 Process Pool Architecture - Étude Complète

**Date**: 2025-11-07
**Version**: v32 (étude préparatoire)
**Status**: 📚 Document d'étude

---

## 🎯 Objectif

Comprendre l'architecture du **process pool** pour implémenter un vrai keep-alive multi-requêtes.

---

## 📊 Comparaison des Architectures

### Architecture Actuelle (v31) - Single-Request Keep-Alive

```
Client Request → FastAPI
                   ↓
            Spawn Process
                   ↓
            Send Message
                   ↓
            Stream Response
                   ↓
            Destroy Process ❌
                   ↓
            Return to Client
```

**Caractéristiques**:
- ✅ Process keep-alive **pendant** la requête HTTP
- ❌ Process détruit **après** la réponse
- ❌ Pas de réutilisation entre requêtes
- ⚡ Gain: spawn overhead réduit **dans** la requête (1.2s vs 2.5s)

**Exemple**:
```
Request 1: Spawn (0.5s) → Execute (1.2s) → Destroy
Request 2: Spawn (0.5s) → Execute (1.2s) → Destroy ← Nouveau process!
Request 3: Spawn (0.5s) → Execute (1.2s) → Destroy ← Nouveau process!
```

### Architecture Cible (v32) - Multi-Request Keep-Alive

```
Client Request 1 → FastAPI
                      ↓
              Get Process from Pool
                      ↓
              (Create if not exists)
                      ↓
              Send Message
                      ↓
              Stream Response
                      ↓
              Return Process to Pool ✅
                      ↓
              Return to Client

Client Request 2 → FastAPI
                      ↓
              Get SAME Process ✅
                      ↓
              Send Message
                      ↓
              Stream Response
                      ↓
              Return Process to Pool ✅
```

**Caractéristiques**:
- ✅ Process keep-alive **entre** requêtes HTTP
- ✅ Process réutilisé pour le même user
- ✅ Context maintenu automatiquement
- ⚡ Gain: spawn overhead éliminé **entre** requêtes (0.8s vs 1.7s après request 1)

**Exemple**:
```
Request 1: Spawn (0.5s) → Execute (1.2s) → Pool ✅
Request 2: Get from Pool (0.0s) → Execute (0.8s) → Pool ✅ ← Même process!
Request 3: Get from Pool (0.0s) → Execute (0.8s) → Pool ✅ ← Même process!
```

**Performance Gain**:
```
Request 1: 1.7s (avec spawn)
Request 2: 0.8s (sans spawn) ← 2.1× plus rapide
Request 3: 0.8s (sans spawn) ← 2.1× plus rapide
```

---

## 🏗️ Composants du Process Pool

### 1. Structure de Données: `ProcessInfo`

**Rôle**: Stocker les métadonnées d'un process actif

```python
@dataclass
class ProcessInfo:
    process: subprocess.Popen        # Le process Claude CLI
    workspace_path: Path             # Workspace de l'utilisateur
    stdin_writer: threading.Thread   # Thread d'écriture stdin
    stdout_reader: threading.Thread  # Thread de lecture stdout
    event_queue: queue.Queue         # File d'événements
    last_used: float                 # Timestamp dernière utilisation
    user_id: str                     # Identifiant user (hash token)
    created_at: float                # Timestamp création
```

**Pourquoi ces champs?**
- `process`: Pour envoyer stdin et lire stdout
- `workspace_path`: Pour cleanup lors destruction
- `stdin_writer`/`stdout_reader`: Threads non-bloquants (I/O bidirectionnel)
- `event_queue`: Communication thread-safe entre threads
- `last_used`: Pour cleanup automatique (idle timeout)
- `user_id`: Isolation par utilisateur
- `created_at`: Debugging et monitoring

### 2. Pool Dictionary: `_process_pool`

**Rôle**: Mapping user_id → ProcessInfo

```python
_process_pool: Dict[str, ProcessInfo] = {}
_pool_lock = threading.Lock()  # Thread-safety
```

**Exemple**:
```python
{
    "abc123def456": ProcessInfo(
        process=<Popen pid=12345>,
        workspace_path="/workspaces/abc123def456",
        last_used=1699876543.123,
        user_id="abc123def456",
        ...
    ),
    "fed456cba987": ProcessInfo(
        process=<Popen pid=67890>,
        workspace_path="/workspaces/fed456cba987",
        last_used=1699876550.456,
        user_id="fed456cba987",
        ...
    )
}
```

**Thread-Safety**:
```python
with _pool_lock:
    if user_id in _process_pool:
        process_info = _process_pool[user_id]
```

### 3. Cleanup Thread: `_cleanup_loop()`

**Rôle**: Détruire les process idle (inactifs depuis >5min)

```python
def _cleanup_loop():
    """Background thread pour cleanup automatique."""
    while True:
        time.sleep(60)  # Check toutes les 60 secondes

        with _pool_lock:
            now = time.time()
            to_remove = []

            for user_id, info in _process_pool.items():
                idle_time = now - info.last_used

                if idle_time > 300:  # 5 minutes
                    logger.info(f"Cleanup idle process: {user_id} (idle: {idle_time:.1f}s)")
                    to_remove.append(user_id)

            for user_id in to_remove:
                _cleanup_process(user_id)
```

**Pourquoi 5 minutes?**
- ✅ Assez long pour conversations courtes (2-3 échanges rapides)
- ✅ Assez court pour éviter accumulation mémoire
- ⚙️ Configurable via variable d'environnement

---

## 🔄 Flux de Requête Détaillé

### Scenario: 3 requêtes du même user avec 2 minutes entre chaque

#### Request 1: Création du process

```
1. Client envoie Request 1
   ↓
2. FastAPI: POST /v1/messages/pooled
   ↓
3. get_or_create_process(user_id)
   ↓
4. Check pool: user_id NOT in _process_pool
   ↓
5. Spawn new Claude CLI process
   |  - Workspace: /workspaces/abc123def456
   |  - Threads: stdin_writer + stdout_reader
   |  - Queue: event_queue
   ↓
6. Add to pool: _process_pool[user_id] = ProcessInfo(...)
   ↓
7. Send message via stdin
   ↓
8. Read events from queue (streaming)
   ↓
9. Update last_used timestamp
   ↓
10. Return response to client
    (Process reste dans pool ✅)
```

**Timing**: 1.7s (spawn 0.5s + execute 1.2s)

#### Request 2: Réutilisation (2 minutes plus tard)

```
1. Client envoie Request 2 (same user)
   ↓
2. FastAPI: POST /v1/messages/pooled
   ↓
3. get_or_create_process(user_id)
   ↓
4. Check pool: user_id IN _process_pool ✅
   ↓
5. Get existing ProcessInfo
   |  - Process already running
   |  - Threads already active
   |  - Context maintained
   ↓
6. Send message via SAME stdin
   ↓
7. Read events from SAME queue
   ↓
8. Update last_used timestamp
   ↓
9. Return response to client
    (Process reste dans pool ✅)
```

**Timing**: 0.8s (no spawn, direct execute)
**Gain**: 2.1× plus rapide que Request 1

#### Request 3: Réutilisation (2 minutes plus tard)

```
Same as Request 2
```

**Timing**: 0.8s
**Gain**: 2.1× plus rapide

#### After 5 minutes idle: Cleanup automatique

```
1. Cleanup thread checks pool
   ↓
2. Find user_id with idle_time > 300s
   ↓
3. _cleanup_process(user_id)
   |  - Stop threads
   |  - Terminate process
   |  - Remove from pool
   |  - Delete workspace
   ↓
4. Pool now empty
```

---

## 🔐 Sécurité et Isolation

### Isolation par User

**Question**: Comment garantir que User A ne peut pas accéder aux données de User B?

**Réponse**: Chaque user a son propre process + workspace

```python
# User A
_process_pool["abc123def456"] = ProcessInfo(
    workspace_path="/workspaces/abc123def456",  # Permissions 0o700
    ...
)

# User B
_process_pool["fed456cba987"] = ProcessInfo(
    workspace_path="/workspaces/fed456cba987",  # Permissions 0o700
    ...
)
```

**Garanties**:
- ✅ Process séparés (isolation PID)
- ✅ Workspaces séparés (isolation filesystem)
- ✅ Credentials séparés (temporaire, 0o600)
- ✅ Aucun partage mémoire/CPU

### Token Hijacking Prevention

**Problème**: Que se passe-t-il si un attaquant devine un `user_id`?

**Réponse**: Le `user_id` est dérivé du token OAuth (SHA256)

```python
user_id = hashlib.sha256(access_token.encode()).hexdigest()[:16]
```

**Scénario d'attaque**:
1. Attacker devine `user_id` = "abc123def456"
2. Attacker envoie requête avec un faux token
3. Wrapper calcule `user_id` = SHA256(fake_token)[:16] = "xyz789uvw012"
4. Wrapper cherche dans pool: `_process_pool["xyz789uvw012"]` → **NOT FOUND**
5. Wrapper spawn NOUVEAU process pour "xyz789uvw012"
6. Attacker n'accède JAMAIS au process de la victime

**Garantie**: Impossible d'accéder au process d'un autre user sans connaître son token OAuth exact.

---

## ⚡ Performance Comparison

### Latency (Single User, 10 Requests)

| Architecture | Request 1 | Request 2-10 | Total |
|--------------|-----------|--------------|-------|
| v31 (single-request) | 1.7s | 1.7s × 9 = 15.3s | **17.0s** |
| v32 (process pool) | 1.7s | 0.8s × 9 = 7.2s | **8.9s** |
| **Gain** | - | - | **1.9× faster** |

### Memory (100 Concurrent Users)

| Architecture | Memory per User | Total Memory |
|--------------|-----------------|--------------|
| v31 (single-request) | Process destroyed after request | **~200 MB** (only during requests) |
| v32 (process pool) | Process alive 5min idle | **~500 MB** (if all idle) |

**Trade-off**: Latency vs Memory

---

## 🚧 Cas d'Usage

### ✅ Process Pool Recommandé

1. **Chat applications** (conversations >3 échanges rapides)
   - Exemple: User envoie 5 messages en 2 minutes
   - Gain: 0.8s × 4 requests économisées = **3.6s saved**

2. **Auto-retry workflows** (retry après erreur)
   - Exemple: Request échoue → Client retry immédiatement
   - Gain: Pas de re-spawn

3. **High-frequency users** (>10 requests/hour)
   - Gain: Latency constante basse (0.8s)

### ❌ Process Pool PAS Recommandé

1. **Batch processing** (1 requête isolée)
   - Pas de gain (spawn unavoidable)
   - Surcoût mémoire inutile

2. **Long idle times** (>10min entre requêtes)
   - Process détruit avant 2ème requête
   - Pas de gain

3. **Memory-constrained environments**
   - Pool consomme mémoire même idle
   - Préférer v31 (stateless)

---

## 🔍 Monitoring et Debugging

### Endpoint Stats: `GET /v1/pool/stats`

**Response Example**:
```json
{
  "pool_size": 23,
  "active_users": [
    {
      "user_id": "abc123def456",
      "idle_time": 45.2,
      "created_at": "2025-11-07T10:23:15Z",
      "last_used": "2025-11-07T10:24:00Z",
      "uptime": 102.5
    },
    {
      "user_id": "fed456cba987",
      "idle_time": 120.8,
      "created_at": "2025-11-07T10:20:10Z",
      "last_used": "2025-11-07T10:22:00Z",
      "uptime": 350.3
    }
  ],
  "cleanup_stats": {
    "last_cleanup": "2025-11-07T10:23:00Z",
    "total_cleaned": 5,
    "avg_lifetime": 245.6
  }
}
```

### Logs

```python
logger.info(f"Pool hit: user={user_id}, idle={idle_time:.1f}s")
logger.info(f"Pool miss: user={user_id}, spawning new process")
logger.info(f"Cleanup: user={user_id}, idle={idle_time:.1f}s, reason=timeout")
```

---

## 📋 Checklist Implémentation

### Phase 1: Core Logic (2h)
- [ ] Créer `ProcessInfo` dataclass
- [ ] Créer `_process_pool` dict + lock
- [ ] Implémenter `_get_or_create_process()`
- [ ] Implémenter `create_message_pooled()`
- [ ] Tester avec 2 requêtes same user

### Phase 2: Cleanup (1h)
- [ ] Implémenter `_cleanup_loop()` thread
- [ ] Implémenter `_cleanup_process()`
- [ ] Tester cleanup après 5min idle
- [ ] Vérifier workspace deletion

### Phase 3: FastAPI (1h)
- [ ] Créer endpoint `/v1/messages/pooled`
- [ ] Créer endpoint `/v1/pool/stats`
- [ ] Tester avec curl
- [ ] Vérifier streaming SSE

### Phase 4: Testing (1h)
- [ ] Test: 10 requests same user (vérifier latency)
- [ ] Test: 2 users simultanés (vérifier isolation)
- [ ] Test: Idle cleanup (vérifier timeout)
- [ ] Test: Memory usage (100 users)

**Total**: 5 heures

---

## 🎯 Décision: v31 vs v32

### Garder v31 si:
- ❌ Users font 1-2 requêtes/session
- ❌ Long idle times (>10min)
- ❌ Memory-constrained (Cloud Run min instances)

### Implémenter v32 si:
- ✅ Users font 3+ requêtes rapides
- ✅ Chat application (conversations)
- ✅ Latency critique (<1s)
- ✅ High-frequency users (>10 req/hour)

---

## 🚀 Next Steps

1. **Décision**: v31 suffisant ou v32 nécessaire?
2. **Si v32**: Implémenter selon checklist (5h)
3. **Testing**: Comparer perfs v31 vs v32
4. **Production**: Deploy v32 avec A/B testing

---

**Status**: 📚 Étude complète - Prêt pour décision
