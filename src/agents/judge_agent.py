# src/agents/judge_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import run_pytest

class JudgeAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        self._already_ran = False

    def run_tests(self, target_dir: str):
        if self._already_ran:
            return False, "Judge already executed"

        self._already_ran = True

        try:
            input_prompt = (
                f"Exécution automatique des tests pytest "
                f"sur le dossier cible : {target_dir}"
            )

            test_result = run_pytest(target_dir)
            success = test_result["success"]
            output_response = test_result.get("stdout", "") + test_result.get("stderr", "")

            action = ActionType.GENERATION if success else ActionType.DEBUG

            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=action,
                details={
                    "input_prompt": input_prompt,
                    "output_response": output_response
                },
                status="SUCCESS" if success else "FAILURE"
            )

            return success, output_response

        except Exception as e:
            log_experiment(
                agent_name="Judge_Agent",
                model_used=self.model_name,
                action=ActionType.DEBUG,
                details={
                    "input_prompt": "Erreur lors de l'exécution de pytest",
                    "output_response": str(e)
                },
                status="FAILURE"
            )
            return False, str(e)

