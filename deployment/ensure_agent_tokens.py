"""Fill empty AGENT_* tokens in deployment/.env. Does not need openssl or gh."""

from __future__ import annotations

import argparse
import re
import secrets
from pathlib import Path

KEYS = ("AGENT_INTERNAL_TOKEN", "AGENT_SERVICE_TOKEN")


def current_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def upsert(text: str, key: str, value: str) -> str:
    pattern = rf"^{re.escape(key)}=.*$"
    line = f"{key}={value}"
    if re.search(pattern, text, re.M):
        return re.sub(pattern, line, text, count=1, flags=re.M)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_file")
    args = parser.parse_args()
    path = Path(args.env_file)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    filled: list[str] = []
    used: set[str] = {current_value(text, key) for key in KEYS}
    used.discard("")
    for key in KEYS:
        if current_value(text, key):
            continue
        value = secrets.token_hex(32)
        while value in used:
            value = secrets.token_hex(32)
        used.add(value)
        text = upsert(text, key, value)
        filled.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if filled:
        print(f"generated {', '.join(filled)} in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
