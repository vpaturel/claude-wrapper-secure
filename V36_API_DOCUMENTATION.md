# 📚 API v36 Documentation - Thinking Bool + Auto File Inclusion

**Version**: v36-files-watcher
**Date**: 2025-11-09
**Endpoint**: https://wrapper.claude.serenity-system.fr

---

## 🆕 NOUVEAUTÉS v36

### 1. Thinking Parameter Simplifié

**Avant (v35)**:
```json
{
  "thinking": {
    "type": "enabled",
    "budget_tokens": 5000
  }
}
```

**Maintenant (v36)**:
```json
{
  "thinking": true
}
```

**Avantages**:
- ✅ Plus simple (boolean au lieu d'objet)
- ✅ Format compatible Claude CLI (`alwaysThinkingEnabled`)
- ✅ Par défaut: `false` (comportement normal)

---

### 2. Auto File Inclusion

**Nouveau paramètre**: `include_files`

Inclut automatiquement tous les fichiers créés/modifiés par Claude dans la réponse.

**Cas d'usage**:
- Génération de code (récupérer tous les fichiers créés)
- Projets complets (télécharger workspace)
- Modifications multiples (voir tous les changements)

---

## 📖 RÉFÉRENCE API

### POST /v1/messages

#### Paramètres de Requête

```typescript
{
  oauth_credentials: {
    access_token: string;      // sk-ant-oat01-...
    refresh_token: string;     // sk-ant-ort01-...
    expires_at: number;        // Unix timestamp (ms)
    scopes: string[];          // ["user:inference", "user:profile"]
    subscription_type: string; // "max" | "pro"
  };
  messages: Array<{
    role: "user" | "assistant";
    content: string;
  }>;

  // Optional parameters
  model?: "opus" | "sonnet" | "haiku";  // Default: "sonnet"
  session_id?: string;                   // UUID v4 for stateful mode
  stream?: boolean;                      // Default: false

  // v36 NEW parameters
  thinking?: boolean;                    // Default: false
  fallback_model?: "opus" | "sonnet" | "haiku";
  include_files?: boolean;               // Default: false

  mcp_servers?: {
    [name: string]: {
      command?: string;
      args?: string[];
      env?: Record<string, string>;
      // OR
      url?: string;
      transport?: "sse" | "streamableHttp";
      auth_type?: "jwt" | "oauth" | "bearer";
      auth_token?: string;
    };
  };
}
```

#### Réponse (sans include_files)

```json
{
  "type": "message",
  "content": [
    {
      "type": "text",
      "text": "I've created a FastAPI application..."
    }
  ],
  "model": "claude-sonnet-4-5-20250929",
  "usage": {
    "input_tokens": 123,
    "output_tokens": 456
  }
}
```

#### Réponse (avec include_files: true)

```json
{
  "type": "message",
  "content": [
    {
      "type": "text",
      "text": "I've created a FastAPI application with the following files..."
    }
  ],
  "model": "claude-sonnet-4-5-20250929",
  "usage": {
    "input_tokens": 123,
    "output_tokens": 456
  },

  // NEW: Files section
  "files": [
    {
      "path": "main.py",
      "content": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/\")\ndef root():\n    return {\"message\": \"Hello World\"}",
      "encoding": "text",
      "size": 123
    },
    {
      "path": "requirements.txt",
      "content": "fastapi==0.109.0\nuvicorn==0.27.0",
      "encoding": "text",
      "size": 45
    },
    {
      "path": "logo.png",
      "content": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
      "encoding": "base64",
      "size": 5678
    }
  ],

  "files_summary": {
    "total": 3,
    "total_size": 5846
  }
}
```

---

## 💡 EXEMPLES D'UTILISATION

### Exemple 1: Thinking Activé

```bash
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {
      "access_token": "sk-ant-oat01-...",
      "refresh_token": "sk-ant-ort01-...",
      "expires_at": 1762671773363,
      "scopes": ["user:inference", "user:profile"],
      "subscription_type": "max"
    },
    "messages": [
      {
        "role": "user",
        "content": "Solve this complex math problem: If f(x) = x^3 - 6x^2 + 11x - 6, find all real roots."
      }
    ],
    "model": "sonnet",
    "thinking": true
  }'
```

**Réponse**: Claude prend plus de temps pour raisonner avant de répondre.

---

### Exemple 2: Récupérer Fichiers Générés

```bash
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {...},
    "messages": [
      {
        "role": "user",
        "content": "Create a complete REST API with FastAPI: users CRUD, authentication, and Dockerfile"
      }
    ],
    "model": "sonnet",
    "include_files": true
  }'
```

**Réponse**:
```json
{
  "content": [...],
  "files": [
    {"path": "main.py", "content": "...", "size": 1234},
    {"path": "models.py", "content": "...", "size": 567},
    {"path": "auth.py", "content": "...", "size": 890},
    {"path": "requirements.txt", "content": "...", "size": 123},
    {"path": "Dockerfile", "content": "...", "size": 456}
  ],
  "files_summary": {
    "total": 5,
    "total_size": 3270
  }
}
```

---

### Exemple 3: Thinking + Files (Combiné)

```bash
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_credentials": {...},
    "messages": [
      {
        "role": "user",
        "content": "Design and implement a production-ready microservice architecture with: API Gateway, 3 services (users, orders, payments), Docker Compose, and comprehensive tests."
      }
    ],
    "model": "sonnet",
    "thinking": true,
    "include_files": true
  }'
```

**Résultat**:
- Extended Thinking: Claude analyse en profondeur l'architecture
- Auto File Inclusion: Récupère tous les fichiers générés (20+ fichiers)

---

### Exemple 4: Mode Stateful avec Files

```javascript
// Conversation 1
const response1 = await fetch('/v1/messages', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    oauth_credentials: {...},
    session_id: "project-abc-123",
    messages: [{
      role: "user",
      content: "Create a basic Express.js server"
    }],
    include_files: true
  })
});

const data1 = await response1.json();
console.log(`Created ${data1.files.length} files`);
// → Created 2 files: server.js, package.json

// Conversation 2 (même session)
const response2 = await fetch('/v1/messages', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    oauth_credentials: {...},
    session_id: "project-abc-123",  // Même session
    messages: [{
      role: "user",
      content: "Add a /users endpoint with MongoDB"
    }],
    include_files: true
  })
});

const data2 = await response2.json();
console.log(`Total files: ${data2.files.length}`);
// → Total files: 4 (server.js modifié + package.json modifié + models/user.js + config/db.js)
```

---

## 🔍 FILTRAGE FICHIERS

### Fichiers Ignorés Automatiquement

Le File Watcher ignore:

```
.git/
__pycache__/
*.pyc
*.swp
*~
node_modules/
.DS_Store
.claude/
*.tmp
*.temp
.env
.env.*
```

**Pourquoi**:
- Sécurité (.env contient secrets)
- Performance (node_modules peut être énorme)
- Pertinence (fichiers temporaires inutiles)

### Limite de Taille

- **Max par fichier**: 10 MB
- **Fichiers dépassant**: Ignorés avec warning dans logs

---

## 📊 ENCODAGE FICHIERS

### Text Files (encoding: "text")

Extensions supportées:
- Code: `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.c`, `.cpp`
- Web: `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte`
- Config: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
- Docs: `.md`, `.txt`, `.rst`

**Retourné tel quel** (UTF-8):
```json
{
  "path": "main.py",
  "content": "from fastapi import FastAPI\n...",
  "encoding": "text"
}
```

### Binary Files (encoding: "base64")

Extensions:
- Images: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`
- Archives: `.zip`, `.tar`, `.gz`
- Autres binaires

**Encodé en base64**:
```json
{
  "path": "logo.png",
  "content": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "encoding": "base64"
}
```

**Décodage côté client**:
```javascript
const binaryData = atob(file.content);  // Decode base64
const blob = new Blob([binaryData], {type: 'image/png'});
const url = URL.createObjectURL(blob);
```

---

## ⚡ PERFORMANCE

### Snapshot Mode (Défaut)

**Timing**:
```
Claude génère code (30s)
  ↓
Scan workspace (0.1s)
  ↓
Lire fichiers (0.2s)
  ↓
Retourner response (30.3s total)
```

**Overhead**: ~0.3s (négligeable)

### Impact Réseau

**Sans include_files**:
```json
{
  "content": [...],  // ~2 KB
  "usage": {...}
}
// Total: ~2 KB
```

**Avec include_files (5 fichiers)**:
```json
{
  "content": [...],     // ~2 KB
  "files": [...],       // ~15 KB (5 fichiers × 3 KB)
  "files_summary": {...}
}
// Total: ~17 KB
```

**Recommandation**:
- ✅ Activer si vous avez besoin des fichiers
- ❌ Désactiver si vous voulez juste la réponse texte

---

## 🔒 SÉCURITÉ

### Isolation Workspace

Chaque utilisateur a son propre workspace isolé:

```
/workspaces/
├── 6fcbaf5339bade94/  (User A)
│   ├── main.py
│   └── utils.py
└── abc123def456789a/  (User B)
    ├── server.js
    └── package.json
```

**Garantie**: User A ne peut JAMAIS voir les fichiers de User B.

### Filtrage Secrets

Les fichiers contenant potentiellement des secrets sont **automatiquement exclus**:
- `.env`
- `.env.local`, `.env.production`
- `credentials.json`
- Fichiers dans `**/secrets/**`

**Important**: Même si Claude crée un `.env`, il ne sera **PAS** inclus dans la réponse.

---

## 🐛 DEBUGGING

### Vérifier si Fichiers Inclus

```javascript
const response = await fetch('/v1/messages', {...});
const data = await response.json();

if ('files' in data) {
  console.log(`✅ Files included: ${data.files.length}`);
  console.log(`📊 Total size: ${data.files_summary.total_size} bytes`);
} else {
  console.log('❌ No files (include_files was false or no files created)');
}
```

### Fichier Manquant

**Pourquoi un fichier pourrait être absent**:
1. Ignoré par filtres (.git, node_modules, .env)
2. Trop gros (> 10 MB)
3. Binaire non reconnu
4. Créé puis supprimé par Claude

**Solution**: Vérifier les logs Cloud Run:
```bash
gcloud run services logs read claude-wrapper-secure \
  --project=claude-476509 \
  --region=europe-west1 \
  --limit=50 | grep "File"
```

---

## 📈 CAS D'USAGE RECOMMANDÉS

### ✅ Quand Utiliser include_files: true

1. **Génération de Projet Complet**
   ```
   "Create a full-stack app with React + FastAPI"
   → Récupère 20+ fichiers (frontend + backend)
   ```

2. **Modifications Multiples**
   ```
   "Add authentication to all 5 services"
   → Récupère tous les fichiers modifiés
   ```

3. **Export/Backup**
   ```
   "Refactor the entire codebase using async/await"
   → Snapshot de tous les changements
   ```

4. **Code Review**
   ```
   "Fix all type errors in the project"
   → Voir tous les fichiers corrigés
   ```

### ❌ Quand NE PAS Utiliser

1. **Questions Simples**
   ```
   "What is 2+2?"
   → Pas de fichiers générés
   ```

2. **Conversations Texte**
   ```
   "Explain how OAuth works"
   → Juste texte, pas de code
   ```

3. **Bandwidth Limité**
   ```
   Mobile 3G + 50 fichiers
   → Trop lourd
   ```

---

## 🔄 COMPATIBILITÉ

### Rétrocompatibilité

**v36 est 100% compatible avec v35**:

```javascript
// v35 code (toujours fonctionnel)
fetch('/v1/messages', {
  body: JSON.stringify({
    thinking: {type: "enabled"},  // ❌ Ignoré silencieusement
    // ...
  })
});

// v36 code (recommandé)
fetch('/v1/messages', {
  body: JSON.stringify({
    thinking: true,  // ✅ Format simplifié
    // ...
  })
});
```

**Migration**: Aucune action requise, les anciennes requêtes fonctionnent toujours.

---

## 📊 LIMITES

| Limite | Valeur | Raison |
|--------|--------|--------|
| Max file size | 10 MB | Performance |
| Max total files | Illimité | - |
| Max response size | ~100 MB | HTTP limits |
| Encoding | UTF-8, base64 | Standard |

---

## 🎯 EXEMPLES COMPLETS

### Python Client

```python
import requests
import json
import base64

def create_project_with_files(prompt):
    response = requests.post(
        "https://wrapper.claude.serenity-system.fr/v1/messages",
        json={
            "oauth_credentials": {
                "access_token": "sk-ant-oat01-...",
                "refresh_token": "sk-ant-ort01-...",
                "expires_at": 1762671773363,
                "scopes": ["user:inference", "user:profile"],
                "subscription_type": "max"
            },
            "messages": [{"role": "user", "content": prompt}],
            "model": "sonnet",
            "thinking": True,
            "include_files": True
        }
    )

    data = response.json()

    # Save files to disk
    if "files" in data:
        for file in data["files"]:
            path = file["path"]
            content = file["content"]
            encoding = file["encoding"]

            # Create directory if needed
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Write file
            if encoding == "text":
                with open(path, 'w') as f:
                    f.write(content)
            elif encoding == "base64":
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(content))

            print(f"✅ Saved: {path}")

    return data

# Usage
result = create_project_with_files("Create a Flask REST API with SQLite")
print(f"📦 Created {result['files_summary']['total']} files")
```

### JavaScript Client

```javascript
async function createProjectWithFiles(prompt) {
  const response = await fetch(
    'https://wrapper.claude.serenity-system.fr/v1/messages',
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        oauth_credentials: {
          access_token: 'sk-ant-oat01-...',
          refresh_token: 'sk-ant-ort01-...',
          expires_at: 1762671773363,
          scopes: ['user:inference', 'user:profile'],
          subscription_type: 'max'
        },
        messages: [{role: 'user', content: prompt}],
        model: 'sonnet',
        thinking: true,
        include_files: true
      })
    }
  );

  const data = await response.json();

  // Download files as ZIP
  if (data.files) {
    const JSZip = require('jszip');
    const zip = new JSZip();

    for (const file of data.files) {
      if (file.encoding === 'text') {
        zip.file(file.path, file.content);
      } else if (file.encoding === 'base64') {
        zip.file(file.path, file.content, {base64: true});
      }
    }

    const blob = await zip.generateAsync({type: 'blob'});
    const url = URL.createObjectURL(blob);

    // Trigger download
    const a = document.createElement('a');
    a.href = url;
    a.download = 'project.zip';
    a.click();

    console.log(`✅ Downloaded ${data.files.length} files as ZIP`);
  }

  return data;
}

// Usage
createProjectWithFiles('Create a Next.js app with TypeScript and Tailwind');
```

---

## 🚀 DÉPLOIEMENT

**Version actuelle en production**: v36-files-watcher

**Endpoint**: https://wrapper.claude.serenity-system.fr

**Santé du service**:
```bash
curl https://wrapper.claude.serenity-system.fr/health
# {
#   "status": "healthy",
#   "version": "v36-files-watcher",
#   "security_level": "BALANCED"
# }
```

---

## 📞 SUPPORT

**Issues**: https://github.com/anthropics/claude-code/issues
**Email**: vincent.paturel@serenity-system.fr

---

**Dernière mise à jour**: 2025-11-09
**Version**: v36-files-watcher
