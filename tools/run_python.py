import os
import subprocess
import sys

from rich.console import Console

MAX_TIMEOUT = 300

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
env["PYTHONUNBUFFERED"] = "1"


def run_python(code: str, console: Console, timeout: int = 10):
    timeout = max(1, min(int(timeout), MAX_TIMEOUT))

    console.print(f"Running python code: {code}", markup=False, style="yellow")

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        stdout, stderr, rc = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        stderr = f"TimeoutExpired: exceeded {timeout}s"
        rc = -1

    if stdout:
        console.print(f"Output: {stdout}", markup=False, style="yellow")
    if stderr:
        console.print(f"Error: {stderr}", markup=False, style="red")
    console.print(f"Return Code: {rc}", markup=False, style="yellow")
    console.print("")

    return {"stdout": stdout, "stderr": stderr, "returncode": rc}