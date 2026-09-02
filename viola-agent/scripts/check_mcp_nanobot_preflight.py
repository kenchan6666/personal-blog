"""Preflight checks for nanobot MCP integration."""

from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    fragment = root / "mcp_service" / "mcp_nanobot" / "mcp_common" / "fragment.json"
    results = {
        "fragment_exists": fragment.exists(),
        "backend_api_base_url": bool(os.environ.get("BACKEND_API_BASE_URL", "").strip()),
        "nanobot_write_enabled": os.environ.get("NANOBOT_WRITE_ENABLED", "false").strip().lower(),
        "nanobot_read_only_mode": os.environ.get("NANOBOT_READ_ONLY_MODE", "true").strip().lower(),
    }
    results["ok"] = results["fragment_exists"] and results["backend_api_base_url"]
    print(json.dumps(results, ensure_ascii=False))
    return 0 if results["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
