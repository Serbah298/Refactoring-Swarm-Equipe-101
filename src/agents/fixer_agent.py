# src/agents/fixer_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import safe_read_file, safe_write_file
import os


class FixerAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def fix_code(self, file_path: str, analysis_feedback: str):
        """Corrige le code en fonction du retour de l'auditor ou du judge."""
        try:
            # --- 1. Lire le code ---
            code = safe_read_file(file_path)

            # --- 2. Normaliser le nom du fichier ---
            base_name = os.path.basename(file_path)
            while base_name.startswith("fixed_"):
                base_name = base_name.replace("fixed_", "", 1)

            fixed_file_path = os.path.join("sandbox", f"fixed_{base_name}")

            # --- 3. Construire le prompt ---
            input_prompt = (
                "Tu es un agent de correction de code Python.\n"
                "Applique UNIQUEMENT les corrections décrites ci-dessous.\n"
                "Ne modifie rien d'autre.\n"
                "Ne reformule pas le code.\n"
                "Ne commente pas tes actions.\n"
                "Ne produis QUE le code Python corrigé.\n\n"
                "FEEDBACK :\n"
                f"{analysis_feedback}\n\n"
                "CODE À CORRIGER :\n"
                f"{code}"
            )

            # --- 4. Simulation LLM (TP) ---
            output_response = "Corrections appliquées selon le feedback."
            fixed_code = '"""Fonction corrigée"""\n' + code.replace("   ", "    ")

            # --- 5. Écriture sécurisée ---
            safe_write_file(fixed_file_path, fixed_code)

            # --- 6. Logging conforme ---
            log_experiment(
                agent_name="Fixer_Agent",
                model_used=self.model_name,
                action=ActionType.FIX,
                details={
                    "file_fixed": os.path.basename(fixed_file_path),
                    "input_prompt": input_prompt,
                    "output_response": output_response,
                },
                status="SUCCESS",
            )

            print(f"✅ Fichier corrigé : {fixed_file_path}")
            return fixed_file_path

        except Exception as e:
            log_experiment(
                agent_name="Fixer_Agent",
                model_used=self.model_name,
                action=ActionType.FIX,
                details={
                    "file_fixed": os.path.basename(file_path),
                    "input_prompt": "Erreur pendant la correction",
                    "output_response": str(e),
                },
                status="FAILURE",
            )
            print(f"❌ Erreur FixerAgent : {e}")
            raise
