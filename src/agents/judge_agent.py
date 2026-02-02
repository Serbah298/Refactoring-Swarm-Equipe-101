# src/agents/judge_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import run_pytest
import os
import subprocess

class JudgeAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def run_tests(self, target_dir: str):
        """Exécute pytest sur le dossier corrigé."""
        try:
            input_prompt = (
                f"Exécution automatique des tests pytest "
                f"sur le dossier cible : {target_dir}"
            )
          
            test_result = run_pytest()
            success = test_result["success"]
            output_response = test_result.get("stdout", "") + test_result.get("stderr", "")

            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=ActionType.GENERATION,
                details={
                    "test_target": target_dir,
                    "input_prompt": input_prompt,
                    "output_response": output_response,
                    "passed": success
                },
                status="SUCCESS" if success else "FAIL"
            )

            if success:
                print(f"✅ Tous les tests réussis pour {target_dir}")
            else:
                print(f"❌ Tests échoués pour {target_dir}\n{output_response}")

            return success, output_response

        except Exception as e:
            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=ActionType.GENERATION,
                details={
                    "test_target": target_dir,
                    "input_prompt": "Erreur lors de l'exécution de pytest",
                    "output_response": str(e),
                },
                status="FAILURE"
            )
            print(f"❌ Erreur JudgeAgent : {e}")
            return False, str(e)
