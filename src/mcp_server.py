import os
import sys
import subprocess
from pathlib import Path
from fastmcp import FastMCP

# Project workspace is passed via environment variable by main.py
PROJECT_DIR = Path(os.environ.get("WEAVER_PROJECT_DIR", "./Workspace/default")).resolve()
PROJECT_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("weaver-local-tools")


def _safe_path(rel_path: str) -> Path:
    """Resolve path and block any traversal outside PROJECT_DIR."""
    target = (PROJECT_DIR / rel_path).resolve()
    if not str(target).startswith(str(PROJECT_DIR)):
        raise ValueError(f"Access denied: '{rel_path}' escapes project workspace.")
    return target


def _ensure_project_venv() -> Path:
    """Ensure the target project has its own isolated .venv and return its bin/Scripts path."""
    venv_dir = PROJECT_DIR / ".venv"
    if not venv_dir.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    return venv_dir / ("Scripts" if os.name == "nt" else "bin")


@mcp.tool()
def list_files() -> str:
    """List all files in the current project workspace (excluding .venv and __pycache__)."""
    files = []
    for p in PROJECT_DIR.rglob("*"):
        if p.is_file() and ".venv" not in p.parts and "__pycache__" not in p.parts:
            files.append(str(p.relative_to(PROJECT_DIR)))
    return "\n".join(sorted(files)) if files else "(Workspace is currently empty)"


@mcp.tool()
def read_file(rel_path: str) -> str:
    """Read the exact contents of a file inside the project workspace."""
    target = _safe_path(rel_path)
    if not target.exists():
        return f"ERROR: File '{rel_path}' does not exist."
    return target.read_text(encoding="utf-8")


@mcp.tool()
def write_file(rel_path: str, content: str) -> str:
    """Create or overwrite a file inside the project workspace."""
    target = _safe_path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"SUCCESS: Wrote {len(content)} characters to '{rel_path}'."


@mcp.tool()
def run_command(command: str) -> str:
    """
    Execute a shell/python command inside the project workspace using its isolated .venv.
    Example commands: 'python main.py', 'pytest', 'pip install requests'
    """
    venv_bin = _ensure_project_venv()
    env = os.environ.copy()
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    env["VIRTUAL_ENV"] = str(PROJECT_DIR / ".venv")

    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return (
            f"EXIT_CODE: {res.returncode}\n"
            f"--- STDOUT ---\n{res.stdout.strip() or '(empty)'}\n"
            f"--- STDERR ---\n{res.stderr.strip() or '(empty)'}"
        )
    except subprocess.TimeoutExpired:
        return "EXIT_CODE: -1\n--- STDERR ---\nCommand timed out after 30 seconds."


if __name__ == "__main__":
    mcp.run(transport="stdio")