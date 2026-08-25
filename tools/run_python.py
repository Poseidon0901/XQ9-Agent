from rich.console import Console
import subprocess
import sys

MAX_TIMEOUT = 300

def run_python(code: str, timeout: int = 10,console: Console = None):
    timeout = max(1, min(int(timeout), MAX_TIMEOUT))
    
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout
    )

    console.print(f"[yellow]Running python code: {code}[/yellow]")
    console.print(f"[yellow]Output: {result.stdout}[/yellow]")
    console.print(f"[yellow]Error: [/yellow][red]{result.stderr}[/red]")
    console.print(f"[yellow]Return Code: {result.returncode}[/yellow]")
    console.print("")
    
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }