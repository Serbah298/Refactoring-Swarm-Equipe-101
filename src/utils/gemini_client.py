"""
gemini_client.py — Wrapper pour l'API Google Gemini (CORRIGÉ)
"""

import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("[ERREUR] Le package 'google-generativeai' n'est pas installé.")
    print("         Lancez : pip install google-generativeai")
    sys.exit(1)

from dotenv import load_dotenv

# Charge les variables d'environnement depuis .env
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# ─── Configuration de l'API ─────────────────────────────────────────────────
_API_KEY = os.getenv("GOOGLE_API_KEY")
if not _API_KEY or _API_KEY.startswith("AIzaSy..."):
    print("[ERREUR] GOOGLE_API_KEY non configurée dans .env")
    print("         Copiez .env.example vers .env et ajoutez votre clé.")
    sys.exit(1)

genai.configure(api_key=_API_KEY)

# ─── Modèle utilisé ─────────────────────────────────────────────────────────
MODEL_NAME = "models/gemini-2.5-flash"


# ─── Fonction principale d'appel ────────────────────────────────────────────
def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Appelle Gemini avec un system_prompt et un user_prompt.
    Retourne la réponse brute sous forme de chaîne.
    
    CORRIGÉ : system_instruction va dans generate_content(), pas dans le modèle
    """
    # Créer le modèle SANS system_instruction
    model = genai.GenerativeModel(model_name=MODEL_NAME)

    # Combiner system_prompt + user_prompt dans le contenu
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Générer la réponse
    response = model.generate_content(full_prompt)

    # Extraction du texte de la réponse
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    
    return ""
