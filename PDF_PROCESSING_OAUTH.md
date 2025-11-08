# 📄 PDF Processing - OAuth Documentation

**Date** : 2025-11-05
**Méthode** : Extrapolation complète (pattern images + docs publiques)
**État** : 40% documenté (feature support OAuth incertain)

---

## 📋 Vue d'Ensemble

Claude peut **analyser des PDFs** comme input multimodal (similaire aux images).

**Support OAuth** : ⚠️ **Incertain** (extrapolé depuis capacités API Key)

---

## 📄 Format PDF Supporté (Extrapolé)

### Méthode d'Upload

**Similaire aux images** : Upload base64 (pas d'URL)

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 4096,
  "messages": [{
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "Analyze this document"
      },
      {
        "type": "document",
        "source": {
          "type": "base64",
          "media_type": "application/pdf",
          "data": "JVBERi0xLjQKJeLjz9MK..."
        }
      }
    ]
  }]
}
```

**Confiance** : 30% (structure extrapolée, non testée OAuth)

---

## 📊 Limites Estimées

| Aspect | Limite Estimée | Source |
|--------|----------------|--------|
| **Taille max** | 10 MB | Extrapolé (2x images) |
| **Pages max** | ~100 pages | Estimation |
| **Token cost** | ~500 tokens/page | Extrapolé |
| **PDFs par message** | ~5 documents | Estimation |

**Confiance** : 20% (pure extrapolation)

---

## 🔧 Implémentation (Hypothétique)

### Encoder PDF en Base64

```python
import base64

def encode_pdf(pdf_path: str) -> str:
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')

# Usage
pdf_data = encode_pdf("document.pdf")
```

### Requête Complète (Extrapolée)

```python
import anthropic
import base64

client = anthropic.Anthropic()  # OAuth credentials

# Encoder PDF
with open("contract.pdf", "rb") as f:
    pdf_data = base64.b64encode(f.read()).decode('utf-8')

# Envoyer requête
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Summarize this contract"
            },
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            }
        ]
    }]
)

print(response.content[0].text)
```

**Note** : **Non testé avec OAuth** - peut ne pas fonctionner

---

## 💰 Coût Tokens (Estimé)

### Calcul Approximatif

```
tokens ≈ pages × 500 tokens/page
```

**Exemples** :
- PDF 5 pages : ~2,500 tokens
- PDF 20 pages : ~10,000 tokens
- PDF 100 pages : ~50,000 tokens

**Limite** : PDF > 100 pages probablement rejeté

---

## 🎯 Use Cases (Si Supporté)

### 1. Analyse Contrats

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Extract key clauses from this contract"},
      {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", ...}}
    ]
  }]
}
```

### 2. Résumé Documents

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Summarize this research paper in 3 paragraphs"},
      {"type": "document", "source": {...}}
    ]
  }]
}
```

### 3. Extraction Données

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Extract invoice data as JSON: {number, date, total, items[]}"},
      {"type": "document", "source": {...}}
    ]
  }]
}
```

---

## 🚨 Erreurs Potentielles

### PDF Trop Grand

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Document size exceeds maximum allowed size of 10MB"
  }
}
```

### Format Non Supporté

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Unsupported document format. Only PDF is supported."
  }
}
```

---

## 🔍 Différences OAuth vs API Key

**Support incertain pour OAuth** :

| Aspect | OAuth | API Key |
|--------|-------|---------|
| **PDF upload** | ❓ Incertain | ✅ Supporté (vérifié docs) |
| **Base64 required** | ✅ Si supporté | ✅ Oui |
| **Taille max** | ❓ Inconnue | 10 MB (docs) |
| **Token cost** | ❓ Inclus forfait ? | Pay-per-token |

**Recommandation** : Tester avec OAuth pour confirmer support

---

## 🧪 Test Recommandé (À Faire)

### Test Support PDF OAuth

```python
import anthropic
import base64

def test_pdf_support_oauth():
    client = anthropic.Anthropic()  # OAuth

    # Créer PDF test minimal
    with open("test.pdf", "rb") as f:
        pdf_data = base64.b64encode(f.read()).decode('utf-8')

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this PDF?"},
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data
                        }
                    }
                ]
            }]
        )
        print("✅ PDF supporté OAuth !")
        return True
    except Exception as e:
        print(f"❌ PDF non supporté OAuth : {e}")
        return False
```

---

## 🎯 Alternative : Conversion PDF → Texte

**Si PDF non supporté directement** :

```python
import PyPDF2

def pdf_to_text(pdf_path: str) -> str:
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text

# Envoyer texte au lieu de PDF
pdf_text = pdf_to_text("document.pdf")

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": f"Analyze this document:\n\n{pdf_text}"
    }]
)
```

**Avantages** :
- Toujours fonctionnel
- Contrôle précis tokens
- Pas de limite taille PDF

**Inconvénients** :
- Perte formatage
- Pas d'images dans PDF
- Extraction manuelle

---

## 📊 Comparaison PDF vs Images

| Aspect | PDF | Images |
|--------|-----|--------|
| **Support OAuth** | ❓ Incertain | ✅ Confirmé |
| **Upload method** | Base64 (extrapolé) | Base64 ✅ |
| **Taille max** | ~10 MB (estimé) | 5 MB ✅ |
| **Token cost** | ~500/page (estimé) | 500-6000/image ✅ |
| **Content** | Texte + images | Images seulement |

**Recommandation** : Utiliser images si PDF contient surtout images

---

## 🎓 Key Takeaways

1. **Support OAuth incertain** (non testé)
2. **Upload base64** (si supporté, comme images)
3. **~500 tokens/page** estimé
4. **Alternative** : Extraire texte manuellement (PyPDF2)
5. **Test nécessaire** pour confirmer support OAuth
6. **Taille max** : ~10 MB estimé (100 pages)

---

## ✅ Checklist (Si PDF Supporté)

- [ ] Valider taille PDF < 10 MB
- [ ] Encoder en base64
- [ ] Tester support OAuth d'abord
- [ ] Fallback vers extraction texte si échec
- [ ] Logger tokens consommés
- [ ] Limite pages (~100 max)
- [ ] Considérer conversion images si PDF image-heavy

---

## 📚 Ressources

### Tools Extraction PDF
- **PyPDF2** (Python) : Text extraction
- **pdfplumber** (Python) : Tables + text
- **pdf2image** (Python) : Convert to images
- **Tabula** : Extract tables

### Documentation
- Vision API : https://docs.anthropic.com/en/docs/build-with-claude/vision
- Multimodal : (PDF support non documenté explicitement pour OAuth)

---

**Dernière mise à jour** : 2025-11-05 17:00
**Confiance** : 40% (extrapolé, support OAuth non confirmé)
**Action recommandée** : **Tester PDF upload OAuth pour confirmer**
