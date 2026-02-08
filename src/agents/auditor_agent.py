"""
auditor_agent.py — The Auditor
Analyse statique du code : pylint + compréhension sémantique via LLM
ACTION: ANALYSIS uniquement
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.tools import read_file, run_pylint
from src.utils.logger import log_experiment, ActionType
from src.utils.gemini_client import call_gemini, MODEL_NAME


AUDITOR_SYSTEM_PROMPT = """\
Tu es "The Auditor", un expert Python spécialisé en analyse de code.

MISSION :
Analyser le code Python et identifier TOUS les problèmes potentiels :
1. Bugs de syntaxe (deux-points manquants, parenthèses, indentation)
2. Bugs de logique (boucles infinies, division par zéro, conditions incorrectes)
3. Problèmes de style (noms de variables peu clairs, imports inutilisés)
4. Problèmes de conception (super() manquant, gestion d'exceptions incorrecte)
5. Manque de docstrings

RÈGLES STRICTES :
1. Tu ne modifies JAMAIS le code. Tu analyses uniquement.
2. Tu réponds UNIQUEMENT en JSON valide.
3. Analyse la SÉMANTIQUE : si une fonction s'appelle "calculate_average" mais fait une somme, c'est un bug !
4. Identifie les bugs même s'ils ne causent pas d'erreur syntax (ex: super() manquant)

FORMAT DE RÉPONSE OBLIGATOIRE :
{
  "issues": [
    {
      "id": 1,
      "file": "nom_fichier.py",
      "type": "syntax_error | logic_error | style_issue | missing_docstring | design_flaw | semantic_error",
      "severity": "critical | warning | info",
      "line": <numéro ligne ou null>,
      "description": "description précise du problème",
      "suggestion": "comment corriger",
      "intent_analysis": "ce que le code DEVRAIT faire selon les noms de variables/fonctions"
    }
  ],
  "pylint_score_before": <score float>,
  "summary": "résumé en une phrase",
  "semantic_analysis": "analyse de l'intention du code basée sur les noms"
}

IMPORTANT : 
- Pour "calculate_average" qui fait sum(x), note : "intent_analysis: Fonction devrait diviser la somme par le nombre d'éléments"
- Pour "is_palindrome" qui retourne None au lieu de False, note : "design_flaw: Retourne None au lieu de False"
"""


class AuditorAgent:
    """Agent d'analyse statique et sémantique du code"""

    def __init__(self):
        self.agent_name = "Auditor_Agent"

    def analyze_file(self, file_path: str) -> dict:
        """
        Analyse complète d'un fichier Python.
        
        Returns:
            dict: {
                "issues": [...],
                "pylint_score_before": float,
                "summary": str,
                "semantic_analysis": str
            }
        """
        print(f"\n[AUDITOR] Analyse de : {file_path}")

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 1 : LECTURE DU CODE
        # ══════════════════════════════════════════════════════════════════
        
        try:
            code = read_file(file_path)
        except FileNotFoundError:
            print(f"[AUDITOR] ⚠️  Fichier introuvable : {file_path}")
            return {
                "issues": [],
                "pylint_score_before": 0.0,
                "summary": "File not found",
                "semantic_analysis": ""
            }

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 2 : ANALYSE STATIQUE (PYLINT)
        # ══════════════════════════════════════════════════════════════════
        
        pylint_result = run_pylint(file_path)
        score_before = pylint_result["score"]
        pylint_messages = pylint_result["messages"]
        
        print(f"[AUDITOR] Pylint score : {score_before}/10")

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 3 : ANALYSE SÉMANTIQUE (LLM)
        # ══════════════════════════════════════════════════════════════════
        
        filename = os.path.basename(file_path)
        
        user_prompt = f"""\
Analyse ce code Python en profondeur :

```python
{code}
```

Fichier : {filename}
Score pylint actuel : {score_before}/10

Messages pylint (pour contexte) :
{pylint_messages[:1000]}

Analyse SÉMANTIQUE requise :
1. Regarde les NOMS de fonctions/variables
2. Déduis l'INTENTION du code
3. Compare avec le COMPORTEMENT réel
4. Détecte les bugs logiques même sans erreur de syntaxe

Retourne ton analyse complète en JSON.
"""

        try:
            raw_response = call_gemini(AUDITOR_SYSTEM_PROMPT, user_prompt)
            print(f"[AUDITOR] Réponse LLM reçue ({len(raw_response)} chars)")
        except Exception as e:
            print(f"[AUDITOR] ⚠️  Erreur API : {e}")
            # Fallback : créer un plan basé uniquement sur pylint
            raw_response = self._create_fallback_analysis(filename, score_before, pylint_messages)

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 4 : LOGGING DE L'INTERACTION
        # ══════════════════════════════════════════════════════════════════
        
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.ANALYSIS,
            details={
                "file_analyzed": file_path,
                "input_prompt": user_prompt,
                "output_response": raw_response,
                "pylint_score_before": score_before,
                "pylint_messages_summary": pylint_messages[:500]
            },
            status="SUCCESS"
        )

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 5 : PARSING DE LA RÉPONSE JSON
        # ══════════════════════════════════════════════════════════════════
        
        try:
            # Nettoyer les balises markdown
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            analysis = json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            print(f"[AUDITOR] ⚠️  Erreur parsing JSON : {e}")
            # Fallback : plan minimal
            analysis = {
                "issues": [
                    {
                        "id": 1,
                        "file": filename,
                        "type": "logic_error",
                        "severity": "warning",
                        "line": None,
                        "description": f"Code nécessite un refactoring (pylint: {score_before}/10)",
                        "suggestion": "Améliorer la qualité du code selon les recommandations pylint",
                        "intent_analysis": "Analyse manuelle requise"
                    }
                ],
                "pylint_score_before": score_before,
                "summary": "Analyse partielle (JSON parse error)",
                "semantic_analysis": "Non disponible"
            }

        # ══════════════════════════════════════════════════════════════════
        #  ÉTAPE 6 : VALIDATION ET ENRICHISSEMENT
        # ══════════════════════════════════════════════════════════════════
        
        # S'assurer que les champs obligatoires existent
        if "pylint_score_before" not in analysis:
            analysis["pylint_score_before"] = score_before
        if "issues" not in analysis:
            analysis["issues"] = []
        if "summary" not in analysis:
            analysis["summary"] = f"{len(analysis['issues'])} problème(s) détecté(s)"

        print(f"[AUDITOR] ✅ {len(analysis['issues'])} problème(s) identifié(s)")
        
        return analysis

    # ══════════════════════════════════════════════════════════════════════
    #  MÉTHODE FALLBACK
    # ══════════════════════════════════════════════════════════════════════

    def _create_fallback_analysis(self, filename: str, score: float, pylint_msgs: str) -> str:
        """Créer une analyse minimale en cas d'erreur API"""
        
        # Extraire quelques messages pylint pour créer des issues
        issues = []
        for line in pylint_msgs.split('\n')[:5]:
            if ':' in line and len(line) > 10:
                issues.append({
                    "id": len(issues) + 1,
                    "file": filename,
                    "type": "style_issue",
                    "severity": "warning",
                    "line": None,
                    "description": line.strip()[:100],
                    "suggestion": "Voir messages pylint pour détails",
                    "intent_analysis": "N/A"
                })
        
        fallback = {
            "issues": issues if issues else [{
                "id": 1,
                "file": filename,
                "type": "logic_error",
                "severity": "warning",
                "line": None,
                "description": "Analyse requise (API quota exceeded)",
                "suggestion": "Refactoring général recommandé",
                "intent_analysis": "N/A"
            }],
            "pylint_score_before": score,
            "summary": f"Analyse basée sur pylint uniquement ({score}/10)",
            "semantic_analysis": "Non disponible (API error)"
        }
        
        return json.dumps(fallback, ensure_ascii=False)
