from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DEPLOY = REPO / "deployment"
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _bash() -> str | None:
    if GIT_BASH.is_file():
        return str(GIT_BASH)
    found = shutil.which("bash")
    if found and "WindowsApps" not in found and "System32" not in found:
        return found
    return None


def test_start_sh_is_valid_bash() -> None:
    script = DEPLOY / "start.sh"
    assert script.is_file()
    bash = _bash()
    if bash is None:
        pytest.skip("Git Bash is not installed")
    result = subprocess.run(
        [bash, "-n", str(script)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr


def test_start_sh_help_exits_cleanly() -> None:
    bash = _bash()
    if bash is None:
        pytest.skip("Git Bash is not installed")
    result = subprocess.run(
        [bash, str(DEPLOY / "start.sh"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0
    assert "--prod" in result.stdout


def test_start_ps1_parses() -> None:
    script = DEPLOY / "start.ps1"
    assert script.is_file()
    quoted = str(script).replace("'", "''")
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$e=$null; "
                "[void][System.Management.Automation.Language.Parser]::ParseFile("
                f"'{quoted}',[ref]$null,[ref]$e); "
                "if($e){ $e | ForEach-Object { $_.ToString() }; exit 1 }"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_prod_compose_file_parses() -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker is not installed")
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(REPO / "docker-compose.prod.yml"),
            "--env-file",
            str(DEPLOY / "env.example"),
            "config",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert "agent:" in (result.stdout or "")


def test_ensure_agent_tokens_compiles() -> None:
    script = DEPLOY / "ensure_agent_tokens.py"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
