# 🔒 Claude OAuth API Wrapper - Production Multi-Tenant

**Projet** : Claude Secure Multi-Tenant API Wrapper
**Localisation** : `/home/tincenv/wrapper-claude/`
**État** : Production-Ready v5.0-SECURE
**Déployé** : https://wrapper.claude.serenity-system.fr

---

## 📍 INFRASTRUCTURE GCP

### Projet GCP
```
Projet ID    : claude-476509
Nom          : Claude
Project Number: 778234387929
Owner        : vincent.paturel@serenity-system.fr
```

### Service Cloud Run
```
Service      : claude-wrapper-secure
Région       : europe-west1 (Belgique)
URL directe  : https://claude-wrapper-secure-mrrlk6xxya-ew.a.run.app
Domaine      : https://wrapper.claude.serenity-system.fr
```

### Configuration
```yaml
CPU: 2 vCPU
RAM: 2 Gi
Concurrency: 10 requêtes/instance
Min instances: 1 (always warm)
Max instances: 100
Startup CPU boost: Activé
Port: 8080
```

### Architecture complète du projet
```
claude-476509/
├── claude-frontend          → claude.serenity-system.fr
├── claude-backend           → api.claude.serenity-system.fr
└── claude-wrapper-secure    → wrapper.claude.serenity-system.fr
```

---

## 🏗️ ARCHITECTURE DU WRAPPER

### Structure du code
```
/home/tincenv/wrapper-claude/
├── server.py                              # FastAPI server (721 lignes)
├── claude_oauth_api_secure_multitenant.py # Client API sécurisé (804 lignes)
├── requirements.txt                       # Dépendances Python
├── Dockerfile                             # Container definition
├── deploy.sh                              # Script de déploiement
│
├── Documentation (50+ fichiers)
│   ├── README.md                          # Vue d'ensemble (97% complété)
│   ├── SECURITY_JOURNEY_COMPLETE.md       # Parcours sécurité
│   ├── PRODUCTION_SECURITY_GUIDE.md       # Guide sécurité production
│   ├── PROJECT_OVERVIEW.txt               # Vue d'ensemble projet
│   ├── QUICK_START.md                     # Guide démarrage
│   └── ... (40+ autres docs)
│
└── Versions précédentes
    ├── claude_oauth_api.py                # v1 - Simple
    ├── claude_oauth_api_multi_tenant.py   # v3 - Multi-tenant
    ├── claude_oauth_api_ultimate.py       # v4 - 19 features
    └── streaming_bidirectional.py         # v4.1 - Streaming
```

### Stack technique
- **Framework** : FastAPI + Uvicorn
- **Client** : Subprocess wrapper Claude CLI
- **Sécurité** : 5 couches d'isolation
- **Cloud** : Cloud Run (gVisor compatible)

---

## 🚀 DÉPLOIEMENT

### Déploiement rapide (1 commande)
```bash
cd /home/tincenv/wrapper-claude

# Build + Deploy en une commande
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v8 \
  --project=claude-476509 && \
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v8 \
  --project=claude-476509 \
  --region=europe-west1 \
  --platform=managed
```

### Déploiement détaillé
```bash
# 1. Build l'image Docker
gcloud builds submit \
  --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v8 \
  --project=claude-476509

# 2. Deploy sur Cloud Run
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v8 \
  --project=claude-476509 \
  --region=europe-west1 \
  --platform=managed \
  --memory=2Gi \
  --cpu=2 \
  --concurrency=10 \
  --min-instances=1 \
  --max-instances=100

# 3. Vérifier le déploiement
curl -s https://wrapper.claude.serenity-system.fr/health | jq '.'
```

### Tags de versions
```
v1-v2: Versions de développement
v3: Multi-tenant basique
v4: Ultimate (19 features)
v5: Secure (isolation 100%)
v6: Optimisations
v7-session-doc: Documentation sessions (ACTUELLE EN PROD)
v8+: Nouvelles versions (token_consumption_comparison, etc.)
```

---

## 🔒 SÉCURITÉ MULTI-TENANT

### Isolation 100% entre utilisateurs

**5 couches de protection** :

1. **Workspace Isolation** : Directories per-user (0o700)
```
/workspaces/
├── abc123def456/  (User A - drwx------)
└── fed456cba987/  (User B - drwx------)
```

2. **Credentials Isolation** : Temporary files (0o600)
```python
temp_dir = mkdtemp(prefix=f"claude_user_{secrets.token_hex(16)}_")
creds_file.chmod(0o600)  # Owner only
```

3. **Tools Restrictions** : 3 niveaux (PARANOID/BALANCED/DEVELOPER)
```python
"deny": [
    "Bash(ls:/tmp/*)",    # Pas d'accès /tmp
    "Bash(ps:*)",         # Pas de ps
    "Read(/proc/*)",      # Pas /proc autres users
]
```

4. **Secure Cleanup** : Overwrite avant delete
```python
creds_file.write_bytes(b'\x00' * file_size)  # Overwrite
shutil.rmtree(temp_home)
```

5. **Path Validation** : Injection prevention
```python
if ".." in user_id or "/" in user_id:
    raise SecurityError()
```

### Niveau de sécurité actuel
```
Production: BALANCED (recommandé)
- Token isolation: 100%
- Code isolation: 100%
- Workspace isolation: per-user
```

---

## 📚 ENDPOINTS API

### POST /v1/messages
**Endpoint principal** - Envoyer messages à Claude

```bash
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {
      "access_token": "sk-ant-oat01-...",
      "refresh_token": "sk-ant-ort01-...",
      "expires_at": 1762444195608,
      "scopes": ["user:inference", "user:profile"],
      "subscription_type": "max"
    },
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "model": "sonnet",
    "stream": false,
    "session_id": "optional-uuid-v4"
  }'
```

**Paramètres** :
- `oauth_credentials` (required) : Credentials OAuth complètes
- `messages` (required) : Historique conversation
- `model` (optional) : opus / sonnet / haiku (default: sonnet)
- `stream` (optional) : true/false (default: false)
- `session_id` (optional) : UUID v4 pour sessions stateful
- `mcp_servers` (optional) : MCP servers custom

### GET /
**Documentation complète** - API auto-documentée

```bash
curl -s https://wrapper.claude.serenity-system.fr/ | jq '.'
```

Retourne :
- Liste endpoints
- Paramètres détaillés
- Exemples curl
- Patterns de conversation
- Comparaison tokens (stateless vs stateful)
- Configuration sécurité

### GET /health
**Health check**

```bash
curl -s https://wrapper.claude.serenity-system.fr/health
# {"status": "healthy", "version": "5.0-SECURE", "security_level": "BALANCED"}
```

### GET /v1/security
**Configuration sécurité**

```bash
curl -s https://wrapper.claude.serenity-system.fr/v1/security | jq '.'
```

### GET /docs
**Swagger UI** - Documentation interactive

```
https://wrapper.claude.serenity-system.fr/docs
```

---

## 🎯 FEATURES PRINCIPALES

### 1. Multi-Tenant OAuth External
- Chaque user utilise son propre token OAuth
- Pas de pooling de tokens
- Facturation individuelle

### 2. Session Management
**Stateless** : Envoyer historique complet
```json
{"messages": [Q1, A1, Q2, A2, Q3]}
```

**Stateful** : Contexte automatique
```json
{"session_id": "uuid", "messages": [Q_new]}
```

**Économies** :
- Network: 97% (7.5k vs 285k tokens)
- API cost après compacting: 50-70% (turns 16+)

### 3. MCP Servers Custom (Local & Remote)
Configuration per-user, isolation workspace

**Supports 2 types:**

**Local MCP (subprocess):**
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspaces"],
      "env": {"DEBUG": "true"}
    }
  }
}
```

**Remote MCP (HTTP/SSE):**
```json
{
  "mcp_servers": {
    "custom-api": {
      "url": "https://mcp.example.com/sse",
      "transport": "sse",
      "auth_type": "jwt",
      "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
}
```

**Authentification types:** jwt, oauth, bearer
**Transport types:** sse, http

### 4. Model Selection
- opus : claude-opus-4-20250514
- sonnet : claude-sonnet-4-5-20250929 (default)
- haiku : claude-3-5-haiku-20241022

### 5. Streaming Support
SSE (Server-Sent Events) pour réponses temps réel

---

## 🔧 DÉVELOPPEMENT LOCAL

### Tester localement
```bash
cd /home/tincenv/wrapper-claude

# Installer dépendances
pip install -r requirements.txt

# Lancer serveur
python server.py
# → http://localhost:8080

# Tester
curl -s http://localhost:8080/health
```

### Vérifier sécurité
```bash
# Vérifier isolation workspace
python -c "
from claude_oauth_api_secure_multitenant import SecureMultiTenantAPI
api = SecureMultiTenantAPI('/tmp/test_workspaces')
workspace = api.get_workspace_path('sk-ant-oat01-test')
print(f'Workspace: {workspace}')
print(f'Permissions: {oct(workspace.stat().st_mode)[-3:]}')
"
```

---

## 📊 MONITORING & LOGS

### Voir les logs Cloud Run
```bash
# Derniers logs
gcloud run services logs read claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1 \
  --limit=50

# Logs en temps réel
gcloud run services logs tail claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1
```

### Métriques
```bash
# Révisions
gcloud run revisions list \
  --service=claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1

# Trafic
gcloud run services describe claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1 \
  --format="get(status.traffic)"
```

---

## 🚨 TROUBLESHOOTING

### Service ne répond pas
```bash
# 1. Vérifier status
gcloud run services describe claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1

# 2. Vérifier logs
gcloud run services logs read claude-wrapper-secure \
  --project=claude-476509 --region=europe-west1 --limit=20

# 3. Redéployer dernière bonne version
gcloud run services update-traffic claude-wrapper-secure \
  --to-revisions=claude-wrapper-secure-00009-szv=100 \
  --project=claude-476509 --region=europe-west1
```

### Erreur 500
Vérifier :
- Claude CLI installé dans container
- Permissions workspace
- Variables d'environnement

### Performance dégradée
```bash
# Augmenter instances
gcloud run services update claude-wrapper-secure \
  --min-instances=3 \
  --max-instances=200 \
  --project=claude-476509 --region=europe-west1
```

---

## 📝 FICHIERS CLÉS À CONSULTER

### Pour comprendre le code
1. `server.py` - Serveur FastAPI, endpoints
2. `claude_oauth_api_secure_multitenant.py` - Logique isolation
3. `SECURITY_JOURNEY_COMPLETE.md` - Parcours sécurité
4. `PROJECT_OVERVIEW.txt` - Vue d'ensemble complète

### Pour utiliser l'API
1. `README.md` - Documentation générale
2. `QUICK_START.md` - Démarrage rapide
3. `TROUBLESHOOTING_FAQ.md` - FAQ problèmes
4. GET https://wrapper.claude.serenity-system.fr/ - Doc auto-générée

---

## 🎓 CONTEXTE PROJET

### Objectif initial
Documenter l'API Claude OAuth (claude.ai) par reverse engineering

### Évolution
Documentation (97%) → Wrapper simple → Multi-tenant → **Production sécurisée**

### Statistiques
- **Code** : ~3,000 lignes Python
- **Documentation** : ~2,500 lignes (93 KB)
- **Fichiers** : 15 code + 50+ docs
- **État** : Production-ready, 97% complété

### Innovation principale
**Documentation complète auto-générée dans l'API** - Endpoint `/` retourne toute la doc nécessaire avec exemples, patterns, comparaisons.

---

## ⚡ QUICK COMMANDS

```bash
# Deploy
cd /home/tincenv/wrapper-claude && \
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v8 --project=claude-476509 && \
gcloud run deploy claude-wrapper-secure --image eu.gcr.io/claude-476509/claude-wrapper-secure:v8 --project=claude-476509 --region=europe-west1 --platform=managed

# Test
curl -s https://wrapper.claude.serenity-system.fr/health | jq '.'

# Logs
gcloud run services logs tail claude-wrapper-secure --project=claude-476509 --region=europe-west1

# Rollback
gcloud run services update-traffic claude-wrapper-secure --to-revisions=PREVIOUS=100 --project=claude-476509 --region=europe-west1
```

---

**Dernière mise à jour** : 2025-11-06
**Mainteneur** : vincent.paturel@serenity-system.fr
**Version** : v12-settings-file (production) - Settings file fix: --settings expects file path, not JSON string
