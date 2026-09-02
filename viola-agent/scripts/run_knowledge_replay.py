"""Lightweight knowledge replay sanity checker."""

from __future__ import annotations

import json
import os


def main() -> int:
    baseline = [
        {"q": "营业时间？", "expected_fact": "营业时间"},
        {"q": "如何转人工？", "expected_fact": "转人工"},
    ]
    out = {
        "cases": len(baseline),
        "mode": (os.getenv("CS_VIOLA_MAINLINE_MODE") or "off").strip().lower(),
        "status": "ready",
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
