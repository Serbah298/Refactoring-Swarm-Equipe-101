# main.py
import argparse
import os
from src.agents.auditor_agent import AuditorAgent
from src.agents.fixer_agent import FixerAgent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_dir", required=True)
    args = parser.parse_args()

    auditor = AuditorAgent()
    fixer = FixerAgent()

    for filename in os.listdir(args.target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(args.target_dir, filename)
            # Étape 1 : Analyse
            analysis_feedback = auditor.analyze_file(file_path)
            # Étape 2 : Correction
            fixer.fix_code(file_path, analysis_feedback)

if __name__ == "__main__":
    main()
