"""
fixer_agent.py — The Fixer (avec vraie phase DEBUG)
WORKFLOW RETRY :
1. Reçoit error_logs du Judge
2. ANALYSE l'erreur (ACTION: DEBUG) → diagnostique
3. CORRIGE basé sur le diagnostique (ACTION: FIX)
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.tools import read_file, write_file
from src.utils.logger import log_experiment, ActionType
from src.utils.gemini_client import call_gemini, MODEL_NAME


FIXER_SYSTEM_PROMPT = """\
Tu es "The Fixer", un développeur Python expert en correction de code.

MISSION :
Corriger le code Python pour qu'il :
1. Fonctionne correctement (pas d'erreurs)
2. Respecte son INTENTION sémantique (ce qu'il DEVRAIT faire selon les noms)
3. Passe tous les tests
4. Respecte PEP 8

RÈGLES STRICTES :
1. Réponds UNIQUEMENT avec le code Python corrigé complet
2. Ne coupe JAMAIS de parties du code - le fichier doit être complet
3. Pas de balises markdown (```python)
4. Corrige les bugs sémantiques : si l'intention != comportement, corrige le comportement
"""

DEBUG_ANALYSIS_PROMPT = """\
Tu es un expert en débogage Python.

MISSION :
Analyser une stacktrace ou des erreurs de tests pour diagnostiquer le problème.

RÈGLES :
1. Lis attentivement la STACKTRACE et les messages d'erreur
2. Identifie la CAUSE RACINE du problème
3. Réponds UNIQUEMENT en JSON avec ton diagnostic

FORMAT :
{
  "error_type": "AttributeError | AssertionError | TypeError | etc.",
  "root_cause": "explication de la cause racine",
  "affected_lines": [numéros de lignes si identifiés],
  "fix_strategy": "stratégie de correction recommandée"
}
"""

FIXER_RETRY_PROMPT = """\
Tu es "The Fixer", expert en correction de bugs.

MISSION :
Corriger le code basé sur un diagnostic de débogage.

RÈGLES :
1. Applique la stratégie de correction fournie
2. Retourne le code complet corrigé (sans balises markdown)
"""


class FixerAgent:
    """Agent de correction de code avec phase DEBUG séparée"""

    def __init__(self):
        self.agent_name = "Fixer_Agent"

    def fix_code(self, file_path: str, feedback: dict) -> str:
        """Corrige un fichier selon le feedback."""
        
        print(f"\n[FIXER] Correction de : {file_path}")

        # ══════════════════════════════════════════════════════════════════
        #  LECTURE DU CODE
        # ══════════════════════════════════════════════════════════════════
        
        try:
            code = read_file(file_path)
        except FileNotFoundError:
            print(f"[FIXER] ⚠️  Fichier introuvable : {file_path}")
            return file_path

        filename = os.path.basename(file_path)
        issues = feedback.get("issues", [])
        error_logs = feedback.get("error_logs")
        is_retry = error_logs is not None

        # ══════════════════════════════════════════════════════════════════
        #  MODE RETRY : DEBUG puis FIX
        # ══════════════════════════════════════════════════════════════════
        
        if is_retry:
            print("[FIXER] Mode : RETRY (analyse DEBUG puis correction)")
            
            # ─── ÉTAPE 1 : ANALYSER L'ERREUR (ACTION: DEBUG) ─────────────
            diagnostic = self._analyze_error(file_path, code, error_logs)
            
            # ─── ÉTAPE 2 : CORRIGER BASÉ SUR LE DIAGNOSTIC (ACTION: FIX) ─
            corrected_code = self._fix_with_diagnostic(file_path, code, diagnostic, error_logs)
            
        else:
            # ══════════════════════════════════════════════════════════════
            #  MODE FIRST FIX : Correction directe
            # ══════════════════════════════════════════════════════════════
            
            print(f"[FIXER] Mode : FIRST FIX ({len(issues)} problème(s))")
            corrected_code = self._fix_with_issues(file_path, code, issues, feedback)

        # ══════════════════════════════════════════════════════════════════
        #  ÉCRITURE DU FICHIER CORRIGÉ
        # ══════════════════════════════════════════════════════════════════
        
        output_path = self._write_corrected_file(filename, file_path, corrected_code)
        return output_path

    # ══════════════════════════════════════════════════════════════════════
    #  MÉTHODE : ANALYSER L'ERREUR (ACTION: DEBUG)
    # ══════════════════════════════════════════════════════════════════════

    def _analyze_error(self, file_path: str, code: str, error_logs: str) -> dict:
        """Phase DEBUG : analyser la stacktrace pour diagnostiquer"""
        
        print("[FIXER] 🔍 Phase DEBUG : analyse de l'erreur...")
        
        user_prompt = f"""\
Analyse cette stacktrace pour diagnostiquer le problème :

```
{error_logs}
```

Code actuel :
```python
{code}
```

Donne ton diagnostic en JSON.
"""

        api_error = None
        raw_response = None
        diagnostic = {}
        status = "SUCCESS"

        try:
            raw_response = call_gemini(DEBUG_ANALYSIS_PROMPT, user_prompt)
            cleaned = raw_response.strip().replace("```json", "").replace("```", "").strip()
            diagnostic = json.loads(cleaned)
            print(f"[FIXER] Diagnostic : {diagnostic.get('root_cause', 'N/A')[:80]}")
        except Exception as e:
            print(f"[FIXER] ⚠️  Erreur API DEBUG : {e}")
            api_error = str(e)
            raw_response = f"ERROR: {e}"
            status = "FAILURE"
            # Fallback diagnostic
            diagnostic = {
                "error_type": "Unknown",
                "root_cause": "API error during debug",
                "affected_lines": [],
                "fix_strategy": "Manual analysis required"
            }

        # ═══ LOGGING ACTION: DEBUG ═══
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.DEBUG,  # ← ACTION DEBUG !
            details={
                "file_debugged": file_path,
                "input_prompt": user_prompt,
                "output_response": raw_response if raw_response else json.dumps(diagnostic),
                "error_logs_analyzed": error_logs[:500],
                "diagnostic": diagnostic,
                "api_error": api_error
            },
            status=status
        )

        return diagnostic

    # ══════════════════════════════════════════════════════════════════════
    #  MÉTHODE : CORRIGER AVEC DIAGNOSTIC (ACTION: FIX après DEBUG)
    # ══════════════════════════════════════════════════════════════════════

    def _fix_with_diagnostic(self, file_path: str, code: str, diagnostic: dict, error_logs: str) -> str:
        """Applique la correction basée sur le diagnostic"""
        
        print("[FIXER] 🔧 Phase FIX : correction basée sur diagnostic...")
        
        user_prompt = f"""\
Corrige ce code basé sur le diagnostic de débogage :

DIAGNOSTIC :
{json.dumps(diagnostic, indent=2, ensure_ascii=False)}

ERREURS ORIGINALES :
```
{error_logs[:500]}
```

CODE ACTUEL :
```python
{code}
```

Applique la stratégie de correction et retourne le code complet corrigé (sans balises markdown).
"""

        api_error = None
        raw_response = None
        corrected_code = code  # Fallback
        status = "SUCCESS"

        try:
            raw_response = call_gemini(FIXER_RETRY_PROMPT, user_prompt)
            corrected_code = self._clean_code_response(raw_response)
            print(f"[FIXER] Correction appliquée ({len(corrected_code)} chars)")
        except Exception as e:
            print(f"[FIXER] ⚠️  Erreur API FIX : {e}")
            api_error = str(e)
            raw_response = f"ERROR: {e}"
            status = "FAILURE"

        # ═══ LOGGING ACTION: FIX (après DEBUG) ═══
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.FIX,
            details={
                "file_fixed": file_path,
                "input_prompt": user_prompt,
                "output_response": raw_response if raw_response else "ERROR",
                "diagnostic_used": diagnostic,
                "is_retry": True,
                "code_length_before": len(code),
                "code_length_after": len(corrected_code),
                "api_error": api_error
            },
            status=status
        )

        return corrected_code

    # ══════════════════════════════════════════════════════════════════════
    #  MÉTHODE : CORRIGER AVEC ISSUES (ACTION: FIX direct)
    # ══════════════════════════════════════════════════════════════════════

    def _fix_with_issues(self, file_path: str, code: str, issues: list, feedback: dict) -> str:
        """Première correction basée sur les issues de l'Auditor"""
        
        semantic_analysis = feedback.get("semantic_analysis", "")
        
        user_prompt = f"""\
Corrige ce code Python :

```python
{code}
```

Problèmes identifiés :
{json.dumps(issues, indent=2, ensure_ascii=False)}

Analyse sémantique : {semantic_analysis}

Retourne le code complet corrigé (sans balises markdown).
"""

        api_error = None
        raw_response = None
        corrected_code = code
        status = "SUCCESS"

        try:
            raw_response = call_gemini(FIXER_SYSTEM_PROMPT, user_prompt)
            corrected_code = self._clean_code_response(raw_response)
            print(f"[FIXER] Correction appliquée ({len(corrected_code)} chars)")
        except Exception as e:
            print(f"[FIXER] ⚠️  Erreur API : {e}")
            api_error = str(e)
            raw_response = f"ERROR: {e}"
            status = "FAILURE"

        # ═══ LOGGING ACTION: FIX ═══
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.FIX,
            details={
                "file_fixed": file_path,
                "input_prompt": user_prompt,
                "output_response": raw_response if raw_response else "ERROR",
                "issues_addressed": [i.get("id") for i in issues],
                "is_retry": False,
                "code_length_before": len(code),
                "code_length_after": len(corrected_code),
                "api_error": api_error
            },
            status=status
        )

        return corrected_code

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITAIRES
    # ══════════════════════════════════════════════════════════════════════

    def _write_corrected_file(self, filename: str, original_path: str, code: str) -> str:
        """Écrit le fichier corrigé dans sandbox/"""
        
        if original_path.startswith("sandbox"):
            output_path = original_path
        else:
            output_path = os.path.join("sandbox", filename)

        try:
            write_file(output_path, code)
            print(f"[FIXER] ✅ Fichier écrit : {output_path}")
        except PermissionError:
            safe_output = os.path.join("sandbox", filename)
            write_file(safe_output, code)
            output_path = safe_output

        return output_path

    @staticmethod
    def _clean_code_response(response: str) -> str:
        """Nettoie la réponse LLM"""
        lines = response.strip().splitlines()
        in_block = False
        code_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```python"):
                in_block = True
                continue
            if stripped == "```" and in_block:
                in_block = False
                continue
            if stripped.startswith("```") and not in_block:
                in_block = True
                continue
            if in_block:
                code_lines.append(line)

        if not code_lines:
            code_lines = lines

        return "\n".join(code_lines).strip() + "\n"