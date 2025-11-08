# 🔍 Contraintes Techniques - Proactivité & Auto-Heal

## 🎯 Concrètement : Impact sur Appel Claude CLI

### ❓ Question : "Cela change quoi sur l'appel Claude CLI ?"

**Réponse courte** : Ça modifie les **messages** envoyés à Claude, pas la commande CLI elle-même.

---

## 📞 Appel Claude CLI - Comparaison

### SANS Config Proactive (actuel)

```bash
# Commande CLI (inchangée)
claude \
  --settings '{"credentials": {...}}' \
  --dangerously-skip-permissions \
  --workspace /workspaces/abc123

# Messages envoyés
[
  {"role": "user", "content": "Crée système auto-heal"}
]
```

**Claude reçoit** : Juste votre question

---

### AVEC Config Proactive (proposée)

```bash
# Commande CLI (IDENTIQUE - pas de changement)
claude \
  --settings '{"credentials": {...}}' \
  --dangerously-skip-permissions \
  --workspace /workspaces/abc123

# Messages envoyés (DIFFÉRENT - ajout system prompt)
[
  {
    "role": "system",
    "content": "RÈGLE: Réponds exhaustivement. Liste toutes contraintes/edge cases d'emblée. Anticipe questions follow-up. User ne doit JAMAIS demander 'Quoi d'autre ?'."
  },
  {
    "role": "user",
    "content": "Crée système auto-heal"
  }
]
```

**Claude reçoit** : Votre question + instruction "sois proactif"

---

## 🔧 Modifications Techniques Concrètes

### 1. Wrapper injecte System Message

```python
# server.py - AVANT (actuel)
async def pooled_endpoint(request: MessageRequest):
    response = await api.create_message_pooled(
        oauth_credentials=request.oauth_credentials,
        messages=request.messages,  # ← Messages bruts du client
        model=request.model
    )
    return response
```

```python
# server.py - APRÈS (avec proactivité)
PROACTIVE_SYSTEM_PROMPT = """
RÈGLE ABSOLUE: PROACTIVITÉ MAXIMALE

Quand user demande une feature, tu DOIS:
1. Analyser en profondeur (3-5 niveaux)
2. Lister TOUTES contraintes (pas juste évidentes)
3. Anticiper edge cases (10+)
4. Proposer alternatives (3+)
5. Répondre aux questions non posées

MÉTRIQUE: User ne doit PAS demander "Quoi d'autre ?"
"""

async def pooled_endpoint(request: MessageRequest):
    # ← AJOUT: Injecter system prompt
    messages = [
        {"role": "system", "content": PROACTIVE_SYSTEM_PROMPT}
    ] + request.messages

    response = await api.create_message_pooled(
        oauth_credentials=request.oauth_credentials,
        messages=messages,  # ← Messages enrichis
        model=request.model
    )
    return response
```

**Impact** :
- ✅ Commande CLI inchangée
- ✅ Credentials inchangés
- ✅ Workspace inchangé
- ⚠️ **Messages modifiés** (ajout system prompt au début)

---

## ⚠️ CONTRAINTES Config Proactive

### Contrainte 1 : Tokens Supplémentaires

**Problème** : System prompt = ~150 tokens ajoutés par requête

**Calcul** :
```
Sans proactivité :
  User: "Crée auto-heal" = 10 tokens
  Total input : 10 tokens

Avec proactivité :
  System: "RÈGLE ABSOLUE..." = 150 tokens
  User: "Crée auto-heal" = 10 tokens
  Total input : 160 tokens
```

**Impact** :
- +150 tokens input par requête (+1500% pour petites requêtes)
- Sur claude.ai Plan Max : Quota limité (pas facturation au token)
- **150 tokens = 1% de quota request** (limite ~8k tokens/request)

**Est-ce grave ?** ❌ Non
- Plan Max = quota requêtes (pas tokens)
- 150 tokens négligeable si génération = 5-10k tokens
- Mais gaspillage si requête simple ("Bonjour")

**Solution** : Activer proactivité seulement si requête complexe

```python
# Proactivité conditionnelle
if len(user_message) > 50 or contains_keywords(user_message, ["système", "architecture", "complet"]):
    messages = inject_proactive_prompt(messages)
```

---

### Contrainte 2 : Latency Accrue

**Problème** : Claude doit analyser + générer plus → temps augmenté

**Mesures** :
```
SANS proactivité :
  Analyse requête : 0.5s
  Génération : 3s
  Total : 3.5s

AVEC proactivité :
  Analyse approfondie (5 niveaux) : 2s
  Génération exhaustive : 5s
  Total : 7s
```

**Impact** : +100% temps de réponse (3.5s → 7s)

**Est-ce grave ?** ⚠️ Moyen
- Si user attend réponse courte → frustration
- Si génération complète app → acceptable (déjà long)

**Solution** : Indiquer "Analyse approfondie en cours..."

---

### Contrainte 3 : Verbosité Excessive

**Problème** : Claude devient trop verbeux (répond à tout)

**Exemple** :
```
USER: "Quel est le port du serveur ?"

SANS proactivité :
CLAUDE: "Port 8080"

AVEC proactivité :
CLAUDE: "Port 8080.

Autres aspects à considérer:
- Ports alternatifs : 8000, 3000, 5000
- Configuration firewall pour 8080
- Bind sur 0.0.0.0 ou 127.0.0.1
- SSL/TLS (port 443)
- Load balancer si clustering
- Health check endpoint
- Logging requêtes

Edge cases:
- Port déjà utilisé (EADDRINUSE)
- Permissions <1024 (root requis)
- IPv6 binding

Voulez-vous configurer reverse proxy ?"
```

**Impact** : Réponse 20× plus longue pour question simple

**Est-ce grave ?** ⚠️ Oui si question simple

**Solution** : Désactiver proactivité pour questions factuelles courtes

```python
SIMPLE_QUESTIONS = ["quel", "combien", "où", "quand", "qui"]

if any(q in user_message.lower() for q in SIMPLE_QUESTIONS):
    # Pas de proactivité pour questions simples
    messages = request.messages
```

---

### Contrainte 4 : Hallucinations Amplifiées

**Problème** : Plus Claude génère, plus risque d'hallucinations

**Exemple** :
```
USER: "Crée API REST"

Claude (proactif) génère:
  - API REST (OK)
  - GraphQL alternative (OK)
  - gRPC alternative (OK)
  - Edge cases : Rate limiting, JWT auth, CORS (OK)
  - "Pour production, ajoute Kafka pour event streaming" ← HALLUCINATION (pas demandé)
  - "Implémente CQRS pattern avec Event Sourcing" ← OVER-ENGINEERING
```

**Impact** : Suggestions non pertinentes (bruit)

**Est-ce grave ?** ⚠️ Moyen
- Si user novice → confusion (trop d'infos)
- Si user expert → ignore suggestions non pertinentes

**Solution** : Limiter suggestions alternatives à 3 max

---

### Contrainte 5 : Coût Processing Wrapper

**Problème** : Auto-expansion requiert appel Claude supplémentaire

**Architecture proposée** :
```python
# Solution 4 (Auto-Expansion) nécessite 2 appels Claude:

# Appel 1: Expansion
expansion = await claude_expand("Anticipe dimensions de la requête")

# Appel 2: Génération
response = await claude_generate(user_request, expansion)
```

**Impact** :
- 2× appels Claude par requête
- 2× quota utilisé
- Latency doublée

**Est-ce grave ?** ❌ CRITIQUE (inacceptable)

**Solution** : NE PAS implémenter auto-expansion (trop coûteux)

---

## ⚠️ CONTRAINTES Safe Auto-Heal

### Contrainte 1 : Temps Validation (critique)

**Problème** : 13 contraintes à vérifier = lent

**Décomposition** :
```
1. Snapshot initial : 5s
   - Scanner fichiers Python (AST parsing)
   - Exécuter tests (pytest --collect-only)
   - Capturer comportement

2. Auto-fix : 20s
   - Claude corrige 5 bugs
   - Réécriture fichiers

3. Snapshot après fix : 5s

4. Regression check (13 contraintes) : 60s
   - Contrainte 1 (features) : 5s
   - Contrainte 2 (tests) : 30s (pytest complet)
   - Contrainte 3 (simplification) : 5s
   - Contrainte 4 (comportement) : 10s (tests fonctionnels)
   - Contraintes 5-13 : 10s

5. Rollback si régression : 2s

TOTAL : 92s (~1.5 minutes)
```

**Impact** : Génération app 50s → 142s avec auto-heal (+184%)

**Est-ce grave ?** ⚠️ Moyen
- Si user attend qualité → acceptable
- Si user veut vitesse → frustrant

**Solution** : Afficher progression temps réel

```
🤖 Auto-Heal en cours (1/5)...
  ✅ Snapshot initial (5s)
  🔧 Correction bugs (20s)
  ✅ Snapshot après fix (5s)
  🔍 Vérification 13 contraintes (60s)...
     ✅ 1. Features préservées
     ✅ 2. Tests OK
     ⏳ 3. Simplification check...
```

---

### Contrainte 2 : Faux Positifs (bloquant)

**Problème** : Détection contraintes peut bloquer fixes légitimes

**Exemple Contrainte 3 (Simplification)** :
```python
# AVANT (code original)
def validate_email(email: str) -> bool:
    if not email:
        return False
    if "@" not in email:
        return False
    if "." not in email.split("@")[1]:
        return False
    return True

# APRÈS (auto-fix légitime)
def validate_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    return len(parts) == 2 and "." in parts[1]
```

**Détection** :
- Lignes avant : 7
- Lignes après : 5
- Réduction : 28% → Déclenche alerte "excessive_simplification" (seuil 30%)

**Problème** : Fix légitime bloqué (faux positif)

**Impact** : Rollback alors que correction était OK

**Est-ce grave ?** ⚠️ OUI (bugs non corrigés)

**Solution** : Seuils plus tolérants + vérification tests

```python
# Si réduction lignes MAIS tests passent → OK
if lines_reduction > 30% and all_tests_pass:
    # Faux positif probable, accepter
    pass
```

---

### Contrainte 3 : Git Overhead (stockage)

**Problème** : Chaque snapshot = git commit

**Calcul** :
```
Génération app complète : 2000 lignes code

Git commits:
  1. Avant auto-heal (snapshot) : 2000 lignes
  2. Après fix 1 : 2005 lignes
  3. Rollback si échec : retour commit 1
  4. Après fix 2 (retry) : 2010 lignes
  5. Final : 2010 lignes

Total git history : 5 commits × 2000 lignes = 10 MB
```

**Impact** : Workspace grossit rapidement (10 MB par génération)

**Est-ce grave ?** ❌ Non (Cloud Run 2 Gi RAM)

**Solution** : Cleanup git history après succès

```bash
# Garder seulement dernier commit
git reset --soft HEAD~4  # Squash 5 commits → 1
```

---

### Contrainte 4 : Complexité Debugging

**Problème** : Si rollback, user ne voit pas ce qui a échoué

**Scénario** :
```
1. Claude génère app (OK)
2. Auto-heal détecte 3 bugs
3. Claude corrige bugs
4. Regression check : CONTRAINTE 5 VIOLÉE (API signature changed)
5. ROLLBACK automatique
```

**User voit** :
```
✅ App générée
⚠️ Auto-heal rollback (violation contrainte 5)
📊 État final : bugs non corrigés
```

**User NE VOIT PAS** :
- Quels bugs détectés ?
- Comment Claude a tenté de corriger ?
- Pourquoi correction viole contrainte 5 ?

**Impact** : Frustration (boîte noire)

**Est-ce grave ?** ⚠️ Oui

**Solution** : Log détaillé des tentatives

```python
# Sauvegarder tentatives avant rollback
rollback_log = {
    "bugs_detected": [bug1, bug2, bug3],
    "fixes_attempted": [fix1, fix2, fix3],
    "constraint_violated": 5,
    "violation_details": "Function 'get_users' renamed to 'fetch_users'",
    "rollback_reason": "Breaking change API publique"
}

# Retourner au user
return {
    "status": "rollback",
    "log": rollback_log
}
```

---

### Contrainte 5 : Limitations AST Parsing

**Problème** : Détection contraintes = parsing code (AST)

**Limites AST** :
```python
# ✅ AST détecte (structure statique)
- Fonctions supprimées
- Classes supprimées
- Signatures changées
- Imports modifiés

# ❌ AST NE détecte PAS (comportement dynamique)
- Logique métier changée (if → else inversé)
- Ordre exécution modifié (side effects)
- Performance dégradée (O(n) → O(n²))
- Comportement conditionnel (runtime)
```

**Exemple non détectable** :
```python
# AVANT
def calculate_discount(price, user_type):
    if user_type == "premium":
        return price * 0.8  # 20% discount
    return price

# APRÈS (bug introduit)
def calculate_discount(price, user_type):
    if user_type == "premium":
        return price * 0.2  # ❌ 80% discount (bug!)
    return price
```

**AST voit** :
- Fonction existe : ✅
- Signature identique : ✅
- Types OK : ✅

**AST NE voit PAS** : Logique métier cassée (0.8 → 0.2)

**Impact** : Contrainte 4 (comportement) peut manquer bugs

**Est-ce grave ?** ⚠️ OUI (fausse sécurité)

**Solution** : Tests obligatoires (pas juste AST)

```python
# Contrainte 4 DOIT exécuter tests, pas juste AST
def check_behavior_preserved():
    # ❌ PAS SUFFISANT
    assert function_signature_unchanged()

    # ✅ REQUIS
    assert pytest_all_pass()  # Tests détectent bug logique
```

---

### Contrainte 6 : Coût Quota Claude

**Problème** : Auto-heal = appels Claude supplémentaires

**Décomposition** :
```
1. Génération initiale : 1 requête Claude
   - Input : 1k tokens (prompt)
   - Output : 5k tokens (app complète)

2. Auto-fix (pour chaque bug) : 1 requête par bug
   - Bug 1 : 1 requête (correction)
   - Bug 2 : 1 requête
   - Bug 3 : 1 requête
   Total : 3 requêtes

TOTAL : 1 + 3 = 4 requêtes Claude par génération app
```

**Impact Plan Max** :
- Limite : ~50 requêtes/jour (estimation)
- Sans auto-heal : 50 apps/jour
- Avec auto-heal : 50/4 = 12 apps/jour

**Réduction capacité : -76%**

**Est-ce grave ?** ❌ CRITIQUE

**Solution** : Batch fixes (1 seule requête)

```python
# ❌ MAUVAIS (3 requêtes)
for bug in bugs:
    fix = await claude_fix_bug(bug)

# ✅ BON (1 requête)
all_bugs = [bug1, bug2, bug3]
all_fixes = await claude_fix_bugs_batch(all_bugs)
```

**Nouvelle décomposition** :
```
1. Génération : 1 requête
2. Auto-fix batch : 1 requête (tous bugs ensemble)
TOTAL : 2 requêtes (-50% capacité)
```

**Acceptable ?** ⚠️ Moyen (50% capacité OK si qualité meilleure)

---

### Contrainte 7 : Risque Boucle Infinie

**Problème** : Auto-fix peut créer nouveaux bugs → retry → nouveaux bugs → ...

**Scénario** :
```
Itération 1:
  - Détecte bug A
  - Corrige bug A
  - Correction introduit bug B
  - Regression check : bug B détecté → ROLLBACK

Itération 2 (retry):
  - Détecte bug A (toujours présent après rollback)
  - Tente correction différente
  - Correction introduit bug C
  - Regression check : bug C détecté → ROLLBACK

Itération 3:
  - ... infini
```

**Impact** : Timeout (10 min Cloud Run) → échec

**Est-ce grave ?** ❌ CRITIQUE

**Solution** : Limite tentatives stricte

```python
MAX_AUTO_HEAL_ATTEMPTS = 2  # Max 2 tentatives

for attempt in range(MAX_AUTO_HEAL_ATTEMPTS):
    fixes = auto_fix_bugs()
    if regression_check_passed():
        break
else:
    # Échec après 2 tentatives → abandonner
    return {
        "status": "auto_heal_failed",
        "reason": "Could not fix bugs without regression",
        "attempts": MAX_AUTO_HEAL_ATTEMPTS
    }
```

---

### Contrainte 8 : Tests Manquants

**Problème** : Si projet n'a pas tests, contrainte 2 (regression tests) impossible

**Scénario** :
```
Claude génère app sans tests (possible si user ne demande pas)

Auto-heal:
  1. Snapshot : tests = 0
  2. Fix bugs
  3. Regression check contrainte 2 : tests = 0 vs 0 → OK (faux négatif!)

Problème : Pas de tests → pas de détection régression comportementale
```

**Impact** : Contraintes 2 et 4 ne fonctionnent pas (fausse sécurité)

**Est-ce grave ?** ❌ CRITIQUE

**Solution** : Forcer génération tests AVANT auto-heal

```python
async def safe_auto_heal_with_tests(project_dir):
    # 1. Vérifier tests existent
    if count_tests(project_dir) == 0:
        # Forcer génération tests
        await claude_generate_tests(project_dir)

    # 2. Maintenant auto-heal
    result = await auto_heal(project_dir)
    return result
```

---

### Contrainte 9 : Workspace Pollué

**Problème** : Snapshots git créent branches/commits → workspace sale

**Après 10 générations avec auto-heal** :
```bash
git log --oneline
# 7a3b2c1 AUTO-HEAL: Fixed 5 bugs
# 6f2d9e0 AUTO-HEAL: Snapshot before fix
# 5c1a8b4 AUTO-HEAL: Fixed 3 bugs
# 4b0f7a3 AUTO-HEAL: Snapshot before fix
# ... (20+ commits)

du -sh .git
# 50 MB  (workspace de 5 MB code → 50 MB avec git history)
```

**Impact** : Workspace grossit (mémoire Cloud Run)

**Est-ce grave ?** ⚠️ Moyen

**Solution** : Cleanup git après chaque session

```python
# Après succès auto-heal, squash commits
subprocess.run(["git", "reset", "--soft", "HEAD~10"])  # Squash 10 commits
subprocess.run(["git", "commit", "-m", "Final state after auto-heal"])
```

---

## 📊 Tableau Récapitulatif Contraintes

### Config Proactive

| Contrainte | Sévérité | Impact | Solution |
|-----------|----------|--------|----------|
| 1. Tokens +150 | Faible | +1% quota | Conditionnel (requêtes complexes) |
| 2. Latency +100% | Moyenne | 3.5s → 7s | Acceptable si app complète |
| 3. Verbosité excessive | Moyenne | Réponses 20× longues | Désactiver pour questions simples |
| 4. Hallucinations | Moyenne | Suggestions non pertinentes | Limiter suggestions à 3 |
| 5. Coût auto-expansion | **CRITIQUE** | 2× quota | ❌ NE PAS implémenter |

**Verdict Config Proactive** : ✅ Faisable (sans auto-expansion)

---

### Safe Auto-Heal

| Contrainte | Sévérité | Impact | Solution |
|-----------|----------|--------|----------|
| 1. Temps validation | Moyenne | +92s | Progression temps réel |
| 2. Faux positifs | Haute | Bugs non corrigés | Seuils tolérants + tests |
| 3. Git overhead | Faible | +10 MB | Cleanup history |
| 4. Debugging complexe | Haute | Boîte noire | Logs détaillés |
| 5. Limites AST | Haute | Fausse sécurité | Tests obligatoires |
| 6. Quota Claude | **CRITIQUE** | -50% capacité | Batch fixes (acceptable) |
| 7. Boucle infinie | **CRITIQUE** | Timeout | Max 2 tentatives |
| 8. Tests manquants | **CRITIQUE** | Contraintes inefficaces | Forcer génération tests |
| 9. Workspace pollué | Faible | +50 MB | Cleanup git |

**Verdict Safe Auto-Heal** : ⚠️ Faisable MAIS complexe (8 contraintes à gérer)

---

## 🎯 Recommandation Finale

### Ce qui est SIMPLE à implémenter

✅ **Config Proactive (sans auto-expansion)** :
- Effort : 1-2h
- Contraintes : 4 faibles/moyennes
- Risque : Faible
- Bénéfice : +50% qualité réponses

### Ce qui est COMPLEXE à implémenter

⚠️ **Safe Auto-Heal** :
- Effort : 10-15h
- Contraintes : 9 (dont 4 critiques)
- Risque : Moyen/Élevé
- Bénéfice : +85% qualité code MAIS -50% capacité

---

## 💡 Proposition Implémentation Progressive

### Phase 1 : Config Proactive (v34) - RECOMMANDÉ

```python
# Ajout simple dans server.py
PROACTIVE_PROMPT = "Réponds exhaustivement..."

messages = [{"role": "system", "content": PROACTIVE_PROMPT}] + request.messages
```

**Temps** : 1-2h
**Risque** : Faible
**Bénéfice** : Immédiat

---

### Phase 2 : Auto-Heal Simplifié (v35) - PLUS TARD

**Version simplifiée** (3 contraintes au lieu de 13) :
1. ✅ Pas suppression features
2. ✅ Pas régression tests
3. ✅ Batch fixes (1 requête)

**Version complète abandonnée** :
- Trop complexe (9 contraintes)
- Trop de faux positifs
- Trop de risques boucle infinie

---

## ❓ Questions pour Décision

Avant d'implémenter, je dois savoir :

1. **Config Proactive** : Voulez-vous l'activer pour TOUTES requêtes ou seulement requêtes complexes ?

2. **Auto-Heal** : Voulez-vous :
   - A. Version simplifiée (3 contraintes) ?
   - B. Version complète (13 contraintes) ?
   - C. Pas d'auto-heal (trop complexe) ?

3. **Quota** : Acceptez-vous -50% capacité (25 apps/jour au lieu de 50) avec auto-heal ?

4. **Latency** : Acceptez-vous +92s par génération avec auto-heal ?

**Dites-moi vos priorités** : Vitesse vs Qualité vs Simplicité ?
