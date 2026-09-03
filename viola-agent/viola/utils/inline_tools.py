from __future__ import annotations

import json
import re
import secrets
from typing import Any

from viola.providers.base import ToolCallRequest

_ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

_PREAMBLE = re.compile(
    r"(?is)(我将|我会|我來|我来|I(?:['’]?ll| will)|Let me).{0,48}"
    r"(读取|讀取|分析|调用|調用|read|fetch|analy[sz]e|look)"
)

_ANNOUNCED_FILE = re.compile(
    r"(?is)(?:读取|讀取|read(?:ing)?)\s+"
    r"[`\"']?(?P<repo>[A-Za-z0-9._-]+)[`\"']?"
    r"(?:\s*(?:仓库|倉庫|repo(?:sitory)?))?"
    r"(?:\s*(?:的|'s|of))?\s*"
    r"[`\"']?(?P<path>README(?:\.[A-Za-z0-9]+)?|[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)[`\"']?"
)

_JSON_FENCE = re.compile(r"(?is)```(?:json|xml)?\s*([\s\S]*?)```")
_XML_CALL = re.compile(r"(?is)<tool_call\b([^>]*)>([\s\S]*?)</tool_call>")


def looks_like_tool_preamble(text: str | None) -> bool:
    return bool(_PREAMBLE.search(text or ""))


def recover_inline_tool_calls(
    content: str | None,
    *,
    available_names: list[str] | None = None,
) -> list[ToolCallRequest]:
    text = content or ""
    calls: list[ToolCallRequest] = []
    seen: set[tuple[str, str]] = set()

    def add(name: str, arguments: dict[str, Any]) -> None:
        resolved = _resolve_name(name, available_names)
        if not resolved:
            return
        key = (resolved, json.dumps(arguments, sort_keys=True, ensure_ascii=False))
        if key in seen:
            return
        seen.add(key)
        calls.append(
            ToolCallRequest(id=_call_id(), name=resolved, arguments=arguments)
        )

    for match in _ANNOUNCED_FILE.finditer(text):
        add(
            "get_github_file",
            {
                "full_name": match.group("repo"),
                "path": match.group("path"),
            },
        )

    for match in _XML_CALL.finditer(text):
        attrs, body = match.group(1) or "", match.group(2) or ""
        parsed = _parse_json_object(body) or _parse_xml_body(attrs, body)
        if parsed:
            add(parsed[0], parsed[1])

    for match in _JSON_FENCE.finditer(text):
        parsed = _parse_json_object(match.group(1) or "")
        if parsed:
            add(parsed[0], parsed[1])

    return calls


def _call_id() -> str:
    return "".join(secrets.choice(_ALNUM) for _ in range(9))


def _resolve_name(wanted: str, available: list[str] | None) -> str:
    wanted = (wanted or "").strip()
    if not wanted:
        return ""
    names = list(available or [])
    lowered = wanted.casefold()
    for name in names:
        if name.casefold() == lowered:
            return name
    for name in names:
        if name.casefold().endswith(lowered) or lowered in name.casefold():
            return name
    if names and lowered in {"get_github_file", "portfolio_get_github_file"}:
        for name in names:
            if "get_github_file" in name.casefold():
                return name
    if not names and lowered in {"get_github_file", "portfolio_get_github_file"}:
        return "mcp_portfolio_portfolio_get_github_file"
    return wanted if not names else ""


def _parse_json_object(raw: str) -> tuple[str, dict[str, Any]] | None:
    try:
        payload = json.loads(raw.strip())
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    name = str(
        payload.get("name")
        or payload.get("tool")
        or (payload.get("function") or {}).get("name")
        or ""
    )
    arguments = (
        payload.get("arguments")
        or payload.get("parameters")
        or payload.get("args")
        or {}
    )
    if isinstance(payload.get("function"), dict) and not arguments:
        arguments = payload["function"].get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not name or not isinstance(arguments, dict):
        return None
    return name, arguments


def _parse_xml_body(attrs: str, body: str) -> tuple[str, dict[str, Any]] | None:
    name_match = re.search(r"name\s*=\s*[\"']([^\"']+)[\"']", attrs)
    name = name_match.group(1) if name_match else ""
    if not name:
        fn = re.search(r"<name>([^<]+)</name>", body, re.I)
        name = fn.group(1).strip() if fn else ""
    arguments: dict[str, Any] = {}
    for match in re.finditer(
        r"<parameter\s+name=[\"']([^\"']+)[\"']>([\s\S]*?)</parameter>",
        body,
        re.I,
    ):
        arguments[match.group(1)] = match.group(2).strip()
    if name:
        return name, arguments
    return None
