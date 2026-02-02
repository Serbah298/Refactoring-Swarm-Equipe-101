# src/agents/fixer_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import safe_read_file, safe_write_file
import os

class FixerAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def fix_code(self, file_path: str, analysis_feedback: str):
        """Corrige le code en fonction du retour de l'auditor."""
        try:
            # Étape 1 : Lire le code original
            code = safe_read_file(file_path)

            # Étape 2 : Construire le prompt pour le LLM
            input_prompt = (
                "Tu es un agent de correction de code Python.\n"
                "Applique UNIQUEMENT les corrections décrites dans le plan ci-dessous.\n"
                "Ne modifie rien d'autre.\n"
                "Ne reformule pas le code.\n"
                "Ne commente pas tes actions.\n"
                "Ne produis QUE le code Python corrigé.\n\n"
                "PLAN DE CORRECTION :\n"
                f"{analysis_feedback}\n\n"
                "CODE À CORRIGER :\n"
                f"{code}"
            )


            # Étape 3 : (Simulation pour test)
            output_response = (
                "Correction appliquée : indentation corrigée, ajout d’une docstring."
            )

            # Étape 4 : Simuler le code corrigé
            fixed_code = '"""Fonction corrigée"""\n' + code.replace("   ", "    ")

            # Étape 5 : Enregistrer le nouveau code dans sandbox/
            fixed_file_path = os.path.join(
                "sandbox", f"fixed_{os.path.basename(file_path)}"
            )

            # ✅ Sécurité : interdiction d’écrire hors du dossier sandbox
            if not os.path.abspath(fixed_file_path).startswith(os.path.abspath("sandbox")):
                raise PermissionError("Tentative d’écriture hors de sandbox interdite !")

            safe_write_file(fixed_file_path, fixed_code)

            # Étape 6 : Logging obligatoire
            log_experiment(
                agent_name="Fixer_Agent",
                model_used=self.model_name,
                action=ActionType.FIX,
                details={
                    "file_fixed": os.path.basename(fixed_file_path),
                    "input_prompt": input_prompt,
                    "output_response": output_response,
                    "status": "code saved"
                },
                status="SUCCESS"
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
                status="FAILURE"
            )
            print(f"❌ Erreur FixerAgent : {e}")
