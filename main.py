# main.py
import argparse
import os
from src.agents.auditor_agent import AuditorAgent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_dir", required=True)
    args = parser.parse_args()

    auditor = AuditorAgent()

    for filename in os.listdir(args.target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(args.target_dir, filename)
            auditor.analyze_file(file_path)

if __name__ == "__main__":
    main()
