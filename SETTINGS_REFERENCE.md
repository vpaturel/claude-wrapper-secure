# 📋 Reference Complète: `--settings` Flag

**Toutes les options configurables via `--settings <json>`**

---

## 🎯 Format Global

```json
{
  "mcpServers": { ... },
  "permissions": { ... }
}
```

---

## 1️⃣ `mcpServers` - Serveurs MCP Custom

### Structure

```json
{
  "mcpServers": {
    "server_name": {
      "command": "string",
      "args": ["array", "of", "strings"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

### Exemples Complets

#### Example 1: MCP Memory

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

#### Example 2: MCP Puppeteer (Docker)

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--init",
        "-e",
        "DOCKER_CONTAINER=true",
        "mcp/puppeteer"
      ]
    }
  }
}
```

#### Example 3: MCP HTTP avec Auth

```json
{
  "mcpServers": {
    "custom_api": {
      "command": "http-mcp-server",
      "args": ["https://api.example.com"],
      "env": {
        "AUTH_TOKEN": "Bearer sk-xxx",
        "API_KEY": "xyz123"
      }
    }
  }
}
```

#### Example 4: MCP SSE avec Auth

```json
{
  "mcpServers": {
    "realtime_api": {
      "command": "sse-mcp-client",
      "args": ["https://sse.example.com/stream"],
      "env": {
        "AUTHORIZATION": "Bearer token_abc",
        "X-API-KEY": "key_123"
      }
    }
  }
}
```

#### Example 5: Custom Python MCP

```json
{
  "mcpServers": {
    "my_custom_server": {
      "command": "/usr/bin/python3",
      "args": ["/path/to/my_mcp_server.py"],
      "env": {
        "PYTHONPATH": "/custom/path",
        "DATABASE_URL": "postgresql://...",
        "API_SECRET": "secret_value"
      }
    }
  }
}
```

### Cas d'Usage Multi-Tenant

```json
{
  "mcpServers": {
    "user_memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "user_database": {
      "command": "python3",
      "args": ["/app/mcp_db_server.py"],
      "env": {
        "DB_HOST": "user-db-123.cloudsql.com",
        "DB_USER": "user123",
        "DB_PASSWORD": "encrypted_pwd",
        "USER_ID": "user-abc-123"
      }
    },
    "user_webhook": {
      "command": "webhook-mcp",
      "args": ["https://webhook.user.com"],
      "env": {
        "WEBHOOK_SECRET": "user_secret_key",
        "RATE_LIMIT": "100"
      }
    }
  }
}
```

---

## 2️⃣ `permissions` - Contrôle Outils

### Structure

```json
{
  "permissions": {
    "defaultMode": "string",
    "allowedTools": ["array"],
    "deny": ["array"]
  }
}
```

### Paramètres

| Paramètre | Type | Description | Valeurs |
|-----------|------|-------------|---------|
| `defaultMode` | string | Mode par défaut | `"acceptEdits"`, `"ask"`, `"deny"` |
| `allowedTools` | array | Outils autorisés | Liste patterns |
| `deny` | array | Outils interdits | Liste patterns |

### Modes Disponibles

- **`acceptEdits`**: Auto-accepte éditions fichiers (recommandé automation)
- **`ask`**: Demande confirmation (mode interactif)
- **`deny`**: Refuse par défaut (mode restrictif)

### Patterns Outils

#### Outils Natifs

```json
{
  "allowedTools": [
    "Read",                  // Lecture fichiers
    "Write(*)",              // Écriture (tous fichiers)
    "Write(/path/only)",     // Écriture (path spécifique)
    "Edit(*)",               // Édition fichiers
    "Bash(ls:*)",            // Commande ls
    "Bash(git:*)",           // Git commands
    "Bash(docker:*)",        // Docker commands
    "Bash(python:*)",        // Python commands
    "Bash(npm:*)",           // NPM commands
    "mcp__memory",           // MCP Memory server
    "mcp__puppeteer",        // MCP Puppeteer server
    "mcp__custom_*"          // Tous MCP commençant par custom_
  ]
}
```

#### Bash Commands Granulaire

```json
{
  "allowedTools": [
    "Bash(ls:*)",            // ls autorisé
    "Bash(cat:*)",           // cat autorisé
    "Bash(grep:*)",          // grep autorisé
    "Bash(git:status)",      // git status uniquement
    "Bash(git:log)",         // git log uniquement
    "Bash(PORT=:*)",         // Variables d'environnement
    "Bash(NODE_ENV=:*)"
  ],
  "deny": [
    "Bash(rm:*)",            // rm interdit
    "Bash(sudo:*)",          // sudo interdit
    "Bash(shutdown:*)",      // shutdown interdit
    "Bash(reboot:*)"         // reboot interdit
  ]
}
```

### Exemples Complets

#### Example 1: Mode Sécurisé (Read-Only)

```json
{
  "permissions": {
    "defaultMode": "deny",
    "allowedTools": [
      "Read",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(grep:*)"
    ],
    "deny": [
      "Write(*)",
      "Edit(*)",
      "Bash(rm:*)"
    ]
  }
}
```

**Usage**: Audit code, analyse sans modifications

#### Example 2: Mode CI/CD

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": [
      "Read",
      "Write(*)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(pytest:*)",
      "Bash(docker:*)"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(sudo:*)"
    ]
  }
}
```

**Usage**: Pipeline automatisé

#### Example 3: Mode Sandbox (User Isolé)

```json
{
  "permissions": {
    "defaultMode": "ask",
    "allowedTools": [
      "Read",
      "Write(/tmp/user_123/*)",
      "Bash(ls:/tmp/user_123/*)",
      "Bash(python:/tmp/user_123/*)",
      "mcp__user_123_*"
    ],
    "deny": [
      "Write(/etc/*)",
      "Write(/home/other_user/*)",
      "Bash(sudo:*)",
      "Bash(rm:/*)"
    ]
  }
}
```

**Usage**: Multi-tenant avec isolation

---

## 🔥 Combinaisons Avancées

### Cas 1: Multi-Tenant avec MCP + Permissions

```json
{
  "mcpServers": {
    "user_memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "user_api": {
      "command": "http-mcp",
      "args": ["https://api.user.com"],
      "env": {
        "AUTH": "Bearer user_token_123"
      }
    }
  },
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": [
      "Read",
      "Write(/tmp/user_123/*)",
      "Bash(python:*)",
      "mcp__user_*"
    ],
    "deny": [
      "Write(/etc/*)",
      "Bash(sudo:*)",
      "Bash(rm:*)"
    ]
  }
}
```

### Cas 2: Development Mode

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
    }
  },
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": [
      "Read",
      "Write(*)",
      "Edit(*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(python:*)",
      "Bash(docker:*)",
      "mcp__*"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(sudo:*)"
    ]
  }
}
```

### Cas 3: Production Restricted

```json
{
  "mcpServers": {
    "monitoring": {
      "command": "monitoring-mcp",
      "args": ["https://metrics.prod.com"],
      "env": {
        "PROM_TOKEN": "prod_token",
        "ENV": "production"
      }
    }
  },
  "permissions": {
    "defaultMode": "deny",
    "allowedTools": [
      "Read",
      "Bash(git:status)",
      "Bash(git:log)",
      "Bash(docker:ps)",
      "Bash(kubectl:get:*)",
      "mcp__monitoring"
    ],
    "deny": [
      "Write(*)",
      "Edit(*)",
      "Bash(rm:*)",
      "Bash(kubectl:delete:*)"
    ]
  }
}
```

---

## 🚀 Usage avec Multi-Tenant API

### Python

```python
from claude_oauth_api_multi_tenant import MultiTenantClaudeAPI, MCPServerConfig

api = MultiTenantClaudeAPI()

# Build settings JSON
settings = {
    "mcpServers": {
        "user_db": {
            "command": "python3",
            "args": ["/app/db_mcp.py"],
            "env": {"USER_ID": "user123"}
        }
    },
    "permissions": {
        "defaultMode": "acceptEdits",
        "allowedTools": ["Read", "Write(/tmp/user123/*)", "mcp__user_*"],
        "deny": ["Bash(rm:*)", "Bash(sudo:*)"]
    }
}

# Les settings sont passés via --settings JSON
response = api.create_message(
    oauth_token="sk-ant-oat01-xxx",
    messages=[{"role": "user", "content": "Hello"}],
    mcp_servers={
        "user_db": MCPServerConfig(
            command="python3",
            args=["/app/db_mcp.py"],
            env={"USER_ID": "user123"}
        )
    }
    # Permissions seraient ajoutées dans _build_settings_json()
)
```

### Bash CLI

```bash
# Create settings JSON
cat > /tmp/user_settings.json <<'EOF'
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  },
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": ["Read", "Write(*)", "mcp__*"],
    "deny": ["Bash(rm:*)", "Bash(sudo:*)"]
  }
}
EOF

# Use with --settings
claude --print --settings /tmp/user_settings.json "Test with custom settings"

# Or inline JSON
claude --print --settings '{"mcpServers":{"memory":{"command":"npx","args":["-y","@modelcontextprotocol/server-memory"]}}}' "Test"
```

---

## 📝 Notes Importantes

### 1. Priorité Config

```
--settings JSON > ~/.config/claude-code/settings.json > defaults
```

### 2. Merge Behavior

`--settings` **merge** avec config globale (ne remplace pas complètement)

### 3. Security

⚠️ **Attention**: `deny` est prioritaire sur `allowedTools`

### 4. MCP avec Auth Externe

Pour MCP HTTP/SSE avec tokens dynamiques:

```json
{
  "mcpServers": {
    "secure_api": {
      "command": "http-mcp-client",
      "args": ["https://api.example.com"],
      "env": {
        "AUTHORIZATION": "Bearer sk-user-token-here",
        "X-USER-ID": "user123",
        "X-TENANT-ID": "tenant456"
      }
    }
  }
}
```

---

## ✅ Checklist Validation

Avant d'utiliser `--settings` :

- [ ] JSON valide (utiliser `jq` pour valider)
- [ ] `command` existe et est exécutable
- [ ] `args` correct (tester manuellement)
- [ ] `env` variables définies
- [ ] Permissions cohérentes (pas de conflit allow/deny)
- [ ] Tester avec CLI avant intégrer API

---

## 🎯 Exemples Prêts à l'Emploi

### Template 1: User Isolé

```json
{
  "mcpServers": {
    "USER_ID_memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  },
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": ["Read", "Write(/tmp/USER_ID/*)", "mcp__USER_ID_*"],
    "deny": ["Bash(rm:*)", "Write(/etc/*)"]
  }
}
```

### Template 2: CI/CD Pipeline

```json
{
  "mcpServers": {},
  "permissions": {
    "defaultMode": "acceptEdits",
    "allowedTools": [
      "Read", "Write(*)", "Edit(*)",
      "Bash(git:*)", "Bash(npm:*)", "Bash(pytest:*)", "Bash(docker:*)"
    ],
    "deny": ["Bash(rm:*)", "Bash(sudo:*)"]
  }
}
```

### Template 3: Read-Only Audit

```json
{
  "mcpServers": {},
  "permissions": {
    "defaultMode": "deny",
    "allowedTools": ["Read", "Bash(ls:*)", "Bash(grep:*)", "Bash(git:log)"],
    "deny": ["Write(*)", "Edit(*)", "Bash(rm:*)"]
  }
}
```

---

**Tout ce qu'on peut passer via `--settings` est maintenant documenté! 🎉**
