# src/agents/judge_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import run_pytest


class JudgeAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def run_tests(self, target_dir: str):
        """
        Exécute pytest et retourne un booléen STRICT + feedback texte.
        Compatible avec la boucle de main.py.
        """
        try:
            input_prompt = (
                f"Exécution automatique des tests pytest "
                f"sur le dossier cible : {target_dir}"
            )

            # 🔧 Appel correct (sans argument)
            test_result = run_pytest()

            success = bool(test_result.get("success", False))
            output_response = (
                test_result.get("stdout", "") +
                test_result.get("stderr", "")
            )

            action = ActionType.GENERATION if success else ActionType.DEBUG

            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=action,
                details={
                    "input_prompt": input_prompt,
                    "output_response": output_response,
                },
                status="SUCCESS" if success else "FAILURE",
            )

            return success, output_response

        except Exception as e:
            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=ActionType.DEBUG,
                details={
                    "input_prompt": "Erreur lors de l'exécution de pytest",
                    "output_response": str(e),
                },
                status="FAILURE",
            )
            return False, str(e)


