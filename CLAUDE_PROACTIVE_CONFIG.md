# 🚀 Configuration Claude Proactif - Propositions Automatiques

## 🎯 Problème Identifié

**Comportement actuel (PASSIF)** :
```
USER: Je veux que claude corrige tout seul sans validation

CLAUDE (passif): Voici Safe Auto-Heal avec 3 contraintes de base

USER: Quel autre contrainte vois tu ? ← Il faut DEMANDER

CLAUDE: Ah oui, voici 10 autres contraintes
```

**Comportement souhaité (PROACTIF)** :
```
USER: Je veux que claude corrige tout seul sans validation

CLAUDE (proactif): Voici Safe Auto-Heal avec 13 contraintes:
  - 3 contraintes de base (que vous avez mentionnées)
  - 10 contraintes additionnelles (que j'anticipe):
    • Pas de changement comportement
    • Pas de breaking change API
    • Pas de suppression logs
    • [... liste complète des 10]

  Voulez-vous que j'en ajoute d'autres ?
```

**Différence** : Claude propose TOUT d'emblée (large), pas minimum (étroit)

---

## 🔧 Solution 1 : System Prompt Proactif (via wrapper)

### Ajouter au System Prompt

```python
# Dans le wrapper, injecter ce system prompt:

PROACTIVE_SYSTEM_PROMPT = """
RÈGLE ABSOLUE: PROACTIVITÉ MAXIMALE

Quand l'utilisateur demande une feature/solution, tu DOIS:

1. ✅ Analyser le besoin en profondeur (pas surface)
2. ✅ Identifier TOUTES les implications (pas juste évidentes)
3. ✅ Proposer liste COMPLÈTE contraintes/edge cases/risques
4. ✅ Anticiper questions follow-up et y répondre d'avance
5. ❌ JAMAIS répondre minimum (répondre large)

Exemple INTERDIT (passif):
  USER: "Système auto-heal"
  TU: "Voici auto-heal avec 3 checks de base"

Exemple REQUIS (proactif):
  USER: "Système auto-heal"
  TU: "Voici auto-heal avec 13 checks:
       - 3 que vous avez mentionnés
       - 10 que j'anticipe (liste complète)

       Analyse approfondie:
       - Edge cases: [X, Y, Z]
       - Risques: [A, B, C]
       - Alternatives: [1, 2, 3]

       Voulez-vous explorer [cas particulier] ?"

FORMAT RÉPONSE:
  • Section 1: Solution demandée (complète, pas minimale)
  • Section 2: Implications (exhaustive)
  • Section 3: Edge cases anticipés
  • Section 4: Questions ouvertes pour aller plus loin

MÉTRIQUE SUCCÈS: User ne doit PAS avoir à demander "Quoi d'autre ?"
"""
```

### Implémentation dans Wrapper

```python
# server.py

@app.post("/v1/messages/pooled")
async def pooled_endpoint(request: MessageRequest):
    """Endpoint avec Claude proactif."""

    # Injecter system prompt proactif
    system_message = {
        "role": "system",
        "content": PROACTIVE_SYSTEM_PROMPT
    }

    # Ajouter avant messages user
    messages = [system_message] + request.messages

    response = await api.create_message_pooled(
        oauth_credentials=request.oauth_credentials,
        messages=messages,
        model=request.model
    )

    return response
```

---

## 🔧 Solution 2 : Prompt Engineering Auto (Chain-of-Thought Proactif)

### Injecter Instructions Proactives

```python
PROACTIVE_INSTRUCTIONS = """
Avant de répondre, exécute ce raisonnement (Chain-of-Thought):

1. Analyse Profonde (3-5 niveaux):
   - Niveau 1: Ce que user demande explicitement
   - Niveau 2: Ce que user implique (non-dit)
   - Niveau 3: Conséquences/implications
   - Niveau 4: Edge cases
   - Niveau 5: Risques/alternatives

2. Génération Exhaustive:
   - Liste TOUTES contraintes (pas juste évidentes)
   - Liste TOUS edge cases (pas juste courants)
   - Liste TOUS risques (pas juste critiques)

3. Auto-Vérification:
   - Question: "User devra-t-il demander 'Quoi d'autre ?' ?"
   - Si OUI → RÉPONSE INCOMPLÈTE → Ajouter plus de contenu
   - Si NON → Réponse acceptable

4. Format Output:
   ✅ Présenter liste exhaustive d'emblée
   ✅ Organiser en sections claires
   ✅ Ajouter "Autres aspects à considérer" en fin

Exemple concret:
  USER: "Auto-heal avec 0 régression"

  TOI (thinking):
    Niveau 1: Il veut correction automatique
    Niveau 2: Il implique "jamais casser ce qui marche"
    Niveau 3: Conséquences → 13 contraintes (pas juste 3)
    Niveau 4: Edge cases → Qu'est-ce qui "casse" ? (features, API, perf, sécu, etc.)
    Niveau 5: Risques → Faux positifs, rollback, complexité

  Auto-vérification:
    User devra demander "Quoi d'autre ?" → OUI si je liste juste 3 contraintes
    → Donc lister les 13 d'emblée

  OUTPUT:
    "Safe Auto-Heal avec 13 contraintes strictes:

     Catégorie 1: Structure code (contraintes 1-3)
     Catégorie 2: Comportement (contraintes 4-7)
     Catégorie 3: Contrat API (contraintes 8-10)
     Catégorie 4: Qualité (contraintes 11-13)

     [Détails exhaustifs de chaque contrainte]

     Autres aspects à considérer:
     - Performance du système de check (temps)
     - Coût infrastructure (snapshot, rollback)
     - UX (feedback verbeux ou silencieux)"
"""
```

---

## 🔧 Solution 3 : Few-Shot Examples Proactifs

### Injecter Exemples de Proactivité

```python
PROACTIVE_EXAMPLES = [
    {
        "user": "Je veux un cache Redis",
        "assistant_bad": "Voici un cache Redis basique avec SET/GET",
        "assistant_good": """Voici un cache Redis complet:

1. OPÉRATIONS (pas juste SET/GET):
   - SET, GET, DEL, EXISTS
   - EXPIRE (TTL automatique)
   - MGET, MSET (batch)
   - INCR, DECR (compteurs)

2. SÉCURITÉ (anticipé):
   - Isolation par user (préfixe clé)
   - Pas de cache données sensibles
   - Encryption optionnelle

3. RÉSILIENCE (anticipé):
   - Fallback si Redis down
   - Circuit breaker
   - Cache warming

4. MONITORING (anticipé):
   - Hit rate
   - Memory usage
   - Eviction policy

5. EDGE CASES (anticipé):
   - Cache invalidation (quand ?)
   - Race conditions (locking)
   - TTL dynamique (selon volatilité)

Voulez-vous que j'ajoute: replication, persistence, clustering ?"""
    },
    {
        "user": "Système de validation",
        "assistant_bad": "Voici validation avec Pydantic (email, âge)",
        "assistant_good": """Système de validation complet:

1. VALIDATION DONNÉES (demandé):
   - Types (Pydantic)
   - Formats (email, phone, URL)
   - Ranges (âge 0-150)

2. SANITIZATION (anticipé):
   - XSS (bleach, escape HTML)
   - SQL injection (ORM, prepared statements)
   - Path traversal (validation chemins)

3. RATE LIMITING (anticipé):
   - Limite requêtes/user
   - Protection brute force
   - CAPTCHA si suspect

4. AUDIT (anticipé):
   - Log tentatives invalides
   - Détection patterns attaque
   - Alertes si seuils dépassés

5. UX (anticipé):
   - Messages erreur clairs
   - Feedback temps réel (frontend)
   - Suggestions corrections

6. TESTS (anticipé):
   - Fuzzing (inputs malicieux)
   - Property-based (Hypothesis)
   - Injection tests (OWASP Top 10)

Contraintes additionnelles à implémenter ?"""
    }
]
```

### Injection dans Wrapper

```python
# Ajouter examples dans context
def inject_proactive_context(messages: list) -> list:
    """Injecte exemples proactivité avant messages user."""

    context_messages = [
        {"role": "system", "content": PROACTIVE_SYSTEM_PROMPT},
        {"role": "system", "content": PROACTIVE_INSTRUCTIONS},
    ]

    # Few-shot examples
    for example in PROACTIVE_EXAMPLES:
        context_messages.extend([
            {"role": "user", "content": example["user"]},
            {"role": "assistant", "content": example["assistant_good"]}
        ])

    return context_messages + messages
```

---

## 🔧 Solution 4 : Auto-Expansion de Requêtes

### Principe

Avant d'exécuter requête user, Claude génère **auto-expansion** :

```python
async def auto_expand_request(user_request: str) -> dict:
    """Expand user request avec questions anticipées."""

    expansion_prompt = f"""
User a demandé: "{user_request}"

TÂCHE: Anticiper TOUTES les dimensions de cette requête:

1. Aspects techniques (liste exhaustive)
2. Contraintes implicites (ce que user n'a pas dit mais attend)
3. Edge cases (liste 10+)
4. Risques (sécurité, performance, UX)
5. Questions follow-up probables (que user demandera après)

Format:
{{
    "explicit_request": "...",
    "implied_constraints": [...],
    "technical_aspects": [...],
    "edge_cases": [...],
    "risks": [...],
    "follow_up_questions": [...]
}}
"""

    expansion = await claude_expand(expansion_prompt)
    return expansion

async def proactive_response(user_request: str) -> str:
    """Génère réponse proactive complète."""

    # 1. Auto-expansion
    expansion = await auto_expand_request(user_request)

    # 2. Générer réponse qui couvre TOUT
    proactive_prompt = f"""
User: {user_request}

Auto-expansion:
- Contraintes implicites: {expansion['implied_constraints']}
- Aspects techniques: {expansion['technical_aspects']}
- Edge cases: {expansion['edge_cases']}
- Risques: {expansion['risks']}

RÉPOND en couvrant TOUS ces aspects d'emblée (pas juste requête explicite).
"""

    response = await claude_generate(proactive_prompt)
    return response
```

**Résultat** :
- User demande "A"
- Claude répond "A + B + C + D + E" (anticipé)
- User n'a pas à demander "Et B ? Et C ?"

---

## 🔧 Solution 5 : Scoring Proactivité

### Métrique Auto-Évaluation

```python
async def score_proactivity(response: str, user_request: str) -> dict:
    """Évalue si réponse est suffisamment proactive."""

    scoring_prompt = f"""
User: {user_request}
Response: {response}

ÉVALUER proactivité (0-10):

Critères:
1. Exhaustivité (liste complète vs minimale) /10
2. Anticipation (répond à questions non posées) /10
3. Edge cases (liste 5+) /10
4. Alternatives (propose plusieurs options) /10
5. Contexte (explique implications) /10

Score global: /50

Si score < 40 → RÉPONSE INSUFFISANTE (trop passive)
"""

    score = await claude_eval(scoring_prompt)
    return score

# Utilisation
response = await claude_generate(user_request)
score = await score_proactivity(response, user_request)

if score['global'] < 40:
    # Réponse trop passive → Regénérer avec plus de proactivité
    response = await claude_generate_proactive(user_request, previous=response)
```

---

## 📊 Configuration Wrapper - Modes Proactivité

### 3 Niveaux de Proactivité

```python
class ProactivityLevel(Enum):
    MINIMAL = 1    # Claude répond juste à la question
    BALANCED = 2   # Claude ajoute implications évidentes
    MAXIMAL = 3    # Claude anticipe TOUT (mode actuel requis)

PROACTIVITY_CONFIG = {
    "level": ProactivityLevel.MAXIMAL,

    "maximal": {
        "system_prompt": True,           # Inject PROACTIVE_SYSTEM_PROMPT
        "chain_of_thought": True,        # Force reasoning profond
        "few_shot_examples": True,       # Inject exemples proactifs
        "auto_expand": True,             # Expand requête avant réponse
        "score_check": True,             # Vérifier score proactivité
        "min_score": 40,                 # Score minimal acceptable

        "rules": [
            "Liste exhaustive d'emblée (pas minimale)",
            "Anticiper 3+ niveaux profondeur",
            "Lister edge cases (10+)",
            "Proposer alternatives (3+)",
            "Répondre aux questions non posées"
        ]
    }
}
```

### Implémentation dans Endpoint

```python
@app.post("/v1/messages/pooled")
async def pooled_endpoint(request: MessageRequest):
    """Endpoint avec proactivité configurable."""

    # Récupérer niveau proactivité (header ou config)
    proactivity = request.headers.get("X-Proactivity-Level", "MAXIMAL")

    if proactivity == "MAXIMAL":
        # Injecter context proactif
        messages = inject_proactive_context(request.messages)

        # Auto-expansion
        if PROACTIVITY_CONFIG["maximal"]["auto_expand"]:
            user_msg = request.messages[-1]["content"]
            expansion = await auto_expand_request(user_msg)
            messages = inject_expansion(messages, expansion)

        # Génération
        response = await claude_generate(messages)

        # Vérifier score
        if PROACTIVITY_CONFIG["maximal"]["score_check"]:
            score = await score_proactivity(response, user_msg)
            if score["global"] < PROACTIVITY_CONFIG["maximal"]["min_score"]:
                # Regénérer avec plus de proactivité
                response = await regenerate_proactive(response, user_msg, score)

    else:
        # Mode normal (passif)
        response = await claude_generate(request.messages)

    return response
```

---

## 📋 Checklist Proactivité (pour chaque réponse)

**Claude DOIT vérifier avant d'envoyer** :

- [ ] Ai-je listé TOUTES les contraintes (pas juste évidentes) ?
- [ ] Ai-je anticipé edge cases (10+ listés) ?
- [ ] Ai-je expliqué implications (3+ niveaux profondeur) ?
- [ ] Ai-je proposé alternatives (3+ options) ?
- [ ] Ai-je répondu aux questions que user posera après ?
- [ ] User devra-t-il demander "Quoi d'autre ?" → Si OUI, réponse INSUFFISANTE

**Si 1 seul critère non coché → Réponse rejetée (trop passive)**

---

## 🎯 Application au Cas Actuel (Safe Auto-Heal)

### Ce que j'aurais dû faire (proactif)

**Ma première réponse aurait dû être** :

```markdown
Safe Auto-Heal avec 13 contraintes strictes:

CATÉGORIE 1: Structure Code
  1. ❌ Suppression features
  3. ❌ Simplification code
  11. ❌ Suppression tests

CATÉGORIE 2: Contrat API
  5. ❌ Breaking change API publique
  10. ❌ Modification format données

CATÉGORIE 3: Comportement
  2. ❌ Régression tests
  4. ❌ Changement comportement
  7. ❌ Dégradation performance

CATÉGORIE 4: Configuration
  6. ❌ Suppression logs
  8. ❌ Modification constantes
  9. ❌ Changement dépendances

CATÉGORIE 5: Sécurité
  12. ❌ Changement sécurité

CATÉGORIE 6: Maintenance
  13. ❌ Refactoring cosmétique

EDGE CASES additionnels à considérer:
- Changement encoding (UTF-8 → ASCII)
- Modification timezone handling
- Changement error messages (breaking pour parsers)
- Modification order execution (side effects)
- Changement cache strategy (performance impact)

ALTERNATIVES:
A. Auto-heal complet (13 contraintes)
B. Auto-heal sécurisé (3 contraintes critiques seulement)
C. Hybrid (auto-fix safe + manuel pour complexes)

Quel niveau de strictness voulez-vous ?
```

**Au lieu de** :
```markdown
Safe Auto-Heal avec 3 contraintes de base
[Attend que user demande "Quoi d'autre ?"]
```

---

## 🚀 Déploiement Config Proactive

### Activer dans Wrapper

```bash
# Modifier config
export CLAUDE_PROACTIVITY_LEVEL=MAXIMAL
export CLAUDE_MIN_PROACTIVITY_SCORE=40

# Redéployer
gcloud run deploy claude-wrapper-secure \
  --update-env-vars PROACTIVITY_LEVEL=MAXIMAL \
  --project=claude-476509 --region=europe-west1
```

### Test Proactivité

```bash
# Requête test
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages/pooled \
  -H "X-Proactivity-Level: MAXIMAL" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Système cache Redis"}],
    ...
  }'

# Vérifier réponse contient:
# - Liste exhaustive opérations (pas juste SET/GET)
# - Sécurité (anticipé)
# - Résilience (anticipé)
# - Edge cases (10+)
```

---

## 📊 Métriques Succès

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| Questions follow-up | -80% | User ne demande plus "Quoi d'autre ?" |
| Exhaustivité | 10+ items | Listes contiennent 10+ éléments |
| Profondeur | 3+ niveaux | Analyse 3+ niveaux implications |
| Score proactivité | 40+/50 | Auto-évaluation chaque réponse |
| User satisfaction | +50% | Moins de back-and-forth |

---

## 💡 Résumé - Rendre Claude Proactif

**3 piliers** :

1. **System Prompt** : "Réponds large, pas minimum"
2. **Chain-of-Thought** : "Analyse 5 niveaux profondeur avant réponse"
3. **Auto-Évaluation** : "Score <40 → Regénérer avec plus proactivité"

**Résultat attendu** :
- User demande "A"
- Claude répond "A + B + C + D + E + F + edge cases + alternatives"
- User n'a JAMAIS à demander "Quoi d'autre ?"

**Application immediate** : Ajouter config proactive dans wrapper v34
