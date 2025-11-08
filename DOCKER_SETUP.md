# 🐳 Setup Docker pour tests OAuth

**Date** : 2025-11-05
**Objectif** : Créer environnement isolé pour tester OAuth sans impacter session active

---

## 📦 Image Docker créée

**Fichier** : `Dockerfile.test`

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    curl jq ca-certificates gnupg lsb-release nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash testuser
USER testuser
WORKDIR /home/testuser

CMD ["/bin/bash"]
```

**Build** :
```bash
docker build -f Dockerfile.test -t claude-test:latest .
```

---

## 🚀 Container lancé

**Commande** :
```bash
docker run -d --name claude-oauth-test \
  --network host \
  -v /home/tincenv/.local/share/claude:/opt/claude:ro \
  claude-test:latest tail -f /dev/null
```

**Vérification** :
```bash
docker exec claude-oauth-test /opt/claude/versions/2.0.33 --version
# Output: 2.0.33 (Claude Code)
```

---

## 🔐 Credentials copiés

**Backup utilisé** : `~/.claude/.credentials.json.backup_20251105_112519`

```bash
# 1. Créer répertoire
docker exec claude-oauth-test mkdir -p /home/testuser/.claude

# 2. Copier backup (pas les credentials actuels !)
docker cp ~/.claude/.credentials.json.backup_20251105_112519 \
  claude-oauth-test:/home/testuser/.claude/.credentials.json

# 3. Forcer expiration (dans le container uniquement)
docker exec claude-oauth-test bash -c \
  "jq '.claudeAiOauth.expiresAt = 0' /home/testuser/.claude/.credentials.json > /tmp/expired.json && \
   mv /tmp/expired.json /home/testuser/.claude/.credentials.json"
```

**Résultat** :
- ✅ Token expiré dans container
- ✅ Credentials originaux intacts sur l'hôte
- ✅ Isolation complète

---

## 🌐 Proxy lancé

**Commande** :
```bash
cd /home/tincenv/analyse-claude-ai
python3 proxy_capture_full.py > /tmp/proxy_oauth.log 2>&1 &
```

**Vérification** :
```bash
curl -s http://localhost:8000 | head -3
# Output: HTTP proxy page (proxy actif)
```

---

## ❌ Problème rencontré : Node.js ignore HTTP_PROXY

**Tentative** :
```bash
docker exec claude-oauth-test bash -c \
  "HTTP_PROXY=http://localhost:8000 HTTPS_PROXY=http://localhost:8000 \
   /opt/claude/versions/2.0.33 --print 'hello'"
```

**Résultat** : Claude CLI (Node.js) **ignore** les variables `HTTP_PROXY` et `HTTPS_PROXY`

**Causes possibles** :
1. Node.js utilise son propre agent HTTP (ne respecte pas proxy system)
2. Claude CLI peut avoir hardcodé `proxy: false` dans ses requêtes
3. Nécessite configuration via `NODE_OPTIONS` ou certificats

**Vérification** :
```bash
docker exec claude-oauth-test curl -s -x http://localhost:8000 http://httpbin.org/ip
# → Fonctionne avec curl (proxy OK)

# Mais Claude CLI ne passe pas par le proxy
```

---

## 🎯 Prochaines approches (Option 3)

### Approche 1 : NODE_EXTRA_CA_CERTS + mitmproxy

**Principe** : Forcer Node.js à accepter le certificat du proxy MITM

```bash
# 1. Générer certificat mitmproxy
mitmproxy --set confdir=~/.mitmproxy
cp ~/.mitmproxy/mitmproxy-ca-cert.pem /tmp/mitm-ca.pem

# 2. Lancer mitmproxy
mitmproxy -p 8080 --mode regular

# 3. Forcer Node.js
docker exec claude-oauth-test bash -c \
  "NODE_EXTRA_CA_CERTS=/tmp/mitm-ca.pem \
   HTTPS_PROXY=http://localhost:8080 \
   /opt/claude/versions/2.0.33 --print 'hello'"
```

### Approche 2 : iptables redirect

**Principe** : Rediriger **tout** le trafic HTTPS (443) du container vers le proxy

```bash
# Rediriger port 443 → 8000 pour le container
sudo iptables -t nat -A OUTPUT \
  -p tcp --dport 443 \
  -m owner --uid-owner $(id -u testuser) \
  -j REDIRECT --to-port 8000
```

### Approche 3 : tcpdump + analyse manuelle

**Principe** : Capturer le trafic brut réseau et analyser

```bash
# Capturer trafic du container
sudo tcpdump -i any -w /tmp/claude_oauth.pcap \
  'host api.anthropic.com and port 443'

# Dans une autre terminal : déclencher requête Claude
docker exec claude-oauth-test /opt/claude/versions/2.0.33 --print 'hello'

# Analyser avec Wireshark
wireshark /tmp/claude_oauth.pcap
```

### Approche 4 : Strace

**Principe** : Observer les syscalls réseau de Claude CLI

```bash
docker exec claude-oauth-test bash -c \
  "strace -f -e trace=network /opt/claude/versions/2.0.33 --print 'hello' 2>&1 | grep connect"
```

---

## 📋 État actuel

- ✅ Docker setup complet
- ✅ Credentials isolés
- ✅ Proxy actif
- ❌ Capture refresh token échouée (Node.js ignore proxy)
- ⏳ Tentative Option 3 en cours

---

## 🧹 Cleanup

```bash
# Supprimer container
docker stop claude-oauth-test
docker rm claude-oauth-test

# Supprimer image
docker rmi claude-test:latest

# Tuer proxy
pkill -f proxy_capture_full.py
```

---

**Date** : 2025-11-05
**Status** : En cours, Option 3 à tester
