# 🌉 n8n MCP Bridge - Setup Guide

Guide complet pour déployer le serveur MCP bridge pour n8n.

---

## 📋 Vue d'ensemble

**Problème**: n8n ne supporte pas nativement le protocole MCP.

**Solution**: Nous créons un serveur "bridge" qui:
1. Expose un endpoint MCP (SSE)
2. Traduit les requêtes MCP vers l'API n8n
3. Permet à Claude d'interagir avec n8n via MCP

---

## 🏗️ Architecture

```
┌──────────────┐
│ Claude CLI   │
└──────┬───────┘
       │ MCP Protocol (SSE)
       ▼
┌──────────────────────┐
│ n8n MCP Bridge       │ ← Ce serveur Python
│ (Port 8000)          │
└──────┬───────────────┘
       │ HTTP API
       ▼
┌──────────────────────┐
│ n8n Instance         │
│ (Port 5678)          │
└──────────────────────┘
```

---

## 🚀 Installation

### 1. Prérequis

```bash
# Python 3.8+
python3 --version

# pip
pip --version

# n8n installé et lancé
n8n start
```

### 2. Installer dépendances

```bash
cd /home/tincenv/wrapper-claude

# Installer les packages Python
pip install fastapi uvicorn httpx
```

### 3. Générer API Key n8n

```bash
# Dans n8n Web UI (http://localhost:5678)
# 1. Settings → API
# 2. "Create API Key"
# 3. Copier la clé (n8n_xxx...)
```

### 4. Lancer le bridge

```bash
# Basic
python n8n_mcp_bridge.py \
  --n8n-url http://localhost:5678 \
  --n8n-api-key "n8n_api_xxx..."

# Avec token custom
python n8n_mcp_bridge.py \
  --n8n-url http://localhost:5678 \
  --n8n-api-key "n8n_api_xxx..." \
  --bridge-token "my-secure-token-123" \
  --port 8000
```

**Sortie attendue:**
```
======================================================================
🌉 n8n MCP Bridge Server
======================================================================
   n8n URL: http://localhost:5678
   Bridge URL: http://0.0.0.0:8000
   MCP Endpoint: http://0.0.0.0:8000/mcp/sse
======================================================================
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🧪 Test du bridge

### 1. Health check

```bash
curl http://localhost:8000/health
```

**Réponse attendue:**
```json
{
  "status": "healthy",
  "n8n_accessible": true,
  "timestamp": "2025-11-06T10:30:00"
}
```

### 2. Test outils MCP (direct)

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-bridge-token" \
  -d '{
    "tool": "list_workflows",
    "arguments": {}
  }'
```

**Réponse attendue:**
```json
{
  "success": true,
  "result": {
    "count": 5,
    "workflows": [
      {
        "id": "1",
        "name": "My First Workflow",
        "active": true
      }
    ]
  }
}
```

### 3. Test avec Claude Wrapper

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
        "content": "Tu as accès à n8n. Liste tous les workflows."
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

---

## 🔧 Configuration avancée

### Variables d'environnement

```bash
# .env file
N8N_URL=http://localhost:5678
N8N_API_KEY=n8n_api_xxx...
BRIDGE_TOKEN=my-secure-token-123
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8000
```

```bash
# Lancer avec .env
set -a
source .env
set +a

python n8n_mcp_bridge.py \
  --n8n-url "$N8N_URL" \
  --n8n-api-key "$N8N_API_KEY" \
  --bridge-token "$BRIDGE_TOKEN"
```

### Systemd service (Linux)

```bash
# /etc/systemd/system/n8n-mcp-bridge.service
[Unit]
Description=n8n MCP Bridge Server
After=network.target

[Service]
Type=simple
User=tincenv
WorkingDirectory=/home/tincenv/wrapper-claude
ExecStart=/usr/bin/python3 n8n_mcp_bridge.py \
  --n8n-url http://localhost:5678 \
  --n8n-api-key YOUR_API_KEY \
  --bridge-token YOUR_TOKEN
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activer le service
sudo systemctl daemon-reload
sudo systemctl enable n8n-mcp-bridge
sudo systemctl start n8n-mcp-bridge

# Vérifier status
sudo systemctl status n8n-mcp-bridge

# Logs
sudo journalctl -u n8n-mcp-bridge -f
```

### Docker

```dockerfile
# Dockerfile.n8n-bridge
FROM python:3.11-slim

WORKDIR /app

COPY n8n_mcp_bridge.py .
RUN pip install --no-cache-dir fastapi uvicorn httpx

EXPOSE 8000

CMD ["python", "n8n_mcp_bridge.py", \
     "--n8n-url", "${N8N_URL}", \
     "--n8n-api-key", "${N8N_API_KEY}", \
     "--bridge-token", "${BRIDGE_TOKEN}"]
```

```bash
# Build
docker build -t n8n-mcp-bridge -f Dockerfile.n8n-bridge .

# Run
docker run -d \
  --name n8n-mcp-bridge \
  -p 8000:8000 \
  -e N8N_URL=http://host.docker.internal:5678 \
  -e N8N_API_KEY=your-key \
  -e BRIDGE_TOKEN=your-token \
  n8n-mcp-bridge
```

---

## 🎯 Outils MCP disponibles

Le bridge expose 4 outils:

### 1. `list_workflows`

Liste tous les workflows n8n.

**Arguments**: Aucun

**Exemple Claude**:
```
"Liste tous les workflows n8n disponibles."
```

### 2. `get_workflow`

Récupère les détails d'un workflow.

**Arguments**:
- `workflow_id` (string): ID du workflow

**Exemple Claude**:
```
"Récupère les détails du workflow avec l'ID '123'."
```

### 3. `execute_workflow`

Exécute un workflow avec des données optionnelles.

**Arguments**:
- `workflow_id` (string): ID du workflow
- `data` (object, optional): Données à passer

**Exemple Claude**:
```
"Exécute le workflow '123' avec les données: {\"user\": \"john\", \"action\": \"test\"}"
```

### 4. `get_executions`

Liste l'historique des exécutions.

**Arguments**:
- `workflow_id` (string, optional): Filtrer par workflow
- `limit` (integer, optional): Nombre max (défaut: 10)

**Exemple Claude**:
```
"Montre-moi les 5 dernières exécutions du workflow '123'."
```

---

## 🐛 Troubleshooting

### Bridge ne démarre pas

**Erreur:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
pip install fastapi uvicorn httpx
```

---

### n8n non accessible

**Erreur:**
```json
{
  "status": "degraded",
  "n8n_accessible": false
}
```

**Solutions:**
1. Vérifier que n8n est lancé: `ps aux | grep n8n`
2. Vérifier l'URL: `curl http://localhost:5678/healthz`
3. Vérifier le firewall

---

### API Key invalide

**Erreur:**
```
n8n API error: 401 - Unauthorized
```

**Solutions:**
1. Vérifier que l'API key est correcte
2. Régénérer une nouvelle clé dans n8n
3. Tester directement:
   ```bash
   curl -H "X-N8N-API-KEY: your-key" \
     http://localhost:5678/api/v1/workflows
   ```

---

### Claude ne voit pas les outils MCP

**Erreur:**
```
Je n'ai pas accès à des outils n8n.
```

**Solutions:**
1. Vérifier que le bridge est lancé: `curl http://localhost:8000/health`
2. Vérifier la config MCP dans la requête:
   ```json
   "mcp_servers": {
     "n8n": {
       "url": "http://localhost:8000/mcp/sse",
       "transport": "sse",
       "auth_type": "bearer",
       "auth_token": "test-bridge-token"
     }
   }
   ```
3. Vérifier les logs du bridge
4. Vérifier les logs Claude Wrapper

---

## 📊 Monitoring

### Logs du bridge

```bash
# Logs en temps réel
tail -f /var/log/n8n-mcp-bridge.log

# Avec systemd
sudo journalctl -u n8n-mcp-bridge -f

# Logs Docker
docker logs -f n8n-mcp-bridge
```

### Métriques

```bash
# Nombre de workflows
curl http://localhost:8000/mcp/tools/call \
  -H "Authorization: Bearer test-bridge-token" \
  -d '{"tool": "list_workflows", "arguments": {}}'

# Santé n8n
curl http://localhost:8000/health
```

---

## 🔒 Sécurité

### Best practices

1. **Token sécurisé**: Utilisez un token long et aléatoire
   ```bash
   # Générer un token
   openssl rand -hex 32
   ```

2. **HTTPS**: En production, utilisez HTTPS
   ```bash
   # Avec nginx reverse proxy
   nginx → https://your-domain.com → http://localhost:8000
   ```

3. **Firewall**: Limitez l'accès au bridge
   ```bash
   # Autoriser seulement localhost
   sudo ufw allow from 127.0.0.1 to any port 8000
   ```

4. **API Key rotation**: Changez régulièrement l'API key n8n

5. **Logs**: Surveillez les logs pour détecter les accès suspects

---

## 🚀 Déploiement production

### Cloud Run (GCP)

```bash
# Build image
gcloud builds submit \
  --tag eu.gcr.io/claude-476509/n8n-mcp-bridge:v1

# Deploy
gcloud run deploy n8n-mcp-bridge \
  --image eu.gcr.io/claude-476509/n8n-mcp-bridge:v1 \
  --region europe-west1 \
  --platform managed \
  --set-env-vars N8N_URL=https://your-n8n.com,N8N_API_KEY=secret,BRIDGE_TOKEN=secret
```

### AWS Lambda

```python
# Handler pour Lambda
from mangum import Mangum
handler = Mangum(app)
```

---

## 📚 Ressources

- **n8n API**: https://docs.n8n.io/api/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastAPI**: https://fastapi.tiangolo.com/

---

**Dernière mise à jour**: 2025-11-06
**Version**: 1.0.0
**Mainteneur**: vincent.paturel@serenity-system.fr
