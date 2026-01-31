import subprocess
from pathlib import Path

PROJECT_ROOT = Path.cwd()

def run_pylint(path: str) -> dict:
    try:
        result = subprocess.run(
            ["pylint", path],
            capture_output=True,
            text=True
        )

        score = None
        for line in result.stdout.splitlines():
            if "Your code has been rated at" in line:
                try:
                    score = float(line.split("rated at")[1].split("/")[0])
                except Exception:
                    score = None

        return {
            "success": result.returncode == 0,
            "score": score,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def run_pytest() -> dict:
    try:
        result = subprocess.run(
            ["pytest"],
            capture_output=True,
            text=True
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def safe_read_file(path: str) -> str:
    try:
        file_path = (PROJECT_ROOT / path).resolve()
        if not str(file_path).startswith(str(PROJECT_ROOT)):
            raise ValueError("Access denied")
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Cannot read file: {e}")

def safe_write_file(path: str, content: str) -> None:
    try:
        file_path = (PROJECT_ROOT / path).resolve()
        if not str(file_path).startswith(str(PROJECT_ROOT)):
            raise ValueError("Access denied")
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Cannot write file: {e}")
