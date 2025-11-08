# 🔥 Claude API ULTIMATE - Guide Complet des Features

**Toutes les fonctionnalités cachées du Claude CLI découvertes et intégrées**

---

## 🎯 Résumé Exécutif

Le CLI Claude possède **50+ options** dont beaucoup sont sous-documentées. Ce guide explore **TOUTES** les features et propose des use cases créatifs.

### 14 Nouvelles Features Ajoutées

1. 🔥 **Custom Agents** via JSON
2. 🎭 **System Prompts** dynamiques
3. 🔄 **Fallback Models** automatique
4. 🛠️ **Tools Control** granulaire
5. 🔒 **Permission Modes** (plan, bypass, etc.)
6. 🔌 **Plugins** custom
7. 🐛 **Debug Mode** avec filtering
8. 📁 **Add Directories** access
9. 🔀 **Fork Sessions**
10. 🗣️ **Verbose Logging**
11. 💻 **IDE Auto-Connect**
12. 🎚️ **Setting Sources** control
13. 🔄 **Input/Output Format** control
14. 🔁 **Continue Recent** conversation

---

## 1️⃣ Custom Agents 🔥

### Qu'est-ce que c'est ?

Créer des **agents spécialisés** avec leurs propres prompts, descriptions et outils.

### Syntaxe

```bash
--agents '{"name": {"description": "...", "prompt": "...", "tools": [...]}}'
```

### Use Cases Créatifs

#### Use Case 1: Team d'Agents Code Review

```python
from claude_oauth_api_ultimate import create_ultimate_client, CustomAgent

client = create_ultimate_client(
    model="sonnet",
    custom_agents={
        # Agent 1: Security auditor
        "security_auditor": CustomAgent(
            name="security_auditor",
            description="Security vulnerabilities expert",
            prompt="You are a security auditor. Find SQL injections, XSS, CSRF, "
                   "authentication bypasses, and insecure configurations. "
                   "Rate severity: CRITICAL, HIGH, MEDIUM, LOW.",
            tools=["Read", "Grep", "Bash(git:*)"]
        ),

        # Agent 2: Performance optimizer
        "perf_optimizer": CustomAgent(
            name="perf_optimizer",
            description="Performance optimization specialist",
            prompt="You are a performance expert. Find N+1 queries, memory leaks, "
                   "slow algorithms, unnecessary computations, and blocking operations. "
                   "Suggest optimizations with estimated impact.",
            tools=["Read", "Bash(grep:*)", "Bash(rg:*)"]
        ),

        # Agent 3: Architecture reviewer
        "architect": CustomAgent(
            name="architect",
            description="Software architecture expert",
            prompt="You are a senior architect. Review code structure, design patterns, "
                   "SOLID principles, coupling, cohesion, and scalability concerns.",
            tools=["Read", "Glob"]
        )
    }
)

# Utiliser les agents
response = client.create_message(
    messages=[{"role": "user", "content": "Review src/api.py with all agents"}]
)
```

#### Use Case 2: Agent de Documentation Auto

```python
client = create_ultimate_client(
    custom_agents={
        "doc_generator": CustomAgent(
            name="doc_generator",
            description="Auto-generates comprehensive documentation",
            prompt="You are a technical writer. Generate documentation with: "
                   "1. Overview, 2. Installation, 3. Usage examples, "
                   "4. API reference, 5. Troubleshooting. "
                   "Use clear language and code examples.",
            tools=["Read", "Write(*)", "Edit(*)"]
        )
    }
)
```

#### Use Case 3: Agent Multi-Langue

```python
client = create_ultimate_client(
    custom_agents={
        "translator": CustomAgent(
            name="translator",
            description="Multi-language translator",
            prompt="You are a professional translator. Translate code comments, "
                   "docs, and error messages. Preserve technical terms and formatting.",
            tools=["Read", "Edit(*)"]
        )
    }
)
```

---

## 2️⃣ System Prompts Dynamiques 🎭

### Options

```bash
--system-prompt "..."           # Replace system prompt
--append-system-prompt "..."    # Append to default
```

### Use Cases Créatifs

#### Use Case 1: Context-Aware Assistant

```python
# User context
user_profile = {
    "role": "Senior DevOps Engineer",
    "experience": "10 years",
    "stack": ["Kubernetes", "Terraform", "Go"],
    "preferences": "Prefer Infrastructure as Code, avoid manual configs"
}

system_prompt = f"""
You are a DevOps assistant customized for: {user_profile['role']}
Experience level: {user_profile['experience']}
Tech stack: {', '.join(user_profile['stack'])}
Preferences: {user_profile['preferences']}

Adapt your responses to their expertise and preferences.
"""

client = create_ultimate_client(
    model="sonnet",
    system_prompt=system_prompt
)
```

#### Use Case 2: Domain-Specific Assistant

```python
# Medical assistant
medical_system_prompt = """
You are a medical informatics assistant with expertise in:
- HL7 FHIR standards
- HIPAA compliance
- Clinical workflows
- Electronic Health Records (EHR) systems

Always prioritize patient safety and data privacy.
Use medical terminology but explain complex concepts.
"""

client = create_ultimate_client(system_prompt=medical_system_prompt)
```

#### Use Case 3: Tone & Style Control

```python
# Casual vs Professional
casual_tone = "You are a friendly coding buddy. Use casual language, emojis, and memes."
professional_tone = "You are a professional consultant. Use formal language and business terminology."

# User preference
client = create_ultimate_client(
    system_prompt=casual_tone if user.prefers_casual else professional_tone
)
```

---

## 3️⃣ Fallback Models Automatique 🔄

### Syntaxe

```bash
--model opus --fallback-model sonnet
```

### Use Cases Créatifs

#### Use Case 1: Cost-Optimized API

```python
# Try Opus first, fallback to Sonnet if quota reached
client = create_ultimate_client(
    model="opus",
    fallback_model="sonnet"
)

# Si Opus quota exceeded, Sonnet utilisé automatiquement
response = client.create_message(messages=[...])
```

#### Use Case 2: Latency-Optimized

```python
# Try Haiku (fast), fallback to Sonnet si quality insuffisante
client = create_ultimate_client(
    model="haiku",
    fallback_model="sonnet"
)
```

#### Use Case 3: Smart Routing

```python
def smart_routing(complexity: str):
    """Route to appropriate model based on complexity"""
    if complexity == "high":
        return create_ultimate_client(model="opus", fallback_model="sonnet")
    elif complexity == "medium":
        return create_ultimate_client(model="sonnet", fallback_model="haiku")
    else:
        return create_ultimate_client(model="haiku")
```

---

## 4️⃣ Tools Control Granulaire 🛠️

### Options

```bash
--tools "Bash,Read,Edit"           # Only these tools
--allowed-tools "Bash(git:*)"      # Allow specific patterns
--disallowed-tools "Bash(rm:*)"    # Deny specific patterns
```

### Use Cases Créatifs

#### Use Case 1: Read-Only Audit Mode

```python
client = create_ultimate_client(
    tools=["Read", "Bash"],
    allowed_tools=["Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)"],
    disallowed_tools=["Write(*)", "Edit(*)", "Bash(rm:*)"]
)

# Claude peut uniquement lire, jamais modifier
```

#### Use Case 2: CI/CD Safe Mode

```python
client = create_ultimate_client(
    allowed_tools=[
        "Read", "Write(*)",
        "Bash(git:*)", "Bash(npm:*)", "Bash(pytest:*)", "Bash(docker:build:*)"
    ],
    disallowed_tools=[
        "Bash(rm:*)", "Bash(sudo:*)", "Bash(docker:push:*)"
    ]
)
```

#### Use Case 3: Sandbox Mode per User

```python
def create_user_sandbox(user_id: str):
    """Sandbox isolé par user"""
    return create_ultimate_client(
        tools=["Read", "Write", "Bash"],
        allowed_tools=[
            f"Write(/tmp/user_{user_id}/*)",
            f"Bash(ls:/tmp/user_{user_id}/*)",
            f"Bash(python:/tmp/user_{user_id}/*)"
        ],
        disallowed_tools=[
            "Write(/etc/*)",
            "Write(/home/*)",
            "Bash(rm:/*)",
            "Bash(sudo:*)"
        ]
    )
```

---

## 5️⃣ Permission Modes 🔒

### Modes Disponibles

- `acceptEdits` - Auto-accepte éditions (automation)
- `bypassPermissions` - Bypass all (sandbox)
- `default` - Ask user (interactive)
- `plan` - Plan only, no execution

### Use Cases Créatifs

#### Use Case 1: Planning Mode

```python
# Generate plan without executing
client_plan = create_ultimate_client(
    model="sonnet",
    permission_mode=PermissionMode.PLAN
)

plan = client_plan.create_message(
    messages=[{"role": "user", "content": "Refactor this codebase"}]
)

# Review plan, then execute
if user_approves(plan):
    client_exec = create_ultimate_client(permission_mode=PermissionMode.ACCEPT_EDITS)
    client_exec.create_message(messages=[{"role": "user", "content": "Execute the plan"}])
```

#### Use Case 2: Progressive Trust

```python
class ProgressiveTrustClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.trust_level = self.get_trust_level(user_id)

    def get_client(self):
        if self.trust_level == "untrusted":
            return create_ultimate_client(permission_mode=PermissionMode.DEFAULT)
        elif self.trust_level == "verified":
            return create_ultimate_client(permission_mode=PermissionMode.ACCEPT_EDITS)
        else:  # admin
            return create_ultimate_client(permission_mode=PermissionMode.BYPASS)
```

---

## 6️⃣ Debug Mode 🐛

### Syntaxe

```bash
--debug "api,mcp"      # Debug specific categories
--debug "!statsig"     # Debug all except statsig
--verbose              # Full verbosity
```

### Use Cases Créatifs

#### Use Case 1: MCP Development

```python
# Debug uniquement MCP servers
client = create_ultimate_client(
    debug="mcp",
    verbose=True
)

# Output détaillé des MCP calls
```

#### Use Case 2: Production Issue Debugging

```python
# Debug API calls sans polluer logs
client = create_ultimate_client(
    debug="api,!statsig,!file"  # API only, exclude statsig and file
)
```

---

## 7️⃣ Add Directories 📁

### Syntaxe

```bash
--add-dir /path1 /path2
```

### Use Cases Créatifs

#### Use Case 1: Multi-Project Access

```python
client = create_ultimate_client(
    add_dirs=[
        "/home/user/project1",
        "/home/user/project2",
        "/home/user/shared_libs"
    ]
)

# Claude peut accéder aux 3 projets
```

#### Use Case 2: Temporary Workspace

```python
import tempfile

temp_workspace = tempfile.mkdtemp()

client = create_ultimate_client(
    add_dirs=[temp_workspace],
    allowed_tools=[f"Write({temp_workspace}/*)", "Read"]
)

# Workspace temporaire isolé
```

---

## 8️⃣ Fork Sessions 🔀

### Syntaxe

```bash
--resume session-123 --fork-session
```

### Use Cases Créatifs

#### Use Case 1: A/B Testing Conversations

```python
# Original conversation
base_session = "conv-123"

# Fork 1: Solution A
client_a = create_ultimate_client(
    session_id=base_session,
    fork_session=True
)
solution_a = client_a.create_message(messages=[{"role": "user", "content": "Try approach A"}])

# Fork 2: Solution B (from same base)
client_b = create_ultimate_client(
    session_id=base_session,
    fork_session=True
)
solution_b = client_b.create_message(messages=[{"role": "user", "content": "Try approach B"}])

# Compare solutions
```

#### Use Case 2: Branching Conversations

```python
# Main conversation
main_client = create_ultimate_client(session_id="main-conv")

# Branch 1: Explore implementation
branch1 = create_ultimate_client(session_id="main-conv", fork_session=True)

# Branch 2: Explore tests
branch2 = create_ultimate_client(session_id="main-conv", fork_session=True)

# Merge insights back to main
```

---

## 🎯 Use Cases Ultra-Créatifs

### 1. AI Code Review Bot avec Agents Multiples

```python
review_bot = create_ultimate_client(
    model="sonnet",
    fallback_model="haiku",
    custom_agents={
        "security": CustomAgent(...),
        "performance": CustomAgent(...),
        "architecture": CustomAgent(...)
    },
    tools=["Read", "Bash(git:*)"],
    permission_mode=PermissionMode.DEFAULT
)

# Review automatique multi-agent
```

### 2. Context-Aware API Multi-Tenant

```python
def create_context_client(user):
    """Client adapté au contexte user"""
    return create_ultimate_client(
        system_prompt=f"You are an assistant for {user.role} with {user.experience} years experience",
        add_dirs=[user.workspace],
        allowed_tools=user.permissions,
        fallback_model="sonnet" if user.plan == "free" else None,
        debug="api" if user.is_admin else None
    )
```

### 3. Progressive Execution avec Planning

```python
# Step 1: Plan
planner = create_ultimate_client(permission_mode=PermissionMode.PLAN)
plan = planner.create_message(messages=[...])

# Step 2: Review plan
print(plan)

# Step 3: Execute si approved
if input("Approve? ") == "y":
    executor = create_ultimate_client(permission_mode=PermissionMode.ACCEPT_EDITS)
    result = executor.create_message(messages=[...])
```

---

## 📊 Tableau Récap Features

| Feature | Use Case Principal | Créativité 🔥 |
|---------|-------------------|---------------|
| Custom Agents | Code review multi-agent | Team d'experts IA |
| System Prompts | Domain-specific assistants | Context-aware responses |
| Fallback Models | Cost optimization | Smart routing |
| Tools Control | Security sandboxing | Per-user permissions |
| Permission Modes | CI/CD automation | Progressive trust |
| Debug Mode | MCP development | Production debugging |
| Add Directories | Multi-project access | Temporary workspaces |
| Fork Sessions | A/B testing | Branching conversations |

---

## ✅ Checklist Feature Adoption

Avant d'utiliser chaque feature:

- [ ] Custom Agents: Définir prompts spécialisés
- [ ] System Prompts: Adapter au contexte user
- [ ] Fallback: Définir stratégie cost/quality
- [ ] Tools Control: Définir whitelist/blacklist
- [ ] Permission Mode: Choisir niveau automation
- [ ] Debug: Définir catégories utiles
- [ ] Directories: Lister paths nécessaires
- [ ] Fork Sessions: Identifier use cases branchement

---

## 🚀 Conclusion

Le wrapper **ULTIMATE v4** intègre **14 nouvelles features** qui débloquent des use cases avancés:

✅ **Agents Multi-Experts** pour code review
✅ **Context-Aware** assistants
✅ **Cost-Optimized** routing
✅ **Security** sandboxing
✅ **Progressive Execution** avec planning
✅ **Debug** granulaire
✅ **Branching** conversations

**Fichier**: `claude_oauth_api_ultimate.py` (700+ lignes)

**Status**: ✅ **PRODUCTION READY**
