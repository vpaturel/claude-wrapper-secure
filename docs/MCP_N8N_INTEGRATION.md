# 🔗 Integration MCP n8n

Guide complet pour intégrer le wrapper Claude avec n8n via MCP (Model Context Protocol).

---

## 📋 Vue d'ensemble

**n8n** est une plateforme d'automatisation de workflow open-source qui peut exposer un serveur MCP pour permettre à Claude d'interagir avec vos workflows.

**MCP (Model Context Protocol)** est un protocole permettant aux LLMs d'accéder à des outils et services externes de manière standardisée.

### Ce que vous pouvez faire

Avec MCP n8n, Claude peut:
- 📋 Lister vos workflows n8n
- ▶️ Exécuter des workflows
- 📊 Récupérer les résultats d'exécution
- ⚙️ Créer/modifier des workflows (selon permissions)
- 🔍 Interroger les données de n8n

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Client (vous)  │
└────────┬────────┘
         │ HTTP POST /v1/messages
         ▼
┌─────────────────────────────────┐
│  Claude Wrapper                 │
│  (wrapper.claude.serenity...)   │
└────────┬────────────────────────┘
         │ Subprocess + MCP
         ▼
┌─────────────────────────────────┐
│  Claude CLI                     │
│  (avec MCP client intégré)      │
└────────┬────────────────────────┘
         │ MCP Protocol
         ▼
┌─────────────────────────────────┐
│  n8n MCP Server                 │
│  (local ou distant)             │
└────────┬────────────────────────┘
         │ n8n API
         ▼
┌─────────────────────────────────┐
│  n8n Instance                   │
│  (vos workflows)                │
└─────────────────────────────────┘
```

---

## 🚀 Setup n8n MCP Server

### Option 1: MCP Local (subprocess)

**Installation:**

```bash
# Installer n8n
npm install -g n8n

# Lancer n8n
n8n start

# Installer MCP server n8n (si package existe)
npm install -g @n8n/mcp-server
```

**Configuration dans le wrapper:**

```json
{
  "mcp_servers": {
    "n8n": {
      "command": "npx",
      "args": ["-y", "@n8n/mcp-server"],
      "env": {
        "N8N_API_KEY": "votre-api-key",
        "N8N_HOST": "http://localhost:5678",
        "DEBUG": "true"
      }
    }
  }
}
```

### Option 2: MCP Remote (HTTP/SSE)

**Si n8n expose un serveur MCP distant:**

```json
{
  "mcp_servers": {
    "n8n": {
      "url": "https://your-n8n.com/mcp/sse",
      "transport": "sse",
      "auth_type": "bearer",
      "auth_token": "your-n8n-api-token"
    }
  }
}
```

**Avec authentification JWT:**

```json
{
  "mcp_servers": {
    "n8n": {
      "url": "https://your-n8n.com/mcp/sse",
      "transport": "sse",
      "auth_type": "jwt",
      "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
}
```

---

## 🧪 Test de l'intégration

### 1. Test rapide (curl)

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
      {
        "role": "user",
        "content": "Tu as accès à n8n via MCP. Liste les workflows disponibles."
      }
    ],
    "model": "sonnet",
    "mcp_servers": {
      "n8n": {
        "command": "npx",
        "args": ["-y", "@n8n/mcp-server"],
        "env": {
          "N8N_API_KEY": "your-key",
          "N8N_HOST": "http://localhost:5678"
        }
      }
    }
  }'
```

### 2. Test avec script Python

```bash
# Configuration
export CLAUDE_ACCESS_TOKEN="sk-ant-oat01-..."
export CLAUDE_REFRESH_TOKEN="sk-ant-ort01-..."
export CLAUDE_EXPIRES_AT="1762444195608"

# Lancer le script de test
python test_mcp_n8n.py
```

### 3. Test manuel (Python)

```python
import requests

payload = {
    "oauth_credentials": {
        "access_token": "sk-ant-oat01-...",
        "refresh_token": "sk-ant-ort01-...",
        "expires_at": 1762444195608,
        "scopes": ["user:inference", "user:profile"],
        "subscription_type": "max"
    },
    "messages": [
        {
            "role": "user",
            "content": "Liste les workflows n8n et exécute le premier."
        }
    ],
    "model": "sonnet",
    "mcp_servers": {
        "n8n": {
            "url": "https://your-n8n.com/mcp/sse",
            "transport": "sse",
            "auth_type": "bearer",
            "auth_token": "your-token"
        }
    }
}

response = requests.post(
    "https://wrapper.claude.serenity-system.fr/v1/messages",
    json=payload,
    timeout=180
)

print(response.json())
```

---

## 🎯 Cas d'usage

### 1. Automatisation avec workflows

**Prompt:**
```
Tu as accès à n8n.
Crée un workflow qui:
1. Surveille les nouveaux emails
2. Extrait les pièces jointes
3. Les sauvegarde dans Google Drive
4. Envoie une notification Slack
```

### 2. Exécution de workflows existants

**Prompt:**
```
Liste tous les workflows n8n actifs.
Exécute le workflow "Daily Report Generator" avec les paramètres:
- date: aujourd'hui
- format: PDF
```

### 3. Analyse de workflows

**Prompt:**
```
Analyse tous mes workflows n8n et identifie:
- Ceux qui ont échoué récemment
- Les goulots d'étranglement
- Les optimisations possibles
```

### 4. Création de workflows complexes

**Prompt:**
```
Crée un workflow n8n pour:
1. Récupérer données API externe (https://api.example.com/users)
2. Transformer en format CSV
3. Uploader sur S3
4. Déclencher un webhook
```

---

## 🔒 Sécurité

### Isolation par utilisateur

Le wrapper assure une isolation complète:
- ✅ **Token isolation**: Chaque user utilise son OAuth token
- ✅ **Workspace isolation**: Chaque user a son workspace isolé
- ✅ **MCP isolation**: Les MCP servers sont isolés par requête

### Permissions MCP

Configurez les permissions dans n8n:
```json
{
  "n8n_permissions": {
    "read_workflows": true,
    "execute_workflows": true,
    "create_workflows": false,
    "delete_workflows": false,
    "read_credentials": false
  }
}
```

### Best practices

1. **API Key rotation**: Changez régulièrement les API keys n8n
2. **Least privilege**: Donnez le minimum de permissions
3. **Audit logs**: Activez les logs n8n pour auditer les actions
4. **Rate limiting**: Limitez le nombre d'exécutions par user
5. **Timeout**: Configurez des timeouts appropriés (180s par défaut)

---

## 🐛 Troubleshooting

### Problème: MCP server n8n ne démarre pas

**Symptômes:**
```
❌ Claude CLI error: Failed to initialize MCP server 'n8n'
```

**Solutions:**
1. Vérifier que n8n est installé: `which n8n`
2. Vérifier que le package MCP existe: `npm list -g @n8n/mcp-server`
3. Tester manuellement: `npx -y @n8n/mcp-server --help`
4. Vérifier les logs: voir `stderr` dans la réponse API

### Problème: Authentification n8n échoue

**Symptômes:**
```
❌ n8n API error: Unauthorized (401)
```

**Solutions:**
1. Vérifier l'API key n8n: `N8N_API_KEY` valide
2. Vérifier les scopes: API key a les bonnes permissions
3. Tester l'API directement:
   ```bash
   curl -H "X-N8N-API-KEY: your-key" \
     http://localhost:5678/api/v1/workflows
   ```

### Problème: Timeout sur exécution workflow

**Symptômes:**
```
❌ Timeout - le serveur MCP n8n ne répond peut-être pas
```

**Solutions:**
1. Augmenter le timeout dans la requête (default: 180s)
2. Vérifier que le workflow n8n ne contient pas de boucles infinies
3. Optimiser le workflow n8n (reduce steps, parallelize)

### Problème: MCP remote non accessible

**Symptômes:**
```
❌ Failed to connect to MCP server at https://...
```

**Solutions:**
1. Vérifier que l'URL est correcte et accessible
2. Vérifier le transport (sse vs http)
3. Vérifier le firewall / CORS
4. Tester avec curl:
   ```bash
   curl -H "Authorization: Bearer token" \
     https://your-n8n.com/mcp/sse
   ```

---

## 📊 Monitoring

### Logs Claude Wrapper

```bash
# Voir les logs Cloud Run
gcloud run services logs tail claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1 | grep "MCP"
```

### Logs n8n

```bash
# Logs n8n local
tail -f ~/.n8n/logs/n8n.log

# Logs n8n Docker
docker logs -f n8n-container
```

### Métriques

Surveillez:
- **Taux de succès MCP**: % de requêtes réussies
- **Latence**: temps de réponse des workflows
- **Erreurs**: erreurs 500 / timeouts
- **Token usage**: consommation tokens Claude

---

## 🔗 Ressources

### Documentation officielle

- **n8n**: https://docs.n8n.io/
- **n8n API**: https://docs.n8n.io/api/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Claude CLI**: https://claude.ai/docs/cli

### Exemples de workflows n8n

- **n8n Templates**: https://n8n.io/workflows/
- **Community workflows**: https://github.com/n8n-io/n8n

### Support

- **n8n Community**: https://community.n8n.io/
- **Claude Wrapper**: vincent.paturel@serenity-system.fr

---

## 🚀 Prochaines étapes

1. **Setup n8n**: Installer et configurer n8n
2. **Créer workflows**: Créer des workflows de test
3. **Tester MCP**: Utiliser `test_mcp_n8n.py`
4. **Intégrer**: Intégrer dans votre application
5. **Monitor**: Configurer monitoring et alertes

---

**Dernière mise à jour**: 2025-11-06
**Version wrapper**: v12-settings-file
**Mainteneur**: vincent.paturel@serenity-system.fr
