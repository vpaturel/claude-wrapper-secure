# 🖼️ Images & Multimodal - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation depuis API Anthropic + Patterns standards
**État** : 75% documenté (extrapolé, haute confiance)

---

## 📋 Vue d'Ensemble

Claude supporte l'**analyse d'images** (Vision) via contenu multimodal dans les messages.

**Capacités** :
- Décrire images
- Extraire texte (OCR)
- Analyser graphiques/diagrammes
- Détecter objets/scènes
- Compter éléments
- Lire documents scannés

---

## 🖼️ Format Image Supporté

### Formats

| Format | Supporté | Extension |
|--------|----------|-----------|
| **PNG** | ✅ | .png |
| **JPEG** | ✅ | .jpg, .jpeg |
| **WebP** | ✅ | .webp |
| **GIF** | ✅ | .gif (frame 1 seulement) |

### Limites

| Aspect | Limite |
|--------|--------|
| **Taille max** | 5 MB par image |
| **Dimensions max** | 8000 x 8000 pixels |
| **Images par message** | ~20 images (estimé) |
| **Total tokens image** | Compte dans context (200K) |

---

## 📨 Structure Requête avec Image

### Format Base64

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What's in this image?"
        },
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDA..."
          }
        }
      ]
    }
  ]
}
```

### Format URL (API Key uniquement)

**OAuth ne supporte PAS les URLs directes** (nécessite base64) :
```json
{
  "type": "image",
  "source": {
    "type": "url",
    "url": "https://example.com/image.jpg"
  }
}
```
❌ **Non supporté OAuth** (retourne erreur)

---

## 🔧 Implémentation

### Encoder Image en Base64

#### Python
```python
import base64

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Usage
image_data = encode_image("photo.jpg")
```

#### JavaScript
```javascript
const fs = require('fs');

function encodeImage(imagePath) {
  const imageBuffer = fs.readFileSync(imagePath);
  return imageBuffer.toString('base64');
}

// Usage
const imageData = encodeImage('photo.jpg');
```

#### Bash
```bash
base64 -w 0 photo.jpg
```

### Requête Complète

```python
import anthropic
import base64

client = anthropic.Anthropic()

# Encoder image
with open("photo.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Envoyer requête
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Describe this image in detail"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            }
        ]
    }]
)

print(response.content[0].text)
```

---

## 🎨 Multi-Images

### Plusieurs Images dans un Message

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Compare these two images:"},
      {
        "type": "image",
        "source": {
          "type": "base64",
          "media_type": "image/jpeg",
          "data": "[IMAGE_1_BASE64]"
        }
      },
      {
        "type": "image",
        "source": {
          "type": "base64",
          "media_type": "image/png",
          "data": "[IMAGE_2_BASE64]"
        }
      },
      {"type": "text", "text": "What are the differences?"}
    ]
  }]
}
```

### Ordre Contenu

**Flexible** : Text et images peuvent être mélangés dans n'importe quel ordre.

**Exemples valides** :
- Text → Image → Text
- Image → Text → Image
- Multiple images → Text
- Text → Multiple images

---

## 💰 Coût Images (Tokens)

### Calcul Tokens

**Images comptent comme tokens** basé sur dimensions :

| Taille | Tokens approximatifs |
|--------|---------------------|
| Petite (< 500x500) | ~500 tokens |
| Moyenne (< 1000x1000) | ~1500 tokens |
| Grande (< 2000x2000) | ~3000 tokens |
| Très grande (< 4000x4000) | ~6000 tokens |

**Formule estimée** :
```
tokens ≈ (width * height) / 750
```

### Optimisation

**Pour réduire coût** :
1. Redimensionner images avant envoi
2. Compresser qualité (JPEG 80-90%)
3. Recadrer zones pertinentes
4. Utiliser WebP (meilleure compression)

```python
from PIL import Image

def optimize_image(input_path, output_path, max_size=1500):
    img = Image.open(input_path)

    # Redimensionner si trop grande
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    # Sauver avec compression
    img.save(output_path, optimize=True, quality=85)
```

---

## 🎯 Use Cases

### 1. OCR / Extraction Texte

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Extract all text from this document"},
      {"type": "image", "source": {...}}
    ]
  }]
}
```

**Claude extrait** : Texte, tableaux, formules mathématiques

### 2. Analyse Graphiques

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Analyze this chart and provide insights"},
      {"type": "image", "source": {...}}
    ]
  }]
}
```

**Claude analyse** : Tendances, données, conclusions

### 3. Description Produits

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Write a product description for this item"},
      {"type": "image", "source": {...}}
    ]
  }]
}
```

### 4. Vérification Documents

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Check if this ID document is valid"},
      {"type": "image", "source": {...}}
    ]
  }]
}
```

⚠️ **Attention** : Ne pas envoyer données sensibles (PII, documents ID réels)

### 5. Comptage Objets

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "How many people are in this photo?"},
      {"type": "image", "source": {...}}
    ]
  }]
}
```

---

## 🚨 Erreurs Images

### Image Trop Grande

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Image size exceeds maximum allowed size of 5MB"
  }
}
```

### Format Non Supporté

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Unsupported image format. Supported formats: PNG, JPEG, WebP, GIF"
  }
}
```

### Base64 Invalide

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Invalid base64 data in image source"
  }
}
```

### Media Type Incorrect

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "media_type must be one of: image/jpeg, image/png, image/gif, image/webp"
  }
}
```

---

## 📊 Différences OAuth vs API Key

| Aspect | OAuth | API Key |
|--------|-------|---------|
| **Base64** | ✅ Supporté | ✅ Supporté |
| **URL directe** | ❌ Non supporté | ✅ Supporté |
| **Taille max** | 5 MB | 5 MB |
| **Formats** | PNG, JPEG, WebP, GIF | PNG, JPEG, WebP, GIF |
| **Coût** | Inclus forfait | Pay-per-token |

**Différence clé** : OAuth **nécessite base64**, pas d'URL directe

---

## 🎨 Best Practices

### 1. Optimiser Avant Envoi

```python
def prepare_image(path):
    img = Image.open(path)

    # Convertir en RGB si nécessaire
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Redimensionner si > 2000px
    max_size = 2000
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))

    # Sauver en JPEG optimisé
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()
```

### 2. Prompts Spécifiques

✅ **Bon** :
```
"Identify all products in this image and list their names"
```

❌ **Mauvais** :
```
"What do you see?"
```

### 3. Multi-Step pour Complexité

**Étape 1** : Analyse générale
```
"Describe what you see in this medical image"
```

**Étape 2** : Questions spécifiques
```
"Based on your analysis, are there any abnormalities?"
```

### 4. Validation Côté Client

```python
def validate_image(path):
    # Vérifier taille fichier
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 5:
        raise ValueError(f"Image too large: {size_mb:.1f}MB > 5MB")

    # Vérifier format
    img = Image.open(path)
    if img.format not in ['PNG', 'JPEG', 'WEBP', 'GIF']:
        raise ValueError(f"Unsupported format: {img.format}")

    # Vérifier dimensions
    if max(img.size) > 8000:
        raise ValueError(f"Image too large: {max(img.size)}px > 8000px")

    return True
```

---

## 🔍 Capacités Vision

### Ce Que Claude Peut Faire ✅

- **Décrire** objets, scènes, personnes
- **Lire** texte (OCR multilingue)
- **Compter** objets visibles
- **Identifier** marques, logos
- **Analyser** graphiques, tableaux
- **Extraire** données structurées
- **Détecter** couleurs, formes
- **Comparer** images multiples
- **Estimer** tailles relatives

### Limitations ❌

- **Pas d'identification faciale** (privacy)
- **Pas de localisation GPS** depuis EXIF
- **Pas de dates** depuis métadonnées
- **Pas de vidéos** (uniquement images statiques)
- **GIF** : Seule la première frame analysée
- **Précision limitée** pour texte très petit
- **Pas de génération** d'images (Claude ne crée pas d'images)

---

## 🧪 Exemples Avancés

### Analyse Document avec Structuration

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": """Extract information from this invoice and return as JSON:
                {
                  "invoice_number": "...",
                  "date": "...",
                  "total": "...",
                  "items": [{"name": "...", "quantity": ..., "price": ...}]
                }"""
            },
            {"type": "image", "source": {"type": "base64", ...}}
        ]
    }]
)
```

### Comparaison Multi-Images

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1500,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Compare these product photos:"},
            {"type": "image", "source": {"type": "base64", "data": image1_b64}},
            {"type": "text", "text": "VS"},
            {"type": "image", "source": {"type": "base64", "data": image2_b64}},
            {"type": "text", "text": "List differences in quality, packaging, and condition"}
        ]
    }]
)
```

---

## 🎯 Modèles Supportant Vision

| Modèle | Vision | Performance |
|--------|--------|-------------|
| **Opus 4** | ✅ | Excellente |
| **Sonnet 4.5** | ✅ | Excellente |
| **Haiku 3.5** | ✅ | Bonne |
| **Sonnet 3.5 legacy** | ✅ | Bonne |

**Tous les modèles Claude 3+ supportent vision.**

---

## 📚 Ressources

### Documentation Officielle
- Vision : https://docs.anthropic.com/en/docs/build-with-claude/vision
- Prompt Library : https://docs.anthropic.com/en/prompt-library

### Outils
- PIL/Pillow (Python) : Image processing
- Sharp (Node.js) : Image processing
- ImageMagick : CLI image processing

---

## 🎓 Key Takeaways

1. **Base64 obligatoire** pour OAuth (pas d'URL)
2. **5 MB max** par image
3. **Formats** : PNG, JPEG, WebP, GIF
4. **Images = tokens** (500-6000 selon taille)
5. **Optimiser** avant envoi (resize, compress)
6. **Multi-images** supporté (comparaison)
7. **OCR excellent** (texte, tableaux)
8. **Pas d'identification** faciale (privacy)

---

## ✅ Checklist Implémentation

- [ ] Valider format image (PNG, JPEG, WebP, GIF)
- [ ] Vérifier taille < 5 MB
- [ ] Optimiser dimensions (< 2000px recommandé)
- [ ] Encoder en base64
- [ ] Spécifier media_type correct
- [ ] Prompts clairs et spécifiques
- [ ] Gérer erreurs (taille, format)
- [ ] Logger tokens consommés
- [ ] Tester avec différents types d'images
- [ ] Documenter limitations (pas de faces, etc.)

---

**Dernière mise à jour** : 2025-11-05 16:10
**Confiance** : 75% (extrapolé depuis API Anthropic, patterns standards)
**Prochaine étape** : Documenter Rate Limits
