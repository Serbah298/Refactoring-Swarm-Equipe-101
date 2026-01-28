# main.py
import argparse
import os
from src.agents.auditor_agent import AuditorAgent
from src.agents.fixer_agent import FixerAgent
from src.agents.judge_agent import JudgeAgent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_dir", required=True)
    args = parser.parse_args()

    auditor = AuditorAgent()
    fixer = FixerAgent()
    judge = JudgeAgent()

    for filename in os.listdir(args.target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(args.target_dir, filename)

            # Étape 1 : Audit
            analysis_feedback = auditor.analyze_file(file_path)
            # Étape 2 : Correction
            fixed_path = fixer.fix_code(file_path, analysis_feedback)

            # Étape 3 : Boucle de test et correction
            for iteration in range(3):  # max 3 boucles pour éviter boucle infinie
                print(f"🔁 Itération {iteration+1} pour {filename}")
                success, feedback = judge.run_tests("sandbox")

                if success:
                    print("🎉 Code validé !")
                    break
                else:
                    print("🔧 Nouvelle tentative de correction...")
                    fixer.fix_code(fixed_path, feedback)

if __name__ == "__main__":
    main()
