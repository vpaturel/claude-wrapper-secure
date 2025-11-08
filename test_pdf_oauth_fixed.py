#!/usr/bin/env python3
"""Test PDF upload support avec OAuth - FIXED avec Authorization Bearer"""

import requests
import base64
import json
from pathlib import Path

# Créer un PDF minimal pour test
def create_test_pdf():
    """Créer un PDF minimal valide"""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""

    pdf_path = Path("/tmp/test_oauth_fixed.pdf")
    pdf_path.write_bytes(pdf_content)
    return pdf_path

def test_pdf_oauth_bearer():
    """Test PDF avec Authorization Bearer (méthode OAuth correcte)"""
    print("🧪 Test PDF Upload OAuth - Authorization Bearer")
    print("=" * 50)

    # Créer PDF test
    pdf_path = create_test_pdf()
    print(f"✅ PDF créé: {pdf_path} ({pdf_path.stat().st_size} bytes)")

    # Encoder en base64
    pdf_data = base64.b64encode(pdf_path.read_bytes()).decode('utf-8')
    print(f"✅ PDF encodé base64: {len(pdf_data)} chars")

    # Lire token OAuth depuis credentials
    creds_path = Path.home() / ".claude" / ".credentials.json"
    creds = json.loads(creds_path.read_text())
    access_token = creds["claudeAiOauth"]["accessToken"]
    print(f"✅ Token OAuth: {access_token[:30]}...")

    # Headers OAuth corrects
    headers = {
        "Authorization": f"Bearer {access_token}",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-app": "test-pdf-oauth"
    }

    # Test 1: PDF comme 'document' type
    print("\n🚀 Test 1: PDF comme 'document' type...")
    payload = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 100,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What does this PDF say?"
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
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCÈS: PDF supporté avec type 'document' !")
            print(f"Réponse: {result['content'][0]['text']}")
            print(f"Usage: input={result['usage']['input_tokens']}, output={result['usage']['output_tokens']}")
            return True
        else:
            error = response.json()
            print(f"❌ Type 'document' échoué: {response.status_code}")
            print(f"Erreur: {error}")

    except Exception as e:
        print(f"❌ Erreur requête 'document': {e}")

    # Test 2: PDF comme 'image' type (fallback)
    print("\n🚀 Test 2: PDF comme 'image' type...")
    payload["messages"][0]["content"][1]["type"] = "image"

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCÈS: PDF supporté avec type 'image' !")
            print(f"Réponse: {result['content'][0]['text']}")
            return True
        else:
            error = response.json()
            print(f"❌ Type 'image' échoué: {response.status_code}")
            print(f"Erreur: {error}")
            return False

    except Exception as e:
        print(f"❌ Erreur requête 'image': {e}")
        return False

if __name__ == "__main__":
    result = test_pdf_oauth_bearer()
    print("\n" + "=" * 50)
    if result:
        print("✅ PDF SUPPORTÉ OAUTH")
    else:
        print("❌ PDF NON SUPPORTÉ OAUTH")
        print("\n💡 Alternative: Extraire texte avec PyPDF2 et envoyer comme texte")
