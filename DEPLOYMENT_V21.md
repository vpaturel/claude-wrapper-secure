# Déploiement v21 - Clean State (Post Keep-Alive Research)

**Date**: 2025-01-07 16:09 CET
**Révision Cloud Run**: `claude-wrapper-secure-00032-6gb`
**Status**: ✅ **Deployed & Healthy**

---

## 🎯 Résumé

Déploiement de la version **v21** après avoir restauré le code à un état propre (v20.1) suite à la recherche keep-alive.

### Version v21 = v20.1 Clean State

- ✅ Architecture subprocess.run() propre (pas de keep-alive)
- ✅ Session fix préservé (vérification `_session_exists()` avant `--resume`)
- ✅ MCP support local + distant (via mcp_proxy.py)
- ✅ Security level: BALANCED
- ✅ Multi-tenant isolation 100%

---

## 📦 Ce qui a été fait

### 1. Archivage recherche keep-alive

**Fichiers archivés** dans `research_archive/keep_alive/`:
- `api_bridge_mcp.py` (12 KB) - MCP bridge HTTP + stdio
- `claude_process_manager.py` (16 KB) - Process pool manager
- `KEEP_ALIVE_ARCHITECTURE.md` (20 KB) - Documentation technique
- `test_keep_alive.py` (7.5 KB) - Tests automatisés
- `README.md` - Résumé de la recherche

**Fichier conservé** à la racine:
- `KEEP_ALIVE_RESEARCH.md` - Documentation complète des findings

### 2. Restauration code v20.1

**`claude_oauth_api_secure_multitenant.py`**:
- ✅ Supprimé `__init__` params: `enable_keep_alive`, `max_idle_time`, `cleanup_interval`
- ✅ Supprimé méthode `create_message_async()` (95 lignes)
- ✅ Supprimé méthodes `start_keep_alive()`, `shutdown()`, `get_stats()`
- ✅ Restauré `create_message()` synchrone (sans wrapper async)
- ✅ Conservé `_session_exists()` bug fix

**`server.py`**:
- ✅ Supprimé endpoint `/v1/stats`
- ✅ Supprimé lifecycle hooks `@app.on_event("startup")` et `shutdown`
- ✅ Supprimé références keep-alive

### 3. Build & Deploy

```bash
# Build image Docker
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v21

# Deploy sur Cloud Run
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v21 \
  --region=europe-west1
```

**Résultat**:
- ✅ Build réussi
- ✅ Déploiement réussi
- ✅ Health check: `{"status": "healthy", "version": "5.0-SECURE"}`

---

## 🔍 Conclusion recherche keep-alive

**Objectif**: Réduire latence de 5-15s à 0.5-2s via processus persistants
**Résultat**: ❌ **Non viable**

### Pourquoi ?

Claude CLI a 3 modes d'opération:
1. **Interactive (TTY)** - Lance MCP, attend input utilisateur
2. **--print (PIPE)** - Single-shot, exit immédiatement
3. **--print + stream-json** - Single-shot streaming, exit après 1 message

**Aucun mode daemon/keep-alive n'existe.**

### Approches testées (toutes échouées)

1. ✅ MCP bridge (HTTP + stdio) - **Bridge OK, mais Claude CLI exit**
2. ✅ Process manager avec pool - **Processus créés mais timeout**
3. ✅ PTY simulation - **Claude CLI ne lance pas MCP**
4. ✅ stream-json I/O - **Exit après 1 message même avec --verbose**
5. ✅ --continue flag - **Requiert TTY interactive, pas PIPE**

### Documentation complète

Voir `KEEP_ALIVE_RESEARCH.md` pour findings détaillés (test results, benchmarks, root cause analysis).

---

## 📊 Architecture actuelle (v21)

### Request Flow

```
Client
  ↓
FastAPI (server.py)
  ↓
SecureMultiTenantAPI.create_message()
  ↓
subprocess.run() - Claude CLI --print
  ↓
Anthropic OAuth API
  ↓
Response (JSON ou SSE stream)
```

### Performance

- **Cold start**: 5-15s (1.1s startup + 3.5s API + overhead)
- **Stateful mode**: 50-70% économie après turn 16 (compacting)
- **Network**: 97% réduction avec session_id (7.5k vs 285k tokens)

### Security

- ✅ Workspace isolation (per-user directories, 0o700)
- ✅ Credentials isolation (temporary files, 0o600)
- ✅ Tools restrictions (deny /tmp, /proc, ps)
- ✅ Secure cleanup (overwrite credentials)
- ✅ Path validation (prevent ../.. attacks)

---

## 🚀 Production Ready

**URL**: https://wrapper.claude.serenity-system.fr
**Révision**: claude-wrapper-secure-00032-6gb
**Min instances**: 1 (always warm)
**Max instances**: 100
**Resources**: 2 vCPU, 2 Gi RAM, 10 concurrent requests/instance

### Endpoints

- `GET /` - Documentation complète auto-générée
- `POST /v1/messages` - Endpoint principal
- `GET /health` - Health check
- `GET /v1/security` - Security configuration
- `GET /docs` - Swagger UI

---

## 📝 Leçons apprises

1. **Claude CLI n'est pas un daemon** - Design pour usage interactif, pas serveur
2. **subprocess.run() est correct** - Architecture actuelle optimale pour Claude CLI
3. **MCP bridge fonctionne** - Pattern réutilisable pour futurs projets
4. **Process manager fonctionne** - Code de qualité, mais use case non applicable ici

**Valeur de la recherche**: Documentation exhaustive des limitations Claude CLI + patterns réutilisables.

---

## 🔄 Rollback (si nécessaire)

```bash
# Liste révisions
gcloud run revisions list \
  --service=claude-wrapper-secure \
  --region=europe-west1

# Rollback vers v20
gcloud run services update-traffic claude-wrapper-secure \
  --to-revisions=claude-wrapper-secure-00031-xxx=100 \
  --region=europe-west1
```

---

**Deployed by**: Claude Code
**Deployment time**: ~8 minutes (build + deploy)
**Status**: ✅ Production-ready
