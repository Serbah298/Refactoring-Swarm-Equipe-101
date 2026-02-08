"""
judge_agent.py — The Judge (CORRIGÉ : utilise GENERATION pour les tests)
1. GÉNÈRE des tests → ACTION: GENERATION
2. Exécute les tests
3. Donne le verdict → ACTION: ANALYSIS
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.tools import read_file, write_file, run_pylint, run_pytest
from src.utils.logger import log_experiment, ActionType
from src.utils.gemini_client import call_gemini, MODEL_NAME


# ═══════════════════════════════════════════════════════════════════════════
#  PROMPT 1 : GÉNÉRATION DE TESTS SÉMANTIQUES
# ═══════════════════════════════════════════════════════════════════════════

TEST_GENERATION_PROMPT = """\
Tu es un expert en Test-Driven Development (TDD).

MISSION CRITIQUE :
Analyser le code Python et générer des tests pytest qui valident la LOGIQUE MÉTIER ATTENDUE,
PAS le comportement actuel du code (qui peut contenir des bugs).

RÈGLES D'OR :
1. Analyse les NOMS de fonctions/variables pour comprendre l'INTENTION
2. Génère des tests qui vérifient ce que le code DEVRAIT faire
3. Exemples :
   - "calculate_average([10, 20])" → doit retourner 15 (même si le code actuel retourne 30)
   - "is_palindrome('racecar')" → doit retourner True (même si le code actuel retourne None)
   - "get_discount(100, 0.2)" → doit retourner 80 (même si le code actuel additionne)

IMPORTANT :
- Réponds UNIQUEMENT avec le code pytest complet
- Pas de balises markdown ```python
- Code directement exécutable
- 2-3 tests par fonction (cas normal + edge cases)
"""

# ═══════════════════════════════════════════════════════════════════════════
#  PROMPT 2 : VERDICT FINAL
# ═══════════════════════════════════════════════════════════════════════════

JUDGE_VERDICT_PROMPT = """\
Tu es "The Judge", l'arbitre final de qualité du code.

MISSION :
Décider si le code est acceptable (PASS) ou doit être corrigé (FAIL).

RÈGLES :
1. Réponds UNIQUEMENT en JSON valide
2. Base ta décision sur les données fournies

FORMAT :
{
  "verdict": "PASS | FAIL",
  "pylint_score_after": <score float>,
  "tests_passed": <true | false>,
  "details": "explication courte",
  "next_action": "DONE | RETRY"
}
"""


class JudgeAgent:
    """Agent qui génère des tests sémantiques, les exécute, et donne le verdict"""

    def __init__(self):
        self.agent_name = "Judge_Agent"
        self.last_scores = {}
        self.current_file = None
        self.generated_tests_cache = {}

    def set_current_file(self, filepath):
        """Définit le fichier en cours de traitement"""
        self.current_file = os.path.basename(filepath)

    def run_tests(self, sandbox_dir: str) -> tuple[bool, dict]:
        """
        Pipeline complet :
        1. Génère les tests (ACTION: GENERATION)
        2. Exécute les tests
        3. Retourne le verdict (ACTION: ANALYSIS)
        """
        if not self.current_file:
            return False, {"issues": [], "error_logs": "No file specified"}

        sandbox_abs = os.path.abspath(sandbox_dir)
        filepath = self._find_file(sandbox_abs, self.current_file)
        
        if not filepath:
            return False, {"issues": [], "error_logs": f"{self.current_file} not found"}

        # ═══════════════════════════════════════════════════════════════════
        #  ÉTAPE 1 : GÉNÉRER LES TESTS (ACTION: GENERATION)
        # ═══════════════════════════════════════════════════════════════════
        
        test_file = self._generate_or_get_tests(filepath)

        # ═══════════════════════════════════════════════════════════════════
        #  ÉTAPE 2 : EXÉCUTER PYLINT
        # ═══════════════════════════════════════════════════════════════════
        
        pylint_result = run_pylint(filepath)
        score_after = pylint_result["score"]
        score_before = self.last_scores.get(filepath, 0.0)
        self.last_scores[filepath] = score_after
        
        print(f"[JUDGE] Pylint : {score_after}/10 (avant : {score_before}/10)")

        # ═══════════════════════════════════════════════════════════════════
        #  ÉTAPE 3 : EXÉCUTER PYTEST
        # ═══════════════════════════════════════════════════════════════════
        
        if test_file and os.path.isfile(test_file):
            print(f"[JUDGE] Pytest : {os.path.basename(test_file)}...", end=" ")
            pytest_result = run_pytest(test_file)
            tests_passed = pytest_result["passed"]
            pytest_output = pytest_result["output"]
            print("✅ PASS" if tests_passed else "❌ FAIL")
        else:
            print(f"[JUDGE] ⚠️  Tests non générés, validation sur pylint uniquement")
            tests_passed = True
            pytest_output = "No tests generated"

        # ═══════════════════════════════════════════════════════════════════
        #  ÉTAPE 4 : VERDICT VIA LLM (ACTION: ANALYSIS)
        # ═══════════════════════════════════════════════════════════════════
        
        verdict = self._get_verdict(
            filename=self.current_file,
            score_before=score_before,
            score_after=score_after,
            tests_passed=tests_passed,
            pytest_output=pytest_output
        )

        # ═══════════════════════════════════════════════════════════════════
        #  ÉTAPE 5 : RETOUR
        # ═══════════════════════════════════════════════════════════════════
        
        if verdict["verdict"] == "PASS":
            return True, {"issues": [], "summary": "All passed"}
        else:
            return False, {
                "issues": [{
                    "id": 1,
                    "file": self.current_file,
                    "type": "test_failure",
                    "severity": "critical",
                    "description": verdict.get("details", "Tests failed"),
                    "suggestion": "Fix based on test errors"
                }],
                "error_logs": pytest_output if not tests_passed else None
            }

    # ═══════════════════════════════════════════════════════════════════════
    #  MÉTHODE : GÉNÉRER LES TESTS SÉMANTIQUES (ACTION: GENERATION)
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_or_get_tests(self, filepath: str) -> str:
        """Génère les tests sémantiques (ou retourne ceux déjà générés)"""
        
        # Vérifier le cache
        if filepath in self.generated_tests_cache:
            return self.generated_tests_cache[filepath]

        filename = os.path.basename(filepath)
        module_name = filename.replace(".py", "")
        test_filename = f"test_{filename}"
        test_path = os.path.join(os.path.dirname(filepath), test_filename)

        print(f"\n[JUDGE] 📝 Génération de tests sémantiques pour {filename}...")

        # Lire le code source
        code = read_file(filepath)

        # Prompt pour générer les tests
        user_prompt = f"""\
Analyse ce code Python et génère des tests pytest basés sur la SÉMANTIQUE (intention du code) :

```python
{code}
```

Module à tester : {module_name}

Génère le fichier {test_filename} complet avec :
- Import : import sys, os; sys.path.insert(0, os.path.dirname(__file__)); from {module_name} import ...
- 2-3 tests par fonction qui vérifient ce que le code DEVRAIT faire (pas ce qu'il fait actuellement)
- Tests qui ÉCHOUENT si le code a des bugs logiques

Retourne UNIQUEMENT le code pytest (sans balises markdown).
"""

        api_error = None
        raw_response = None
        status = "SUCCESS"

        try:
            raw_response = call_gemini(TEST_GENERATION_PROMPT, user_prompt)
            test_code = self._clean_code_response(raw_response)
            write_file(test_path, test_code)
            print(f"[JUDGE] ✅ Tests générés : {test_filename}")
            
        except Exception as e:
            print(f"[JUDGE] ⚠️  Erreur génération tests : {e}")
            api_error = str(e)
            raw_response = f"ERROR: {e}"
            status = "FAILURE"
            test_path = None

        # ═══════════════════════════════════════════════════════════════════
        #  LOGGING avec ACTION: GENERATION (pas ANALYSIS !)
        # ═══════════════════════════════════════════════════════════════════
        
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.GENERATION,  # ← GENERATION pour les tests !
            details={
                "file_tested": filepath,
                "input_prompt": user_prompt,
                "output_response": raw_response if raw_response else "ERROR",
                "test_file_generated": test_path,
                "api_error": api_error
            },
            status=status
        )
        
        if test_path:
            self.generated_tests_cache[filepath] = test_path
        
        return test_path

    # ═══════════════════════════════════════════════════════════════════════
    #  MÉTHODE : OBTENIR LE VERDICT (ACTION: ANALYSIS)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_verdict(self, filename, score_before, score_after, tests_passed, pytest_output):
        """Demande au LLM de donner le verdict final"""
        
        user_prompt = f"""\
Fichier : {filename}
Pylint AVANT : {score_before}/10
Pylint APRÈS : {score_after}/10
Tests pytest : {'✅ PASS' if tests_passed else '❌ FAIL'}

Sortie pytest (extrait) :
{pytest_output[:500]}

Donne ton verdict en JSON.
"""

        api_error = None
        raw_response = None
        status = "SUCCESS"

        try:
            raw_response = call_gemini(JUDGE_VERDICT_PROMPT, user_prompt)
            cleaned = raw_response.strip().replace("```json", "").replace("```", "").strip()
            verdict_data = json.loads(cleaned)
        except Exception as e:
            api_error = str(e)
            raw_response = f"ERROR: {e}"
            status = "FAILURE"
            # Fallback : décision basée sur les faits
            verdict_data = {
                "verdict": "PASS" if tests_passed and score_after >= score_before else "FAIL",
                "pylint_score_after": score_after,
                "tests_passed": tests_passed,
                "details": "Décision automatique (LLM error)",
                "next_action": "DONE" if tests_passed else "RETRY"
            }

        # ═══════════════════════════════════════════════════════════════════
        #  LOGGING avec ACTION: ANALYSIS (verdict seulement)
        # ═══════════════════════════════════════════════════════════════════
        
        log_experiment(
            agent_name=self.agent_name,
            model_used=MODEL_NAME,
            action=ActionType.ANALYSIS,  # ← ANALYSIS pour le verdict
            details={
                "file_judged": filename,
                "input_prompt": user_prompt,
                "output_response": raw_response if raw_response else json.dumps(verdict_data),
                "pylint_score_before": score_before,
                "pylint_score_after": score_after,
                "tests_passed": tests_passed,
                "verdict": verdict_data.get("verdict", "UNKNOWN"),
                "api_error": api_error
            },
            status=status
        )

        return verdict_data

    # ═══════════════════════════════════════════════════════════════════════
    #  UTILITAIRES
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _find_file(sandbox_abs, filename):
        """Trouve le fichier dans le sandbox"""
        filepath = os.path.join(sandbox_abs, filename)
        if os.path.isfile(filepath):
            return filepath
        filepath = os.path.join(sandbox_abs, "dataset_test", filename)
        if os.path.isfile(filepath):
            return filepath
        return None

    @staticmethod
    def _clean_code_response(response: str) -> str:
        """Nettoie la réponse LLM pour extraire le code"""
        lines = response.strip().splitlines()
        in_block = False
        code_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```python") or stripped.startswith("```"):
                in_block = not in_block
                continue
            if in_block or not stripped.startswith("```"):
                code_lines.append(line)

        if not code_lines:
            code_lines = lines

        return "\n".join(code_lines).strip() + "\n"
