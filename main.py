import argparse
import os
import sys
from src.agents.auditor_agent import AuditorAgent
from src.agents.fixer_agent import FixerAgent
from src.agents.judge_agent import JudgeAgent


def main():
    """Point d'entrée principal"""
    
    # ══════════════════════════════════════════════════════════════════════
    #  PARSING DES ARGUMENTS (requis par le Bot de Correction)
    # ══════════════════════════════════════════════════════════════════════
    
    parser = argparse.ArgumentParser(description="Refactoring Swarm - Correction automatique de code Python")
    parser.add_argument(
        "--target_dir",
        required=True,
        help="Dossier contenant les fichiers Python à corriger"
    )
    args = parser.parse_args()

    # ══════════════════════════════════════════════════════════════════════
    #  VALIDATION DU DOSSIER CIBLE
    # ══════════════════════════════════════════════════════════════════════
    
    target_dir = args.target_dir
    
    if not os.path.isdir(target_dir):
        print(f"❌ ERREUR : Le dossier {target_dir} n'existe pas.")
        sys.exit(1)

    # Lister les fichiers Python (exclure les tests)
    try:
        all_files = [
            f for f in os.listdir(target_dir)
            if f.endswith(".py") and not f.startswith("test_")
        ]
    except PermissionError:
        print(f"❌ ERREUR : Permission refusée pour accéder à {target_dir}")
        sys.exit(1)

    if not all_files:
        print(f"⚠️  Aucun fichier Python à traiter dans {target_dir}")
        print("✅ Traitement terminé (0 fichier)")
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════════
    #  INITIALISATION DES AGENTS
    # ══════════════════════════════════════════════════════════════════════
    
    print(f"\n{'='*70}")
    print(f"🤖 REFACTORING SWARM")
    print(f"{'='*70}")
    print(f"📂 Dossier cible : {target_dir}")
    print(f"📄 {len(all_files)} fichier(s) à traiter")
    print(f"{'='*70}\n")

    auditor = AuditorAgent()
    fixer = FixerAgent()
    judge = JudgeAgent()

    # ══════════════════════════════════════════════════════════════════════
    #  TRAITEMENT DE CHAQUE FICHIER
    # ══════════════════════════════════════════════════════════════════════
    
    files_passed = 0
    files_failed = 0

    for idx, filename in enumerate(all_files, 1):
        file_path = os.path.join(target_dir, filename)
        
        print(f"\n{'='*70}")
        print(f"📄 [{idx}/{len(all_files)}] {filename}")
        print(f"{'='*70}")

        # Indiquer au Judge quel fichier on traite (pour tests ciblés)
        judge.set_current_file(filename)

        try:
            # ─── ÉTAPE 1 : AUDIT ──────────────────────────────────────────
            analysis_feedback = auditor.analyze_file(file_path)
            
            # ─── ÉTAPE 2 : CORRECTION ─────────────────────────────────────
            fixed_path = fixer.fix_code(file_path, analysis_feedback)

            # ─── ÉTAPE 3 : BOUCLE DE VALIDATION (max 3 itérations) ───────
            for iteration in range(3):
                print(f"\n🔁 Itération {iteration+1}/3 pour {filename}")
                
                # Tester le fichier corrigé
                success, feedback = judge.run_tests(os.path.dirname(fixed_path))

                if success:
                    print(f"✅ {filename} validé !")
                    files_passed += 1
                    break
                else:
                    if iteration == 2:  # Dernière itération
                        print(f"⚠️  {filename} : max itérations atteint")
                        files_failed += 1
                        break
                    
                    print(f"🔧 Nouvelle tentative de correction...")
                    fixed_path = fixer.fix_code(fixed_path, feedback)
            
            print(f"\n✓ Fichier sauvegardé : {fixed_path}")

        except Exception as e:
            print(f"\n❌ ERREUR lors du traitement de {filename} : {e}")
            files_failed += 1
            continue

    # ══════════════════════════════════════════════════════════════════════
    #  RAPPORT FINAL
    # ══════════════════════════════════════════════════════════════════════
    
    print(f"\n{'='*70}")
    print(f"🏁 TRAITEMENT TERMINÉ")
    print(f"{'='*70}")
    print(f"✅ Fichiers validés     : {files_passed}/{len(all_files)}")
    print(f"⚠️  Fichiers avec erreurs : {files_failed}/{len(all_files)}")
    print(f"📊 Logs disponibles     : logs/experiment_data.json")
    print(f"📁 Code corrigé         : sandbox/")
    print(f"{'='*70}\n")

    # Codes de sortie pour le Bot de Correction
    if files_failed == 0:
        sys.exit(0)  # Succès total
    elif files_passed > 0:
        sys.exit(0)  # Succès partiel (acceptable)
    else:
        sys.exit(1)  # Échec total


if __name__ == "__main__":
    main()

