# Process Pool V33 - SSE Stream Fix

## Problème identifié (V32)

Le endpoint `/v1/messages/pooled` en V32 fonctionnait correctement MAIS le stream SSE ne se fermait jamais, causant des timeouts côté client.

### Symptômes
- ✅ Process pool fonctionnel (création/réutilisation OK)
- ✅ Réponses Claude correctes
- ❌ Stream HTTP reste ouvert indéfiniment
- ❌ Client curl bloque jusqu'au timeout (>2 minutes)

### Cause
Le processus Claude CLI reste en vie dans le pool (comportement voulu), mais le générateur SSE Python continuait à attendre de nouveaux événements sans jamais terminer la connexion HTTP.

## Solution (V33)

### Changement code

**Fichier**: `claude_oauth_api_secure_multitenant.py:1523-1526`

```python
yield event

# Check if this is the final result event (end of conversation)
if isinstance(event, dict) and event.get("type") == "result":
    logger.info(f"✅ Conversation completed for user: {user_id[:8]}... (keeping process alive)")
    break
```

### Logique
1. Le générateur yield tous les événements SSE
2. Détecte l'événement `{"type": "result"}` (fin de conversation)
3. Ferme le stream HTTP en sortant du loop `while True`
4. **Le processus reste en vie** dans le pool pour les requêtes suivantes

## Tests

### Test local (V33)
```bash
timeout 10 curl -N http://localhost:8080/v1/messages/pooled -d '...'
```

**Résultat**:
- ✅ Stream fermé en <10s (pas de timeout)
- ✅ Processus gardé en vie (PID constant)
- ✅ Log: "Conversation completed for user... (keeping process alive)"

### Performance
- **V32**: Timeout après >120s
- **V33**: Stream fermé en ~5s (après réception du résultat)

## Déploiement

```bash
# Build v33
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v33 --project=claude-476509

# Deploy
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v33 \
  --project=claude-476509 \
  --region=europe-west1
```

## Vérification production

Script de test: `/tmp/test_production_v33.sh`

**Attendu**:
1. Requête 1 complète en <15s (création process)
2. Requête 2 complète en <15s (réutilisation process)
3. PID identique entre req1 et req2
4. Pool stats montrent `pool_size: 1`, `alive: true`

## Impact

### Avant (V32)
- Client bloqué jusqu'au timeout réseau (~2min)
- Expérience utilisateur dégradée
- Scripts curl/tests inutilisables

### Après (V33)
- Stream fermé proprement après réponse (~5s)
- Expérience utilisateur fluide
- Process pool pleinement fonctionnel
- Économies de latence maintenues (2.1× plus rapide req2+)

## Commits

- **ff951ad**: "fix(pooled): Close SSE stream after 'result' event while keeping process alive"
- Fichiers modifiés: `claude_oauth_api_secure_multitenant.py` (+5 lignes)
- Repository: https://github.com/vpaturel/claude-wrapper-secure

## Versions

| Version | État | Description |
|---------|------|-------------|
| v32 | ⚠️ Bug | Process pool OK, stream hang |
| v33 | ✅ Fixé | Stream fermé proprement, pool OK |

---

**Date**: 2025-11-08
**Auteur**: Claude Code (fix détecté et implémenté)
**Production**: wrapper.claude.serenity-system.fr
**Status**: Ready to deploy
