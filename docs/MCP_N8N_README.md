# 🔗 MCP n8n Integration - Vue d'ensemble

Intégration complète entre Claude Wrapper, MCP Protocol et n8n.

---

## 🎯 Objectif

Permettre à Claude d'interagir avec vos workflows n8n via le protocole MCP (Model Context Protocol).

**Use cases:**
- 📋 Lister et analyser vos workflows
- ▶️ Exécuter des workflows
- 📊 Récupérer les résultats
- 🤖 Automatiser des tâches complexes

---

## 🏗️ Architecture

```
┌────────────┐
│   Client   │  (Vous)
└─────┬──────┘
      │ HTTP POST
      ▼
┌──────────────────────┐
│ Claude Wrapper       │  wrapper.claude.serenity-system.fr
│ (FastAPI)            │
└─────┬────────────────┘
      │ Subprocess + MCP
      ▼
┌──────────────────────┐
│ Claude CLI           │  Avec MCP client intégré
└─────┬────────────────┘
      │ MCP SSE
      ▼
┌──────────────────────┐
│ n8n MCP Bridge       │  Serveur Python (n8n_mcp_bridge.py)
│ (Port 8000)          │  Traduit MCP → n8n API
└─────┬────────────────┘
      │ HTTP API
      ▼
┌──────────────────────┐
│ n8n Instance         │  Vos workflows
│ (Port 5678)          │
└──────────────────────┘
```

---

## ⚡ Quick Start (5 minutes)

### 1. Installer n8n

```bash
npm install -g n8n
n8n start
# → http://localhost:5678
```

### 2. Générer API Key n8n

1. Ouvrir http://localhost:5678
2. Settings → API
3. "Create API Key"
4. Copier la clé

### 3. Installer dépendances bridge

```bash
pip install fastapi uvicorn httpx
```

### 4. Lancer le bridge

```bash
cd /home/tincenv/wrapper-claude

python n8n_mcp_bridge.py \
  --n8n-url http://localhost:5678 \
  --n8n-api-key "votre-api-key-n8n"

# → Bridge lancé sur http://localhost:8000
```

### 5. Test rapide

```bash
# Test automatique
./TEST_MCP_N8N_QUICK.sh

# Ou test manuel
curl http://localhost:8000/health
```

### 6. Test avec Claude

```bash
export CLAUDE_ACCESS_TOKEN="sk-ant-oat01-..."
export CLAUDE_REFRESH_TOKEN="sk-ant-ort01-..."
export CLAUDE_EXPIRES_AT="1762444195608"

python test_mcp_n8n.py
```

---

## 📁 Fichiers créés

```
/home/tincenv/wrapper-claude/
├── n8n_mcp_bridge.py              # Serveur MCP bridge (15K)
├── test_mcp_n8n.py                # Script de test Python (11K)
├── TEST_MCP_N8N_QUICK.sh          # Test rapide bash
│
└── docs/
    ├── MCP_N8N_INTEGRATION.md     # Documentation complète
    ├── N8N_MCP_BRIDGE_SETUP.md    # Guide de setup détaillé
    └── MCP_N8N_README.md          # Ce fichier
```

---

## 🧪 Tests disponibles

### Test 1: Health check (30s)

```bash
# Vérifier que tout est accessible
curl http://localhost:8000/health
curl https://wrapper.claude.serenity-system.fr/health
```

### Test 2: MCP Bridge direct (1 min)

```bash
# Tester le bridge sans Claude
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-bridge-token" \
  -d '{
    "tool": "list_workflows",
    "arguments": {}
  }'
```

### Test 3: Intégration complète (3 min)

```bash
# Test avec Claude Wrapper + MCP + n8n
./TEST_MCP_N8N_QUICK.sh
```

### Test 4: Test Python interactif (5 min)

```bash
export CLAUDE_ACCESS_TOKEN="sk-ant-oat01-..."
export CLAUDE_REFRESH_TOKEN="sk-ant-ort01-..."
export CLAUDE_EXPIRES_AT="1762444195608"

python test_mcp_n8n.py
```

---

## 🎯 Exemples d'usage

### Exemple 1: Lister workflows

**Requête:**
```bash
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {...},
    "messages": [
      {
        "role": "user",
        "content": "Liste tous les workflows n8n et identifie ceux qui sont inactifs."
      }
    ],
    "model": "sonnet",
    "mcp_servers": {
      "n8n": {
        "url": "http://localhost:8000/mcp/sse",
        "transport": "sse",
        "auth_type": "bearer",
        "auth_token": "test-bridge-token"
      }
    }
  }'
```

### Exemple 2: Exécuter workflow

**Requête:**
```
"Exécute le workflow 'Daily Report' avec les paramètres:
- date: aujourd'hui
- format: PDF
- email: admin@example.com"
```

### Exemple 3: Analyse et optimisation

**Requête:**
```
"Analyse tous mes workflows n8n et identifie:
1. Ceux qui ont échoué cette semaine
2. Les goulots d'étranglement
3. Les suggestions d'optimisation"
```

---

## 🛠️ Outils MCP disponibles

Le bridge expose 4 outils:

| Outil | Description | Arguments |
|-------|-------------|-----------|
| `list_workflows` | Liste tous les workflows | Aucun |
| `get_workflow` | Détails d'un workflow | `workflow_id` |
| `execute_workflow` | Exécute un workflow | `workflow_id`, `data` (opt) |
| `get_executions` | Historique exécutions | `workflow_id` (opt), `limit` (opt) |

---

## 🔒 Sécurité

### Isolation garantie

✅ **Token isolation**: Chaque user utilise son OAuth token
✅ **Workspace isolation**: Workspaces isolés par user
✅ **MCP isolation**: Bridge séparé, pas d'accès direct n8n
✅ **Auth bridge**: Token d'authentification requis

### Configuration sécurisée

```bash
# Générer un token sécurisé
openssl rand -hex 32

# Lancer avec token custom
python n8n_mcp_bridge.py \
  --n8n-api-key "secret" \
  --bridge-token "$(openssl rand -hex 32)"
```

---

## 🐛 Troubleshooting

### Problème: Bridge ne démarre pas

```bash
# Vérifier dépendances
pip install fastapi uvicorn httpx

# Vérifier n8n accessible
curl http://localhost:5678/healthz
```

### Problème: Claude ne voit pas les outils

1. Vérifier que le bridge est lancé
2. Vérifier la config MCP dans la requête
3. Vérifier les logs du bridge
4. Vérifier le token d'authentification

### Problème: Timeout

1. Augmenter timeout dans la requête (défaut: 180s)
2. Optimiser le workflow n8n
3. Vérifier la connexion réseau

**Voir le guide complet**: `docs/N8N_MCP_BRIDGE_SETUP.md`

---

## 📚 Documentation complète

- **Setup détaillé**: [N8N_MCP_BRIDGE_SETUP.md](N8N_MCP_BRIDGE_SETUP.md)
- **Guide intégration**: [MCP_N8N_INTEGRATION.md](MCP_N8N_INTEGRATION.md)
- **README projet**: [../README.md](../README.md)

---

## 🚀 Prochaines étapes

1. ✅ Setup n8n et bridge → **5 min**
2. ✅ Test rapide → **2 min**
3. 🎯 Créer vos workflows n8n → **15 min**
4. 🤖 Intégrer dans votre app → **30 min**
5. 📊 Automatiser vos tâches → **∞**

---

## 💡 Use cases avancés

### Automatisation multi-services

```
"Crée un workflow n8n qui:
1. Surveille Gmail pour nouveaux emails [urgent]
2. Extrait les pièces jointes
3. Les upload sur Google Drive
4. Crée une task Notion
5. Envoie notification Slack"
```

### Monitoring et alertes

```
"Surveille tous les workflows n8n.
Si un workflow échoue:
1. Analyse l'erreur
2. Tente une correction automatique
3. Envoie un rapport détaillé"
```

### Data processing

```
"Récupère les données de l'API externe https://api.example.com/users
Transforme en CSV
Upload sur S3
Déclenche un webhook de notification"
```

---

**Dernière mise à jour**: 2025-11-06
**Version**: 1.0.0
**Mainteneur**: vincent.paturel@serenity-system.fr
