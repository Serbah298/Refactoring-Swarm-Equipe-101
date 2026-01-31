import subprocess

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
