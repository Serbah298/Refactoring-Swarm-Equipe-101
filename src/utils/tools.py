"""
tools.py — API interne pour les agents.
Toutes les opérations fichier / analyse passent ici.
Sécurité : aucune écriture hors du dossier sandbox autorisée.
"""

import os
import subprocess
import sys


# ─── Résolution du dossier sandbox autorisé ─────────────────────────────────
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
SANDBOX_ROOT = os.path.join(_PROJECT_ROOT, "sandbox")


# ─── Sécurité : vérifier qu'un chemin reste dans le sandbox ─────────────────
def _assert_in_sandbox(path: str) -> str:
    """Retourne le chemin absolu si OK, sinon lève une erreur."""
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(SANDBOX_ROOT)):
        raise PermissionError(
            f"[SÉCURITÉ] Tentative d'écriture hors sandbox : {abs_path}"
        )
    return abs_path


# ─── Lecture d'un fichier ────────────────────────────────────────────────────
def read_file(filepath: str) -> str:
    """Lit et retourne le contenu textuel d'un fichier."""
    abs_path = os.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"[TOOLS] Fichier introuvable : {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


# ─── Écriture d'un fichier (uniquement dans le sandbox) ─────────────────────
def write_file(filepath: str, content: str) -> None:
    """Écrit du contenu dans un fichier — uniquement dans le sandbox."""
    safe = _assert_in_sandbox(filepath)
    os.makedirs(os.path.dirname(safe), exist_ok=True)
    with open(safe, "w", encoding="utf-8") as f:
        f.write(content)


# ─── Liste des fichiers Python dans un dossier ──────────────────────────────
def list_python_files(directory: str) -> list[str]:
    """Retourne la liste des .py dans le dossier (récursif)."""
    py_files = []
    for root, _, files in os.walk(directory):
        for name in files:
            if name.endswith(".py"):
                py_files.append(os.path.join(root, name))
    return sorted(py_files)


# ─── Exécution de pylint sur un fichier ──────────────────────────────────────
def run_pylint(filepath: str) -> dict:
    """
    Lance pylint sur `filepath`.
    Retourne { "score": float, "messages": str, "returncode": int }
    """
    abs_path = os.path.abspath(filepath)
    cmd = [
        sys.executable, "-m", "pylint",
        abs_path,
        "--output-format=text",
        "--disable=C0114,C0115,C0116"   # on ignore les docstrings manquantes en score
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return {"score": 0.0, "messages": "Timeout", "returncode": -1}
    except FileNotFoundError:
        return {"score": 0.0, "messages": "pylint not installed", "returncode": -1}

    # Extraction du score (dernière ligne typique : "Rated at X.00/10")
    score = 0.0
    for line in result.stdout.splitlines():
        if "Rated at" in line or "rated at" in line:
            try:
                parts = line.lower().split("rated at")[1].split("/")[0].strip()
                score = float(parts)
            except (IndexError, ValueError):
                pass

    return {
        "score": score,
        "messages": result.stdout + result.stderr,
        "returncode": result.returncode
    }


# ─── Exécution de pytest sur un fichier ou dossier ──────────────────────────
def run_pytest(target: str) -> dict:
    """
    Lance pytest sur `target` (fichier ou dossier).
    Retourne { "passed": bool, "output": str, "returncode": int }
    """
    abs_path = os.path.abspath(target)
    cmd = [sys.executable, "-m", "pytest", abs_path, "-v", "--tb=short"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "Timeout", "returncode": -1}
    except FileNotFoundError:
        return {"passed": False, "output": "pytest not installed", "returncode": -1}

    return {
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }


# ─── Copie d'un fichier vers le sandbox ─────────────────────────────────────
def copy_to_sandbox(src_path: str, dest_relative: str) -> str:
    """
    Copie un fichier source vers sandbox/<dest_relative>.
    Retourne le chemin complet dans le sandbox.
    """
    import shutil
    dest = os.path.join(SANDBOX_ROOT, dest_relative)
    _assert_in_sandbox(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src_path, dest)
    return dest
