# 🛠️ Tool Calling / Function Calling - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation depuis API Anthropic + Patterns standards
**État** : 75% documenté (extrapolé, haute confiance)

---

## 📋 Vue d'Ensemble

**Tool calling** permet à Claude d'**appeler des fonctions externes** définies par le développeur.

**Use cases** :
- Récupérer données d'une API
- Exécuter calculs complexes
- Interroger une base de données
- Interagir avec des services externes

---

## 🔧 Structure Requête avec Tools

### Format Complet

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "tools": [
    {
      "name": "get_weather",
      "description": "Get the current weather in a given location",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA"
          },
          "unit": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The unit of temperature"
          }
        },
        "required": ["location"]
      }
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "What's the weather like in San Francisco?"
    }
  ]
}
```

### Champs Tools

| Champ | Type | Description |
|-------|------|-------------|
| `name` | string | Nom unique de la fonction (snake_case) |
| `description` | string | Description claire pour Claude |
| `input_schema` | object | JSON Schema des paramètres |

---

## 📊 Flow Complet Tool Calling

### Étape 1 : Claude Demande Outil

**Réponse Claude** (SSE) :
```json
{
  "type": "message",
  "id": "msg_01...",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01...",
      "name": "get_weather",
      "input": {
        "location": "San Francisco, CA",
        "unit": "celsius"
      }
    }
  ],
  "stop_reason": "tool_use"
}
```

### Étape 2 : App Exécute Fonction

```javascript
// Votre code
const weatherData = await fetchWeather("San Francisco, CA", "celsius");
// → { temp: 18, condition: "Sunny" }
```

### Étape 3 : Envoyer Résultat à Claude

**Nouvelle requête** :
```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "tools": [...], // Même définition tools
  "messages": [
    {
      "role": "user",
      "content": "What's the weather like in San Francisco?"
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "tool_use",
          "id": "toolu_01...",
          "name": "get_weather",
          "input": {
            "location": "San Francisco, CA",
            "unit": "celsius"
          }
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01...",
          "content": "{\"temp\": 18, \"condition\": \"Sunny\"}"
        }
      ]
    }
  ]
}
```

### Étape 4 : Claude Répond avec Résultat

```json
{
  "type": "message",
  "content": [
    {
      "type": "text",
      "text": "The weather in San Francisco is currently sunny with a temperature of 18°C."
    }
  ],
  "stop_reason": "end_turn"
}
```

---

## 🎯 Input Schema (JSON Schema)

### Types Supportés

```json
{
  "type": "object",
  "properties": {
    "string_param": {
      "type": "string",
      "description": "A text parameter"
    },
    "number_param": {
      "type": "number",
      "description": "A numeric parameter"
    },
    "integer_param": {
      "type": "integer",
      "description": "An integer parameter"
    },
    "boolean_param": {
      "type": "boolean",
      "description": "A true/false parameter"
    },
    "array_param": {
      "type": "array",
      "items": {"type": "string"},
      "description": "An array of strings"
    },
    "enum_param": {
      "type": "string",
      "enum": ["option1", "option2", "option3"],
      "description": "One of predefined options"
    },
    "object_param": {
      "type": "object",
      "properties": {
        "nested_field": {"type": "string"}
      },
      "description": "A nested object"
    }
  },
  "required": ["string_param", "number_param"]
}
```

### Validation

**Claude valide automatiquement** :
- Types conformes au schema
- Champs required présents
- Enum dans valeurs autorisées

**Si validation échoue** : Claude re-génère la requête tool

---

## 🔄 Multi-Tools

### Définir Plusieurs Tools

```json
{
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather for a location",
      "input_schema": {...}
    },
    {
      "name": "search_web",
      "description": "Search the web for information",
      "input_schema": {...}
    },
    {
      "name": "calculate",
      "description": "Perform mathematical calculations",
      "input_schema": {...}
    }
  ]
}
```

### Claude Choisit le Bon Tool

**Prompt** : "What's the weather in Paris and the population of France?"

**Réponse Claude** :
```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01...",
      "name": "get_weather",
      "input": {"location": "Paris, France"}
    },
    {
      "type": "tool_use",
      "id": "toolu_02...",
      "name": "search_web",
      "input": {"query": "population of France"}
    }
  ],
  "stop_reason": "tool_use"
}
```

**Claude peut appeler plusieurs tools en parallèle !**

---

## 🚨 Gestion Erreurs Tool

### Tool Échoue

**Si votre fonction échoue** :
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01...",
      "content": "Error: API rate limit exceeded",
      "is_error": true
    }
  ]
}
```

**Claude gère l'erreur** :
```json
{
  "type": "text",
  "text": "I apologize, but I encountered an error while trying to fetch the weather data. The API rate limit has been exceeded. Please try again in a few moments."
}
```

### Tool Non Trouvé

**Si tool name invalide dans input_schema** :
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "tools.0.name: Tool name must match pattern ^[a-zA-Z0-9_-]{1,64}$"
  }
}
```

---

## 📈 Limites et Contraintes

| Aspect | Limite |
|--------|--------|
| **Max tools par requête** | 64 tools |
| **Max tool calls parallèles** | ~10 (estimé) |
| **Max tool name length** | 64 caractères |
| **Max description length** | 1024 caractères |
| **Max input JSON size** | ~10 KB (estimé) |
| **Max tool result size** | 100 KB (estimé) |

---

## 🎨 Best Practices

### 1. Descriptions Claires

✅ **Bon** :
```json
{
  "name": "get_weather",
  "description": "Get the current weather for a specific location. Returns temperature, conditions, humidity, and wind speed."
}
```

❌ **Mauvais** :
```json
{
  "name": "get_weather",
  "description": "weather"
}
```

### 2. Noms Explicites

✅ **Bon** :
- `get_user_profile`
- `search_products`
- `calculate_shipping_cost`

❌ **Mauvais** :
- `func1`
- `api_call`
- `do_thing`

### 3. Validation Stricte

```json
{
  "properties": {
    "email": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "description": "Valid email address"
    },
    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 150,
      "description": "Age in years"
    }
  }
}
```

### 4. Error Handling Robuste

```javascript
async function executeToolCall(toolUse) {
  try {
    const result = await yourFunction(toolUse.input);
    return {
      type: "tool_result",
      tool_use_id: toolUse.id,
      content: JSON.stringify(result)
    };
  } catch (error) {
    return {
      type: "tool_result",
      tool_use_id: toolUse.id,
      content: `Error: ${error.message}`,
      is_error: true
    };
  }
}
```

---

## 🔍 Différences OAuth vs API Key

### Identique

✅ **Même comportement** :
- Structure tools identique
- Input schema JSON Schema standard
- Flow tool_use → tool_result identique
- Limites identiques

### Pas de Différence

**Tool calling fonctionne exactement pareil** avec OAuth et API Key.

---

## 💡 Exemples Réels

### Exemple 1 : API Database

```json
{
  "tools": [{
    "name": "query_database",
    "description": "Query the user database with SQL-like syntax",
    "input_schema": {
      "type": "object",
      "properties": {
        "table": {
          "type": "string",
          "enum": ["users", "orders", "products"]
        },
        "filters": {
          "type": "object",
          "description": "Key-value filters"
        },
        "limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 10
        }
      },
      "required": ["table"]
    }
  }]
}
```

### Exemple 2 : Calculs Complexes

```json
{
  "tools": [{
    "name": "calculate_mortgage",
    "description": "Calculate monthly mortgage payment",
    "input_schema": {
      "type": "object",
      "properties": {
        "principal": {
          "type": "number",
          "description": "Loan amount in dollars"
        },
        "interest_rate": {
          "type": "number",
          "description": "Annual interest rate as percentage (e.g., 5.5)"
        },
        "years": {
          "type": "integer",
          "description": "Loan term in years"
        }
      },
      "required": ["principal", "interest_rate", "years"]
    }
  }]
}
```

### Exemple 3 : API Externe

```json
{
  "tools": [{
    "name": "search_wikipedia",
    "description": "Search Wikipedia and return article summary",
    "input_schema": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query"
        },
        "language": {
          "type": "string",
          "enum": ["en", "fr", "es", "de"],
          "default": "en",
          "description": "Wikipedia language"
        }
      },
      "required": ["query"]
    }
  }]
}
```

---

## 🎯 Prompt Engineering pour Tools

### Encourager Usage Tool

✅ **Bon prompt** :
```
You have access to a weather API. If the user asks about weather,
use the get_weather tool to fetch real-time data.
```

### Guider Choix Tool

✅ **Bon prompt** :
```
Use search_web for general knowledge questions.
Use query_database for information about our users/orders.
Use calculate for mathematical problems.
```

---

## 🧪 Testing Tools

### Test Input Schema

```javascript
// Valider schema avant envoi
const Ajv = require('ajv');
const ajv = new Ajv();

const validate = ajv.compile(tool.input_schema);
const valid = validate(toolInput);

if (!valid) {
  console.error("Invalid tool input:", validate.errors);
}
```

### Test Flow Complet

```javascript
// 1. Envoyer requête avec tools
const response1 = await anthropic.messages.create({
  model: "claude-sonnet-4-5-20250929",
  max_tokens: 1024,
  tools: [weatherTool],
  messages: [{role: "user", content: "Weather in Paris?"}]
});

// 2. Extraire tool_use
const toolUse = response1.content.find(c => c.type === 'tool_use');

// 3. Exécuter fonction
const result = await getWeather(toolUse.input.location);

// 4. Renvoyer résultat
const response2 = await anthropic.messages.create({
  model: "claude-sonnet-4-5-20250929",
  max_tokens: 1024,
  tools: [weatherTool],
  messages: [
    {role: "user", content: "Weather in Paris?"},
    {role: "assistant", content: response1.content},
    {role: "user", content: [{
      type: "tool_result",
      tool_use_id: toolUse.id,
      content: JSON.stringify(result)
    }]}
  ]
});

console.log(response2.content[0].text);
```

---

## 🔮 Features Avancées

### Streaming avec Tools

**Tools supportent streaming** :
```javascript
const stream = await anthropic.messages.stream({
  model: "claude-sonnet-4-5-20250929",
  max_tokens: 1024,
  tools: [weatherTool],
  messages: [{role: "user", content: "Weather in Paris?"}]
});

stream.on('content_block_start', (event) => {
  if (event.content_block.type === 'tool_use') {
    console.log("Tool:", event.content_block.name);
  }
});
```

### Tool Choice (Contrôle)

**Forcer/interdire usage tools** (extrapolé, à confirmer OAuth) :
```json
{
  "tools": [...],
  "tool_choice": {
    "type": "tool",
    "name": "get_weather"
  }
}
```

Options :
- `{"type": "auto"}` : Claude décide (défaut)
- `{"type": "tool", "name": "X"}` : Force tool X
- `{"type": "any"}` : Force n'importe quel tool
- `{"type": "none"}` : Interdit tools

---

## 📚 Ressources

### Documentation Officielle
- Messages API : https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- JSON Schema : https://json-schema.org/

### Exemples
- GitHub Anthropic : https://github.com/anthropics/anthropic-sdk-python/tree/main/examples

---

## 🎯 Checklist Implémentation

- [ ] Définir tools avec descriptions claires
- [ ] Valider input_schema (JSON Schema)
- [ ] Implémenter fonctions backend
- [ ] Gérer errors (`is_error: true`)
- [ ] Tester avec edge cases
- [ ] Logger tool calls pour debug
- [ ] Implémenter timeout fonctions (5-10s max)
- [ ] Valider tool results avant envoi
- [ ] Documenter tools pour utilisateurs
- [ ] Monitoring usage tools (coût tokens)

---

## 🎓 Key Takeaways

1. **Tools = Functions externes** appelables par Claude
2. **JSON Schema** pour définir input structure
3. **Flow 4 étapes** : request → tool_use → execute → tool_result → response
4. **Multi-tools** supporté (parallèle)
5. **Error handling** via `is_error: true`
6. **Identique OAuth vs API Key**
7. **Streaming compatible**
8. **Descriptions critiques** pour qualité choix Claude

---

**Dernière mise à jour** : 2025-11-05 16:00
**Confiance** : 75% (extrapolé depuis API Anthropic, patterns standards)
**Prochaine étape** : Documenter Images/Multimodal
