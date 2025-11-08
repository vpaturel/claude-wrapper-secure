# 🔄 WORKFLOW - Documentation Claude OAuth API

**⚠️ LIRE CE FICHIER AVANT TOUTE TÂCHE LIÉE À CE PROJET**

---

## 🎯 OBJECTIF DU PROJET

Créer la documentation complète et technique de l'API Claude via authentification OAuth (compte claude.ai Max/Pro).

**État actuel** : 25% complété
**Localisation** : `/home/tincenv/analyse-claude-ai/`

---

## 📋 WORKFLOW OBLIGATOIRE

### AVANT chaque tâche :

```bash
# 1. Vérifier l'état actuel
cat /home/tincenv/analyse-claude-ai/SUMMARY.txt

# 2. Lire le plan détaillé
cat /home/tincenv/analyse-claude-ai/PLAN_COMPLETION.md | less

# 3. Vérifier la progression
grep "Priority: HIGH" /home/tincenv/analyse-claude-ai/PLAN_COMPLETION.md
```

### PENDANT chaque tâche :

1. **Suivre les instructions** du PLAN_COMPLETION.md
2. **Capturer les données** nécessaires
3. **Sauvegarder** dans la structure appropriée (`captures/`)
4. **Documenter** immédiatement les findings

### APRÈS chaque tâche :

```bash
# 1. Mettre à jour la progression
vim /home/tincenv/analyse-claude-ai/README.md
# → Modifier le % de complétion

# 2. Ajouter les findings
vim /home/tincenv/analyse-claude-ai/analyse_claude_api.md
# → Ajouter les nouvelles découvertes

# 3. Cocher les checkboxes
vim /home/tincenv/analyse-claude-ai/PLAN_COMPLETION.md
# → Remplacer [ ] par [x]

# 4. Mettre à jour le résumé si nécessaire
vim /home/tincenv/analyse-claude-ai/SUMMARY.txt
```

---

## 📂 STRUCTURE DU PROJET

```
/home/tincenv/analyse-claude-ai/
├── WORKFLOW.md                 # ⚠️ CE FICHIER - LIRE EN PREMIER
├── README.md                   # Index + progression
├── PLAN_COMPLETION.md          # Plan détaillé - À SUIVRE
├── SUMMARY.txt                 # Résumé visuel rapide
├── analyse_claude_api.md       # Analyse technique (À METTRE À JOUR)
│
├── captures/                   # Captures organisées
│   ├── requests/              # Requêtes HTTP brutes
│   ├── responses/             # Réponses HTTP brutes
│   ├── errors/                # Erreurs capturées (401, 429, etc.)
│   ├── oauth/                 # Flow OAuth (authorize, token, refresh)
│   ├── streaming/             # Events SSE complets
│   └── features/              # Features (tools, images, thinking)
│
├── tools/                      # Scripts & outils
│   ├── proxy_capture.py       # Proxy HTTP actuel
│   └── [futurs scripts]
│
└── [fichiers temporaires]
    ├── claude_capture.json    # Première capture (à archiver)
    └── mitmproxy_install/     # Installation mitmproxy
```

---

## 🎯 RÈGLES STRICTES

### ✅ TOUJOURS

1. **TOUJOURS** lire WORKFLOW.md → README.md → PLAN_COMPLETION.md avant de commencer
2. **TOUJOURS** mettre à jour la progression après chaque action
3. **TOUJOURS** sauvegarder les captures dans `captures/[catégorie]/`
4. **TOUJOURS** documenter les findings immédiatement dans analyse_claude_api.md
5. **TOUJOURS** cocher les checkboxes accomplies dans PLAN_COMPLETION.md
6. **TOUJOURS** nommer les fichiers avec timestamps : `YYYYMMDD_HHMMSS_description.json`

### ❌ JAMAIS

1. **JAMAIS** commencer une tâche sans vérifier l'état actuel
2. **JAMAIS** sauvegarder des captures en vrac (utiliser captures/)
3. **JAMAIS** oublier de mettre à jour la documentation
4. **JAMAIS** partager les tokens OAuth capturés
5. **JAMAIS** modifier le CLAUDE.md global (~/.claude/CLAUDE.md)

---

## ⚡ QUICK START

### Si demande liée à Claude API OAuth :

```bash
# 1. Check status
cat /home/tincenv/analyse-claude-ai/SUMMARY.txt

# 2. Identifier prochaine action prioritaire
grep -A 5 "ÉTAPE 1" /home/tincenv/analyse-claude-ai/PLAN_COMPLETION.md

# 3. Exécuter l'action
# (suivre les instructions du PLAN_COMPLETION.md)

# 4. Update docs
cd /home/tincenv/analyse-claude-ai
# → Mettre à jour README.md, analyse_claude_api.md, PLAN_COMPLETION.md
```

---

## 📊 CONVENTIONS DE NOMMAGE

### Fichiers de captures

```
captures/
├── streaming/
│   ├── 20251105_102548_simple_request.json
│   ├── 20251105_103012_medium_request.json
│   └── 20251105_103445_long_request.json
│
├── errors/
│   ├── 20251105_104521_error_401_unauthorized.json
│   ├── 20251105_104833_error_429_rate_limit.json
│   └── 20251105_105124_error_400_bad_request.json
│
└── features/
    ├── 20251105_110234_tool_calling.json
    ├── 20251105_110912_image_upload.json
    └── 20251105_111445_extended_thinking.json
```

**Format** : `YYYYMMDD_HHMMSS_description.json`

---

## 🚨 RAPPELS CRITIQUES

### Sécurité
- ⚠️ **Tous les tokens OAuth capturés sont SENSIBLES**
- ⚠️ Ne JAMAIS commit sur Git sans redaction
- ⚠️ Ne JAMAIS partager claude_capture.json
- ⚠️ Toujours backup ~/.claude/.credentials.json avant tests

### Scope du projet
- ✅ Ce projet documente l'API **OAuth (claude.ai)**
- ❌ PAS l'API Key (Anthropic Console)
- ✅ Endpoint : `api.anthropic.com/v1/messages`
- ❌ PAS `claude.ai/api` (sauf Artifacts)

### Organisation
- Toujours sauvegarder dans `captures/[catégorie]/`
- Toujours documenter dans `analyse_claude_api.md`
- Toujours mettre à jour `README.md` (progression %)
- Toujours cocher dans `PLAN_COMPLETION.md`

---

## 📈 TRACKING PROGRESSION

### Méthode 1 : Checklist PLAN_COMPLETION.md

```markdown
- [ ] Action non commencée
- [x] Action terminée
```

### Méthode 2 : README.md

```markdown
[████████░░░░░░░░░░░░░░░░░░░░] 25%
```

Mettre à jour après chaque section complétée.

### Méthode 3 : SUMMARY.txt

Régénérer le résumé visuel tous les 10-20% de progression.

---

## 🎯 PROCHAINES ACTIONS (PHASE 1)

**À faire dans l'ordre (voir PLAN_COMPLETION.md pour détails)** :

1. ⏳ Améliorer proxy (sans troncature)
2. ⏳ Capturer streaming complet
3. ⏳ Capturer erreurs HTTP (401, 429, 400)
4. ⏳ Capturer token refresh
5. ⏳ Analyser code Claude CLI

**Temps estimé Phase 1** : 2-3 heures

---

## 📞 EN CAS DE DOUTE

1. **Relire WORKFLOW.md** (ce fichier)
2. **Consulter PLAN_COMPLETION.md** (actions détaillées)
3. **Vérifier SUMMARY.txt** (état global)
4. **Demander à l'utilisateur** si ambiguïté

---

## ✅ CHECKLIST AVANT DE COMMENCER UNE TÂCHE

```
[ ] J'ai lu WORKFLOW.md
[ ] J'ai lu README.md (progression actuelle)
[ ] J'ai lu PLAN_COMPLETION.md (plan détaillé)
[ ] J'ai vérifié SUMMARY.txt (état global)
[ ] Je sais quelle action faire (Phase X, Étape Y)
[ ] J'ai les outils nécessaires (proxy, scripts)
[ ] Je sais où sauvegarder (captures/[catégorie]/)
[ ] Je sais quoi mettre à jour après (docs)
```

Si tous les [ ] sont cochés → GO ! 🚀

---

**VERSION** : 1.0
**DERNIÈRE MÀJ** : 2025-11-05
**AUTEUR** : tincenv
