# src/agents/auditor_agent.py
from src.utils.logger import log_experiment, ActionType
from src.utils.tools import safe_read_file, safe_write_file
import os

class AuditorAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    def analyze_file(self, file_path: str):
        """Analyse un fichier Python et détecte les problèmes."""
        try:
            # Étape 1 : Lire le contenu du fichier
            code = safe_read_file(file_path)

            # Étape 2 : Construire le prompt pour le LLM
            input_prompt = (
                "Tu es un auditeur de code Python strict.\n"
                "Analyse UNIQUEMENT le code ci-dessous.\n"
                "Retourne une liste numérotée de problèmes détectés.\n"
                "Chaque élément doit être court et factuel.\n"
                "N'inclus AUCUNE solution.\n"
                "N'inclus AUCUNE explication.\n"
                "N'inclus AUCUN texte hors de la liste.\n\n"
                f"{code}"
            )


            # Étape 3 : (Ici, on simule la réponse du LLM)
            # Plus tard, tu remplaceras par un appel réel à Gemini
            output_response = (
                "J'ai détecté une absence de docstring et une mauvaise indentation dans la fonction foo()."
            )

            # Étape 4 : Enregistrer l’interaction dans les logs
            log_experiment(
                agent_name="Auditor_Agent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": os.path.basename(file_path),
                    "input_prompt": input_prompt,
                    "output_response": output_response,
                    "issues_found": 2
                },
                status="SUCCESS"
            )

            print(f"✅ Analyse terminée pour {file_path}")
            return output_response

        except Exception as e:
            log_experiment(
                agent_name="Auditor_Agent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": "ERREUR lors de la lecture du fichier",
                    "output_response": str(e)
                },
                status="FAIL"
            )
            print(f"❌ Erreur dans l'auditor : {e}")
