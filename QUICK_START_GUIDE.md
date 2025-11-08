# 🚀 Quick Start Guide - Claude OAuth Wrapper v2

**5 minutes pour démarrer** avec le wrapper OAuth Python
**🆕 Avec sessions persistantes + MCP servers**

---

## Installation

```bash
# 1. Installer Claude CLI (si pas déjà fait)
curl -fsSL https://claude.ai/install.sh | sh

# 2. Se connecter (Claude Max/Pro required)
claude auth login

# 3. Télécharger le wrapper
cd /votre/projet
wget https://raw.githubusercontent.com/tincenv/analyse-claude-ai/main/claude_oauth_api.py
```

---

## Exemple 1: Message Simple (30 secondes)

```python
from claude_oauth_api import quick_message

# Envoi message + réponse
response = quick_message("What is the capital of France?")
print(response)
# Output: "The capital of France is Paris."
```

**✅ DONE!** C'est tout ce qu'il faut pour commencer.

---

## Exemple 2: System Prompt Custom (1 minute)

```python
from claude_oauth_api import create_client

# Créer client avec system prompt
client = create_client(
    model="sonnet",
    system_prompt="You are a professional Python developer. Answer concisely."
)

# Utiliser
response = client.messages.create(
    messages=[{"role": "user", "content": "How to read a CSV file?"}]
)

print(response["content"][0]["text"])
```

**Output**: Code Python concis avec pandas/csv.

---

## Exemple 3: Conversation Multi-Tour (2 minutes)

```python
from claude_oauth_api import create_client

client = create_client(model="sonnet")

# Tour 1
response1 = client.messages.create(
    messages=[
        {"role": "user", "content": "I'm building a web scraper"}
    ]
)

# Tour 2 (avec contexte)
response2 = client.messages.create(
    messages=[
        {"role": "user", "content": "I'm building a web scraper"},
        {"role": "assistant", "content": response1["content"][0]["text"]},
        {"role": "user", "content": "Which library should I use?"}
    ]
)

print(response2["content"][0]["text"])
```

**Output**: Recommandations (BeautifulSoup, Scrapy, etc.)

---

## Exemple 4: Extended Thinking (Opus) (2 minutes)

```python
from claude_oauth_api import create_client

# Activer thinking mode
client = create_client(
    model="opus",
    max_thinking_tokens=30000
)

response = client.messages.create(
    messages=[{
        "role": "user",
        "content": "Explain how blockchain consensus mechanisms work"
    }]
)

# Réponse inclut thinking (raisonnement) + text (réponse finale)
for block in response["content"]:
    if block["type"] == "thinking":
        print(f"🧠 Thinking: {block['thinking'][:200]}...")
    elif block["type"] == "text":
        print(f"📝 Response: {block['text']}")
```

---

## Exemple 5: Streaming (3 minutes)

```python
from claude_oauth_api import create_client

client = create_client(model="sonnet")

print("Streaming response:")
for chunk in client.messages.create(
    messages=[{"role": "user", "content": "Write a haiku about programming"}],
    stream=True
):
    if chunk.get("type") == "content_block_delta":
        delta = chunk.get("delta", {})
        if delta.get("type") == "text_delta":
            print(delta.get("text", ""), end="", flush=True)

print("\n")
```

**Output**: Texte affiché en temps réel (effet typewriter).

---

## ⚙️ Configuration Avancée

### Tous les Paramètres

```python
from claude_oauth_api import create_client, ClaudeConfig

config = ClaudeConfig(
    model="sonnet",                      # opus, sonnet, haiku
    max_thinking_tokens=30000,           # 30K max (Opus/Sonnet)
    system_prompt="You are...",          # System prompt
    append_system_prompt="Additional",   # Append to system
    tools=["Bash", "Edit", "Read"],      # Tools disponibles
    output_format="text",                # text, json, stream-json
    fallback_model="haiku",              # Fallback si quota
    verbose=False,                       # Debug mode
    timeout=180                          # Timeout secondes
)

client = create_client(**config.__dict__)
```

---

## 🔧 Troubleshooting Common

### Erreur: "claude: command not found"

```bash
# Vérifier installation
which claude

# Réinstaller si besoin
curl -fsSL https://claude.ai/install.sh | sh
export PATH="/opt/claude/versions/2.0.33:$PATH"
```

### Erreur: "Authentication required"

```bash
# Se connecter
claude auth login

# Vérifier status
claude auth status
```

### Erreur: "Opus weekly limit reached"

```python
# Solution 1: Utiliser Sonnet/Haiku
client = create_client(model="sonnet")

# Solution 2: Attendre reset (indiqué dans message)
# "Opus weekly limit reached ∙ resets Nov 10, 5pm"
```

### Timeout après 180s

```python
# Augmenter timeout
client = create_client(timeout=300)  # 5 minutes
```

---

## 📊 Performance Tips

### 1. Modèle Approprié

- **Opus**: Tâches complexes, raisonnement profond (~100/week limit)
- **Sonnet**: Usage général, bon équilibre qualité/vitesse ✅ Recommandé
- **Haiku**: Tâches simples, réponses rapides

### 2. System Prompts

```python
# ❌ Mauvais (vague)
system_prompt="Be helpful"

# ✅ Bon (précis)
system_prompt="You are a senior DevOps engineer. Provide commands with explanations."
```

### 3. Batch Processing

```python
# Traiter plusieurs fichiers
import concurrent.futures

def process_file(filename):
    with open(filename) as f:
        return quick_message(f"Summarize: {f.read()}")

files = ["doc1.txt", "doc2.txt", "doc3.txt"]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(process_file, files))
```

---

## 🎯 Use Cases Réels

### 1. Code Review

```python
client = create_client(
    system_prompt="You are a code reviewer. Focus on security and performance."
)

with open("src/api.py") as f:
    code = f.read()

response = client.messages.create(
    messages=[{"role": "user", "content": f"Review this code:\n\n{code}"}]
)

print(response["content"][0]["text"])
```

### 2. Documentation Auto

```python
import os
import glob

client = create_client(model="sonnet")

for file in glob.glob("src/**/*.py", recursive=True):
    with open(file) as f:
        code = f.read()

    doc = quick_message(f"Write docstrings for:\n\n{code}")

    # Sauvegarder ou appliquer
    print(f"✅ {file}: {len(doc)} chars documentation")
```

### 3. CI/CD Integration

```python
# .gitlab-ci.yml script
import subprocess
from claude_oauth_api import quick_message

# Get git diff
diff = subprocess.check_output(["git", "diff", "main...HEAD"], text=True)

# Analyse changes
analysis = quick_message(f"""
Analyze this git diff for:
1. Breaking changes
2. Security issues
3. Performance impacts

Diff:
{diff}
""")

# Fail si critical issues
if "CRITICAL" in analysis or "SECURITY" in analysis:
    print("❌ Critical issues found")
    print(analysis)
    exit(1)

print("✅ Changes look good")
```

---

## Exemple 6: Sessions Persistantes (3 minutes) 🆕

```python
from claude_oauth_api import create_client

# Créer client avec session persistante
client = create_client(
    model="sonnet",
    persist_session=True  # Auto-génère UUID
)

print(f"Session ID: {client.config.session_id}")

# Message 1
response1 = client.messages.create(
    messages=[{"role": "user", "content": "Let's discuss Python programming"}]
)
print(f"Response 1: {response1['content'][0]['text'][:100]}...")

# Message 2 (contexte conservé automatiquement)
response2 = client.messages.create(
    messages=[{"role": "user", "content": "What programming language were we discussing?"}]
)
print(f"Response 2: {response2['content'][0]['text']}")
# Output: "Python" ✅ CONTEXTE CONSERVÉ !
```

**Use case**: Chatbots, assistants conversationnels, tutoriels interactifs

---

## Exemple 7: MCP Servers (3 minutes) 🆕

```python
from claude_oauth_api import create_client

# Créer client avec MCP activé
client = create_client(
    model="sonnet",
    enable_mcp=True,
    skip_mcp_permissions=True  # Auto-approve MCP tools
)

# Utiliser MCP memory server
response = client.messages.create(
    messages=[{
        "role": "user",
        "content": "Use mcp__memory__create_entities to store: name='MyProject', type='software', observations=['Built with Python', 'Uses FastAPI']"
    }]
)

print(response["content"][0]["text"])
# Output: "Successfully stored entity..." ✅

# Utiliser MCP Puppeteer (web automation)
response2 = client.messages.create(
    messages=[{
        "role": "user",
        "content": "Use mcp__puppeteer__puppeteer_navigate to go to https://example.com and mcp__puppeteer__puppeteer_screenshot to take a screenshot"
    }]
)

print(response2["content"][0]["text"])
```

**MCP Servers disponibles** (si configurés) :
- **Puppeteer** (7 outils) : navigate, screenshot, click, fill, select, hover, evaluate
- **Memory** (9 outils) : create_entities, create_relations, add_observations, etc.
- **Resources** (2 outils) : ListMcpResourcesTool, ReadMcpResourceTool

**Configuration** : `~/.config/claude-code/mcp_settings.json`

---

## 📚 Ressources

- **README complet**: [README.md](README.md)
- **Wrapper code**: [claude_oauth_api.py](claude_oauth_api.py)
- **OpenAPI spec**: [openapi-claude-oauth.yaml](openapi-claude-oauth.yaml)
- **Documentation OAuth**: [OAUTH_FLOW_DOCUMENTATION.md](OAUTH_FLOW_DOCUMENTATION.md)

---

## 💡 Pro Tips

1. **Cache responses côté client** pour requêtes répétées
2. **Rate limiting** : 3-5 requêtes/sec max recommandé
3. **Error handling** : Toujours wrapper dans try/except
4. **Fallback model** : Utiliser haiku comme fallback si quota
5. **Timeouts** : Ajuster selon taille prompt (long prompt = timeout >180s)
6. 🆕 **Sessions persistantes** : Utiliser `persist_session=True` pour chatbots/assistants
7. 🆕 **MCP servers** : Activer avec `enable_mcp=True, skip_mcp_permissions=True` pour automation
8. 🆕 **Session cleanup** : Sauvegarder `session_id` pour reprendre conversations plus tard
9. 🆕 **MCP config** : Configurer serveurs dans `~/.config/claude-code/mcp_settings.json`

---

**🎉 Vous êtes prêt!** Commencez avec l'Exemple 1 et progressez selon vos besoins.

**Questions?** Consultez [TROUBLESHOOTING_FAQ.md](TROUBLESHOOTING_FAQ.md)
