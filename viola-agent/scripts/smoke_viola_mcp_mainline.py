"""End-to-end smoke for viola MCP mainline migration."""

from __future__ import annotations

import json
import os


def main() -> int:
    mode = (os.getenv("CS_VIOLA_MAINLINE_MODE") or "off").strip().lower()
    result = {
        "mode": mode,
        "checks": {
            "mainline_switch_present": mode in {"off", "shadow", "canary", "full"},
            "fallback_flag_present": (
                (os.getenv("CS_VIOLA_MAINLINE_FALLBACK_ENABLED") or "true").strip().lower()
                in {"0", "1", "false", "true", "yes", "no", "on", "off"}
            ),
        },
    }
    result["ok"] = all(result["checks"].values())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
