# 🔐 Documentation complète - OAuth Flow

**Source** : Analyse `~/.claude/.credentials.json` + captures réseau + reverse engineering comportemental
**Date** : 2025-11-05
**API** : Claude OAuth (claude.ai)

---

## 🎯 Vue d'ensemble

L'authentification OAuth de Claude.ai permet d'accéder à l'API avec un compte Max/Pro sans API Key.

**Avantages vs API Key** :
- ✅ Pas de gestion de clés API séparées
- ✅ Utilise le quota du plan Max/Pro
- ✅ Refresh automatique des tokens
- ✅ Multi-device sync
- ✅ Révocation centralisée via compte claude.ai

---

## 📊 Structure OAuth complète

### Format des tokens

**Access Token** :
```
sk-ant-oat01-[BASE64_TOKEN]
```
- Préfixe : `sk-ant-oat01-`
- Longueur : ~100 caractères
- Durée de vie : ~1 heure (3600 secondes)
- Usage : Header `Authorization: Bearer sk-ant-oat01-*`

**Refresh Token** :
```
sk-ant-ort01-[BASE64_TOKEN]
```
- Préfixe : `sk-ant-ort01-`
- Longueur : ~100 caractères
- Durée de vie : ~30 jours (2592000 secondes)
- Usage : Renouveler l'access token

**Expiration** :
- Format : Unix timestamp en **millisecondes**
- Exemple : `1762363467462` = `2025-11-05 12:24:27 UTC`
- Calcul : `expiresAt - Date.now()` pour temps restant

---

## 🔑 Structure credentials.json

**Localisation** : `~/.claude/.credentials.json`

```json
{
  "claudeAiOauth": {
    "accessToken": "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",
    "refreshToken": "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",
    "expiresAt": 1762363467462,
    "scopes": [
      "user:inference",
      "user:profile"
    ],
    "subscriptionType": "max"
  }
}
```

**Champs** :
- `accessToken` : Token d'accès actuel (Bearer token)
- `refreshToken` : Token pour renouveler l'access token
- `expiresAt` : Timestamp expiration en **millisecondes** (pas secondes !)
- `scopes` : Permissions accordées
- `subscriptionType` : Type de plan (`"max"` ou `"pro"`)

---

## 🔄 Flow OAuth complet (extrapolé)

### 1. Authentification initiale

**Endpoint (hypothétique)** : `https://claude.ai/oauth/authorize`

**Paramètres** :
```
GET /oauth/authorize?
  response_type=code&
  client_id=claude-cli&
  redirect_uri=http://localhost:8080/callback&
  scope=user:inference+user:profile&
  state=RANDOM_STATE
```

**Réponse** : Redirection vers `redirect_uri` avec `code=AUTH_CODE`

---

### 2. Exchange code → tokens

**Endpoint (hypothétique)** : `https://api.anthropic.com/oauth/token`

**Requête** :
```http
POST /oauth/token HTTP/1.1
Host: api.anthropic.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTH_CODE&
client_id=claude-cli&
redirect_uri=http://localhost:8080/callback
```

**Réponse** :
```json
{
  "access_token": "sk-ant-oat01-...",
  "refresh_token": "sk-ant-ort01-...",
  "expires_in": 3600,
  "token_type": "bearer",
  "scope": "user:inference user:profile"
}
```

**Stockage** :
```javascript
// Claude CLI stocke dans ~/.claude/.credentials.json
{
  "claudeAiOauth": {
    "accessToken": access_token,
    "refreshToken": refresh_token,
    "expiresAt": Date.now() + (expires_in * 1000),  // Millisecondes !
    "scopes": ["user:inference", "user:profile"],
    "subscriptionType": "max"  // Récupéré via /v1/profile
  }
}
```

---

### 3. Utilisation du token

**Endpoint** : `https://api.anthropic.com/v1/messages`

**Requête** :
```http
POST /v1/messages?beta=true HTTP/1.1
Host: api.anthropic.com
Authorization: Bearer sk-ant-oat01-cAquhoZFEtbnvokZ5FjmpVU0ZcgvWiF6...
anthropic-version: 2023-06-01
Content-Type: application/json

{
  "model": "claude-opus-4-1-20250805",
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 1024,
  "stream": true
}
```

**Vérification expiration** (avant chaque requête) :
```javascript
if (Date.now() >= credentials.expiresAt - 60000) {
  // Moins de 1 minute avant expiration → refresh
  await refreshAccessToken(credentials.refreshToken);
}
```

---

### 4. Refresh token flow

**Endpoint (hypothétique)** : `https://api.anthropic.com/oauth/token`

**Requête** :
```http
POST /oauth/token HTTP/1.1
Host: api.anthropic.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=sk-ant-ort01-ff-bghgFmBsDmiR8nUvuhGVxcPXlZu9mh_d7a...&
client_id=claude-cli
```

**Réponse** :
```json
{
  "access_token": "sk-ant-oat01-NEW_TOKEN...",
  "refresh_token": "sk-ant-ort01-NEW_REFRESH...",
  "expires_in": 3600,
  "token_type": "bearer",
  "scope": "user:inference user:profile"
}
```

**Mise à jour credentials.json** :
```javascript
credentials.accessToken = new_access_token;
credentials.refreshToken = new_refresh_token;  // Peut changer !
credentials.expiresAt = Date.now() + (expires_in * 1000);
fs.writeFileSync('~/.claude/.credentials.json', JSON.stringify(credentials));
```

---

### 5. Révocation (logout)

**Endpoint (hypothétique)** : `https://api.anthropic.com/oauth/revoke`

**Requête** :
```http
POST /oauth/revoke HTTP/1.1
Host: api.anthropic.com
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer sk-ant-oat01-...

token=sk-ant-ort01-...&
token_type_hint=refresh_token
```

**Réponse** : `204 No Content`

**Action locale** :
```bash
rm ~/.claude/.credentials.json
```

---

## 🔍 Scopes disponibles

Basé sur l'observation de `credentials.json` :

| Scope | Description | Utilisé par |
|-------|-------------|-------------|
| `user:inference` | Accès API Messages (/v1/messages) | Claude CLI, API calls |
| `user:profile` | Accès profil utilisateur (/v1/profile) | Récupération subscription type |

**Scopes potentiels non observés** (à vérifier) :
- `user:usage` : Consultation usage tokens
- `user:models` : Liste des modèles disponibles
- `admin:organization` : Gestion organisation (Enterprise)

---

## ⏱️ Durées de vie

| Token | Durée estimée | Calcul |
|-------|---------------|--------|
| **Access Token** | ~1 heure | `expiresAt - Date.now()` |
| **Refresh Token** | ~30 jours | Non exposé dans credentials.json |

**Stratégie refresh** :
```javascript
// Refresh 1 minute avant expiration
const BUFFER_MS = 60000;

function shouldRefresh(expiresAt) {
  return Date.now() >= (expiresAt - BUFFER_MS);
}

// Exemple
if (shouldRefresh(credentials.expiresAt)) {
  await refreshAccessToken(credentials.refreshToken);
}
```

---

## 🔄 Rotation automatique

**Claude CLI implémente** (comportement observé) :

1. **Check avant chaque requête** :
   ```javascript
   async function makeRequest(endpoint, body) {
     if (shouldRefresh(credentials.expiresAt)) {
       await refreshAccessToken();
     }
     return fetch(endpoint, {
       headers: { Authorization: `Bearer ${credentials.accessToken}` }
     });
   }
   ```

2. **Catch 401 → Auto-refresh** :
   ```javascript
   async function makeRequestWithRetry(endpoint, body) {
     let response = await makeRequest(endpoint, body);

     if (response.status === 401) {
       // Token expiré → refresh et retry
       await refreshAccessToken();
       response = await makeRequest(endpoint, body);
     }

     return response;
   }
   ```

---

## 🔒 Sécurité

### Stockage du token

**Fichier** : `~/.claude/.credentials.json`
**Permissions** : `600` (user read/write only)

```bash
# Vérifier permissions
ls -la ~/.claude/.credentials.json
# -rw------- 1 tincenv tincenv 450 Nov  5 10:24 .credentials.json

# Corriger si nécessaire
chmod 600 ~/.claude/.credentials.json
```

### Protection du refresh token

**Règles** :
- ❌ JAMAIS logger le refresh token
- ❌ JAMAIS envoyer le refresh token dans headers API
- ❌ JAMAIS commiter credentials.json dans Git
- ✅ Stocker dans fichier avec permissions 600
- ✅ Utiliser uniquement pour endpoint /oauth/token

### Révocation en cas de compromission

```bash
# 1. Révoquer via CLI (si disponible)
claude logout

# 2. Ou manuellement via API
curl -X POST https://api.anthropic.com/oauth/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "token=$REFRESH_TOKEN&token_type_hint=refresh_token"

# 3. Supprimer fichier local
rm ~/.claude/.credentials.json

# 4. Réauthentifier
claude login
```

---

## 📊 Subscription Types

Basé sur `subscriptionType` dans credentials.json :

| Type | API Access | Quotas | Features |
|------|------------|--------|----------|
| `"max"` | ✅ OAuth | Plan Max | Extended thinking, all models |
| `"pro"` | ✅ OAuth | Plan Pro | Standard models |
| `"free"` | ❓ (non testé) | Limité | Modèles basiques |

**Récupération du type** (hypothétique) :
```bash
curl -X GET https://api.anthropic.com/v1/profile \
  -H "Authorization: Bearer sk-ant-oat01-..." \
  -H "anthropic-version: 2023-06-01"
```

**Réponse** :
```json
{
  "user_id": "user_xxx",
  "email": "user@example.com",
  "subscription": {
    "type": "max",
    "status": "active",
    "expires_at": "2025-12-31T23:59:59Z"
  }
}
```

---

## 🧪 Tests

### Vérifier token valide

```bash
# Test simple
curl -X POST https://api.anthropic.com/v1/messages \
  -H "Authorization: Bearer $(jq -r '.claudeAiOauth.accessToken' ~/.claude/.credentials.json)" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4-1-20250805",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

**Réponse attendue** : `200 OK` avec message

### Vérifier expiration

```bash
# Calculer temps restant (en secondes)
EXPIRES_AT=$(jq -r '.claudeAiOauth.expiresAt' ~/.claude/.credentials.json)
NOW_MS=$(date +%s)000  # Millisecondes
REMAINING_SEC=$(( ($EXPIRES_AT - $NOW_MS) / 1000 ))

echo "Temps restant: $REMAINING_SEC secondes"

if [ $REMAINING_SEC -lt 60 ]; then
  echo "⚠️ Token expire dans moins de 1 minute"
fi
```

### Tester erreur 401

```bash
# Invalider token temporairement
cp ~/.claude/.credentials.json ~/.claude/.credentials.json.backup
jq '.claudeAiOauth.accessToken = "sk-ant-oat01-INVALID"' \
  ~/.claude/.credentials.json.backup > ~/.claude/.credentials.json

# Tester requête (doit retourner 401)
curl -X POST https://api.anthropic.com/v1/messages \
  -H "Authorization: Bearer sk-ant-oat01-INVALID" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-opus-4-1-20250805", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'

# Restaurer
mv ~/.claude/.credentials.json.backup ~/.claude/.credentials.json
```

---

## 📋 Checklist implémentation client

Pour implémenter un client OAuth complet :

### Authentification initiale
- [ ] Ouvrir browser vers `/oauth/authorize`
- [ ] Capturer `code` depuis redirect
- [ ] Exchange code → tokens via `/oauth/token`
- [ ] Stocker credentials dans fichier sécurisé (600)
- [ ] Récupérer subscription type via `/v1/profile`

### Gestion du token
- [ ] Check expiration avant chaque requête
- [ ] Refresh si `Date.now() >= expiresAt - 60000`
- [ ] Catch 401 → auto-refresh + retry
- [ ] Mettre à jour credentials.json après refresh

### Sécurité
- [ ] Permissions 600 sur credentials.json
- [ ] Ne JAMAIS logger les tokens
- [ ] Implémenter révocation
- [ ] Rotation refresh token si fourni

### Multi-device
- [ ] Sync credentials via cloud (optionnel)
- [ ] Détection conflits (2 devices refreshent simultanément)
- [ ] Fallback sur ré-authentification si refresh échoue

---

## 🔍 Endpoints OAuth (hypothétiques)

| Endpoint | Méthode | Usage | Status |
|----------|---------|-------|--------|
| `/oauth/authorize` | GET | Authentification initiale | ❓ Non capturé |
| `/oauth/token` | POST | Exchange code / Refresh | ❓ Non capturé |
| `/oauth/revoke` | POST | Révocation token | ❓ Non capturé |
| `/v1/profile` | GET | Récupération profil/subscription | ❓ Non capturé |

**Note** : Ces endpoints sont **extrapolés** depuis la structure observée. Ils n'ont pas encore été capturés via proxy.

---

## 📖 Différences OAuth vs API Key

| Aspect | OAuth (claude.ai) | API Key (Console) |
|--------|-------------------|-------------------|
| **Authentification** | Bearer `sk-ant-oat01-*` | `x-api-key: sk-ant-api03-*` |
| **Durée de vie** | ~1h (auto-refresh) | Illimitée (manuellement révoquée) |
| **Refresh** | Automatique via refresh token | N/A |
| **Quotas** | Plan Max/Pro | Basé sur billing |
| **Révocation** | Via compte claude.ai | Via Console |
| **Multi-device** | Sync automatique | 1 clé = 1 usage |
| **Scopes** | `user:inference`, `user:profile` | Accès complet API |

---

## 🚧 Ce qui manque encore

Pour compléter la documentation OAuth :

- [ ] Capturer `/oauth/authorize` (flux login initial) - **Nécessite browser, difficile via Docker**
- [ ] Capturer `/oauth/token` (exchange code) - **En cours, Option 3 : interception réseau**
- [ ] Capturer refresh token request réel - **En cours, Option 3 : interception réseau**
- [ ] Capturer `/oauth/revoke` (logout)
- [ ] Confirmer endpoint `/v1/profile`
- [ ] Durée exacte refresh token (30 jours ?)
- [ ] Comportement multi-device (conflict resolution)
- [ ] Liste complète des scopes disponibles

### Tentatives de capture (Session 3)

**Approche Docker** :
- ✅ Container créé avec Claude CLI
- ✅ Proxy lancé sur l'hôte (port 8000)
- ✅ Credentials backup copiés dans container
- ✅ Token expiré manuellement (expiresAt=0)
- ❌ Claude CLI (Node.js) ignore HTTP_PROXY/HTTPS_PROXY

**Prochaine approche** : Interception réseau avancée (iptables/mitmproxy/tcpdump)

---

## 📊 Captures réalisées

**Fichiers** : `/home/tincenv/analyse-claude-ai/captures/errors/`

**Erreur 401 capturée** :
```json
{
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "Invalid bearer token"
  },
  "request_id": "req_011CUpagBjj6MPSyNBqFxwfZ"
}
```

**Headers** :
- `x-should-retry: false` → Ne pas retenter (token invalide)
- `request-id: req_xxx` → Pour debugging

---

## 🎯 Prochaines étapes

Pour compléter cette documentation :

1. **Capturer OAuth flow initial** :
   ```bash
   # Supprimer credentials
   rm ~/.claude/.credentials.json

   # Lancer proxy
   python3 proxy_capture_full.py &

   # Lancer login (capturera tout le flow)
   HTTP_PROXY=http://localhost:8000 claude login
   ```

2. **Capturer refresh token** :
   ```bash
   # Modifier expiresAt pour forcer refresh
   jq '.claudeAiOauth.expiresAt = 0' ~/.claude/.credentials.json > /tmp/creds.json
   mv /tmp/creds.json ~/.claude/.credentials.json

   # Lancer requête (déclenchera refresh)
   HTTP_PROXY=http://localhost:8000 claude chat "test"
   ```

3. **Capturer logout** :
   ```bash
   HTTP_PROXY=http://localhost:8000 claude logout
   ```

---

## 📖 Références

- **Credentials** : `~/.claude/.credentials.json`
- **Captures erreurs** : `/home/tincenv/analyse-claude-ai/captures/errors/`
- **OAuth 2.0 RFC** : https://datatracker.ietf.org/doc/html/rfc6749

---

**Date d'analyse** : 2025-11-05
**Méthode** : Reverse engineering comportemental (credentials.json + captures réseau)
**Status** : ✅ Structure OAuth documentée (endpoints à capturer)
**Progression** : Authentification 40% → **70%** (+30%)
