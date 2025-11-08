# 🔧 Troubleshooting FAQ - Claude OAuth Wrapper

**Solutions rapides aux problèmes courants**

---

## Installation & Setup

### Q: `claude: command not found`

**Cause**: Claude CLI pas installé ou pas dans PATH

**Solution**:
```bash
# Installer
curl -fsSL https://claude.ai/install.sh | sh

# Ajouter au PATH
export PATH="/opt/claude/versions/2.0.33:$PATH"

# Vérifier
claude --version
```

---

### Q: `Authentication required`

**Cause**: Pas connecté à Claude

**Solution**:
```bash
# Se connecter
claude auth login

# Vérifier
claude auth status
```

---

### Q: Wrapper import fail: `ModuleNotFoundError: No module named 'claude_oauth_api'`

**Cause**: Fichier pas dans PYTHONPATH

**Solution**:
```bash
# Option 1: Copier dans projet
cp claude_oauth_api.py /votre/projet/

# Option 2: Installer comme module
pip install -e .  # Si setup.py existe

# Option 3: PYTHONPATH
export PYTHONPATH="/path/to/claude_oauth_api:$PYTHONPATH"
```

---

## Erreurs Quota & Rate Limits

### Q: `Opus weekly limit reached ∙ resets Nov 10, 5pm`

**Cause**: Quota Opus Max (~100 msg/week) ou Pro (~50 msg/week) atteint

**Solutions**:
```python
# Solution 1: Utiliser Sonnet (pas de limite weekly)
client = create_client(model="sonnet")

# Solution 2: Fallback automatique
client = create_client(
    model="opus",
    fallback_model="sonnet"  # Si Opus fail, use Sonnet
)

# Solution 3: Attendre reset (indiqué dans message)
```

**Prévention**:
- Utiliser Opus uniquement pour tâches complexes
- Sonnet pour 90% des cas
- Haiku pour tâches simples

---

### Q: `Rate limit exceeded. Please try again later.`

**Cause**: Trop de requêtes/sec

**Solution**:
```python
import time

# Rate limiting manuel
for message in messages:
    response = quick_message(message)
    time.sleep(0.3)  # 3 req/sec max

# Ou avec retry automatique
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def send_with_retry(msg):
    return quick_message(msg)
```

---

## Timeout & Performance

### Q: `Request timeout after 180s`

**Causes**:
1. Prompt trop long (>10K tokens)
2. Réponse complexe (thinking mode)
3. API lente

**Solutions**:
```python
# Solution 1: Augmenter timeout
client = create_client(timeout=300)  # 5 minutes

# Solution 2: Simplifier prompt
# ❌ Mauvais: prompt 50K tokens
# ✅ Bon: Résumer ou découper

# Solution 3: Désactiver thinking (si activé)
client = create_client(
    model="sonnet",  # Au lieu de opus avec thinking
    max_thinking_tokens=None
)
```

---

### Q: Streaming ne fonctionne pas / Pas de sortie

**Cause**: Flag `--verbose` manquant pour streaming CLI

**Solution**:
```python
# Le wrapper gère ça automatiquement maintenant
client = create_client(model="sonnet")

for chunk in client.messages.create(messages=[...], stream=True):
    if chunk.get("type") == "content_block_delta":
        text = chunk.get("delta", {}).get("text", "")
        print(text, end="", flush=True)
```

**Si toujours pas de sortie**:
```bash
# Test CLI direct
claude --print --verbose --model sonnet \
  --output-format stream-json \
  --include-partial-messages \
  "Count from 1 to 5"
```

---

## Erreurs OAuth

### Q: `400: This credential is only authorized for use with Claude Code`

**Cause**: Tentative d'utiliser OAuth token directement avec API (non supporté)

**Solution**: ✅ **Utiliser le wrapper** (c'est le but!)

```python
# ❌ NE PAS FAIRE
import requests
requests.post("https://api.anthropic.com/v1/messages",
    headers={"Authorization": f"Bearer {oauth_token}"})

# ✅ FAIRE
from claude_oauth_api import quick_message
response = quick_message("Hello")
```

---

### Q: `401: OAuth authentication is currently not supported`

**Cause**: Même problème - OAuth tokens ne marchent pas en direct

**Solution**: Wrapper ou API Key

```python
# Option 1: Wrapper OAuth (ce projet)
from claude_oauth_api import create_client
client = create_client()

# Option 2: API Key officielle (si vous en avez)
import anthropic
client = anthropic.Anthropic(api_key="sk-ant-api03-...")
```

---

## Wrapper Errors

### Q: Error parsing response / `KeyError: 'content'`

**Cause**: Réponse CLI pas au format attendu (erreur, quota, etc.)

**Solution temporaire**:
```python
try:
    response = client.messages.create(messages=[...])

    if response.get("type") == "error":
        print(f"Error: {response['error']['message']}")
    else:
        print(response["content"][0]["text"])
except KeyError as e:
    print(f"Unexpected response format: {response}")
```

**Fix permanent**: Contribuer improved error parsing au wrapper

---

### Q: Subprocess error / CLI crash

**Cause**: Claude CLI a crashé ou retourné exit code non-zero

**Diagnostic**:
```bash
# Tester CLI directement
claude --print "test message"

# Vérifier logs
cat /tmp/claude_cli.log  # Si logs activés

# Version CLI
claude --version
```

**Solution**: Réinstaller CLI si nécessaire

---

## Performance Issues

### Q: Réponses très lentes (>30s pour message simple)

**Causes possibles**:
1. Proxy/network lent
2. Model overloaded
3. Prompt trop complexe

**Diagnostic**:
```python
import time

start = time.time()
response = quick_message("test")
elapsed = time.time() - start

print(f"Latency: {elapsed:.2f}s")

# Normal: 1-3s pour message simple
# Lent: >10s
```

**Solutions**:
- Utiliser Haiku (plus rapide)
- Simplifier prompt
- Vérifier connexion network

---

### Q: High memory usage

**Cause**: Streaming buffer ou long context

**Solution**:
```python
# Pour streaming: process chunks immédiatement
for chunk in client.messages.create(..., stream=True):
    text = chunk.get("delta", {}).get("text", "")
    process_immediately(text)  # Ne pas accumuler

# Pour long context: découper
def chunk_text(text, max_chars=5000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

for chunk in chunk_text(long_text):
    response = quick_message(f"Process: {chunk}")
```

---

## Sessions & MCP 🆕

### Q: Comment utiliser les sessions persistantes?

**Solution**:
```python
from claude_oauth_api import create_client

# Option 1: Session ID auto-générée
client = create_client(model="sonnet", persist_session=True)
print(f"Session ID: {client.config.session_id}")  # UUID auto-généré

# Message 1
response1 = client.messages.create(
    messages=[{"role": "user", "content": "Talk about Python"}]
)

# Message 2 (contexte conservé)
response2 = client.messages.create(
    messages=[{"role": "user", "content": "What language?"}]
)
print(response2)  # "Python" ✅

# Option 2: Session ID custom
import uuid
session_id = str(uuid.uuid4())
client = create_client(model="sonnet", session_id=session_id)
```

---

### Q: Comment activer les serveurs MCP?

**Solution**:
```python
# Activer MCP servers (utilise config globale)
client = create_client(
    model="sonnet",
    enable_mcp=True,
    skip_mcp_permissions=True  # Auto-approve outils MCP
)

# Utiliser un outil MCP
response = client.messages.create(
    messages=[{
        "role": "user",
        "content": "Use mcp__memory__create_entities to store: name='Project', type='software'"
    }]
)
```

**Config MCP globale**: `~/.config/claude-code/mcp_settings.json`

---

### Q: Les outils MCP ne fonctionnent pas / Permission denied

**Cause**: MCP permissions non bypassées

**Solution**:
```python
# Sans bypass (mode interactif - demande permission)
client = create_client(model="sonnet", enable_mcp=True)

# Avec bypass (mode automatique - pour automation)
client = create_client(
    model="sonnet",
    enable_mcp=True,
    skip_mcp_permissions=True  # ✅
)
```

⚠️ **Note**: `skip_mcp_permissions=True` équivaut à `--dangerously-skip-permissions` (utiliser en environnement sécurisé seulement)

---

### Q: Comment lister tous les outils MCP disponibles?

**Solution**:
```bash
# Option 1: CLI direct
claude mcp list

# Output:
# puppeteer: docker run ... - ✓ Connected
# memory: npx @modelcontextprotocol/server-memory - ✓ Connected
```

```python
# Option 2: Via wrapper
from claude_oauth_api import list_mcp_tools

tools = list_mcp_tools(model="sonnet")
print(tools)
# ['mcp__puppeteer__puppeteer_navigate', 'mcp__memory__create_entities', ...]
```

---

### Q: Comment configurer de nouveaux serveurs MCP?

**Fichier**: `~/.config/claude-code/mcp_settings.json`

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "puppeteer": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/puppeteer"]
    },
    "custom-server": {
      "command": "/path/to/your/server",
      "args": ["--port", "8080"],
      "env": {
        "API_KEY": "your_key"
      }
    }
  }
}
```

**Après modif**: Redémarrer Claude CLI ou wrapper

---

### Q: Session ne se poursuit pas / Contexte perdu

**Diagnostic**:
```python
# Vérifier si session_id est défini
client = create_client(persist_session=True)
print(f"Session ID: {client.config.session_id}")  # Doit afficher UUID

# Vérifier que même session_id est utilisé
response1 = client.messages.create(...)
response2 = client.messages.create(...)  # Doit utiliser même session
```

**Causes possibles**:
1. Créer nouveau client à chaque appel → Utiliser même instance
2. Ne pas activer `persist_session=True` → Ajouter flag
3. Session expirée (rare) → Créer nouvelle session

**Solution**:
```python
# ❌ Mauvais - nouveau client à chaque fois
for msg in messages:
    client = create_client()  # Nouvelle session !
    response = client.messages.create(...)

# ✅ Bon - réutiliser même client
client = create_client(persist_session=True)
for msg in messages:
    response = client.messages.create(...)  # Même session
```

---

## Common Mistakes

### ❌ 1. Oublier stream=True pour streaming

```python
# ❌ Mauvais
client.messages.create(messages=[...])  # Pas de stream

# ✅ Bon
client.messages.create(messages=[...], stream=True)
```

### ❌ 2. Hardcoder model complet au lieu d'alias

```python
# ❌ Verbeux
model="claude-sonnet-4-5-20250929"

# ✅ Simple
model="sonnet"
```

### ❌ 3. Pas de error handling

```python
# ❌ Crash si erreur
response = quick_message(msg)
print(response)

# ✅ Robuste
try:
    response = quick_message(msg)
    print(response)
except Exception as e:
    print(f"Error: {e}")
    # Fallback logic
```

### ❌ 4. Utiliser Opus pour tout

```python
# ❌ Gaspille quota
client = create_client(model="opus")  # Pour toutes requêtes

# ✅ Stratégique
def get_model_for_task(task_complexity):
    if task_complexity == "high":
        return "opus"
    elif task_complexity == "medium":
        return "sonnet"
    else:
        return "haiku"
```

---

## Debug Mode

**Activer verbose logging**:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

client = create_client(verbose=True)  # Affiche commande CLI complète

# Voir exactement quelle commande est exécutée
```

**Test CLI direct** (bypass wrapper):
```bash
claude --print --model sonnet "test message"
```

**Check environment**:
```bash
# PATH
echo $PATH | grep claude

# Credentials
ls -la ~/.claude/.credentials.json

# Permissions
claude auth status
```

---

## Obtenir de l'Aide

**1. Vérifier logs**:
```bash
# CLI logs (si activés)
cat ~/.claude/logs/cli.log

# Wrapper errors
# Voir stderr du subprocess
```

**2. Minimal reproducible example**:
```python
# Créer test minimal qui reproduit bug
from claude_oauth_api import quick_message

try:
    response = quick_message("test")
    print(f"Success: {response}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

**3. Ressources**:
- README.md - Documentation projet
- QUICK_START_GUIDE.md - Exemples rapides
- CLAUDE_CLI_WRAPPER.md - Détails wrapper
- OpenAPI spec - API reference

**4. GitHub Issues**:
Si bug trouvé dans wrapper, ouvrir issue avec:
- Version Claude CLI (`claude --version`)
- Python version (`python --version`)
- Minimal code reproducing bug
- Error traceback complet

---

## ✅ Checklist Debugging

Avant de demander de l'aide, vérifier:

- [ ] Claude CLI installé (`claude --version`)
- [ ] Authentifié (`claude auth status`)
- [ ] Wrapper dans PYTHONPATH
- [ ] Test CLI direct fonctionne
- [ ] Pas de firewall/proxy bloquant
- [ ] Quota non atteint (pour Opus)
- [ ] Timeout suffisant pour tâche
- [ ] Error handling présent dans code
- [ ] 🆕 Session ID défini si sessions utilisées
- [ ] 🆕 Même client instance réutilisée pour sessions
- [ ] 🆕 MCP config valide si MCP activé (`claude mcp list`)
- [ ] 🆕 `skip_mcp_permissions=True` si automation MCP

---

**🎯 90% des problèmes résolus par cette FAQ!**

**Pas de solution?** Consultez [CLAUDE_CLI_WRAPPER.md](CLAUDE_CLI_WRAPPER.md) pour détails avancés.
