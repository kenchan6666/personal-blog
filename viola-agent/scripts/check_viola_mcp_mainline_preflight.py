"""Preflight checks for viola MCP mainline migration."""

from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    report = {
        "root_exists": root.exists(),
        "main_py_exists": (root / "main.py").exists(),
        "viola_mode": (os.getenv("CS_VIOLA_MAINLINE_MODE") or "off").strip().lower(),
        "viola_api_base": bool((os.getenv("CS_VIOLA_MAINLINE_API_BASE") or "").strip()),
        "fallback_enabled": (
            (os.getenv("CS_VIOLA_MAINLINE_FALLBACK_ENABLED") or "true").strip().lower()
            not in ("0", "false", "no", "off")
        ),
    }
    report["ok"] = report["root_exists"] and report["main_py_exists"]
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
