from __future__ import annotations

import json
from typing import Any

_CONTENT_KINDS = {
    "project": "项目",
    "article": "文章",
    "journal": "日志",
    "about": "关于",
    "category": "分类",
}


def _args(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for item in value.values():
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return ""


def _repo_name(value: str) -> str:
    parts = [part for part in value.replace("\\", "/").split("/") if part]
    return parts[-1] if parts else ""


def _file_name(value: str) -> str:
    parts = [part for part in value.replace("\\", "/").split("/") if part]
    if not parts:
        return ""
    if len(parts) <= 2:
        return "/".join(parts)
    return "/".join(parts[-2:])


def _join(*parts: str) -> str:
    return " · ".join(part for part in parts if part)


def _tool_key(name: str) -> str:
    return (name or "").replace("-", "_").casefold()


def format_owner_tool_label(name: str, arguments: Any = None) -> str:
    key = _tool_key(name)
    args = _args(arguments)
    repo = _repo_name(
        _text(args.get("full_name"), args.get("project_slug"), args.get("repo"))
    )
    path = _file_name(_text(args.get("path"), args.get("file_path")))
    identifier = _text(
        args.get("identifier"),
        args.get("slug"),
        args.get("title"),
        args.get("query"),
    )
    kind = _CONTENT_KINDS.get(str(args.get("kind") or "").casefold(), "")

    if "get_github_file" in key or "get_source_file" in key:
        return _join(repo, path) or repo or path
    if "get_github_source" in key or "get_project_source" in key:
        return _join(repo, path) or repo
    if "list_github_repos" in key:
        return "GitHub"
    if (
        "create_content" in key
        or "update_content" in key
        or "publish_content" in key
        or "get_content" in key
    ):
        return _join(kind, identifier) or identifier or kind
    if "list_content" in key:
        return kind or identifier
    if "remember_knowledge" in key or "update_knowledge" in key:
        return _join("关于我", identifier)
    if "list_knowledge" in key:
        return "关于我"
    if "update_site" in key or "get_site" in key or key.endswith("overview"):
        return "站点"
    if "comment" in key:
        return "评论"
    return _join(repo, path, identifier)


def format_owner_tool_activities(tools: Any) -> str:
    labels: list[str] = []
    rows = tools if isinstance(tools, list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("phase") or "start") not in {"", "start"}:
            continue
        label = format_owner_tool_label(str(row.get("name") or ""), row.get("arguments"))
        if label and label not in labels:
            labels.append(label)
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]} · +{len(labels) - 1}"


def label_from_tool_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        existing = payload.get("label")
        if isinstance(existing, str) and existing.strip():
            return existing.strip()
        return format_owner_tool_activities(payload.get("tools"))
    return ""


def parse_sse_block(block: str) -> tuple[str, Any]:
    event = ""
    data_lines: list[str] = []
    for line in block.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    data = "\n".join(data_lines)
    if not data or data == "[DONE]":
        return event, None
    try:
        return event, json.loads(data)
    except json.JSONDecodeError:
        return event, data


def rewrite_owner_sse_block(block: str) -> bytes | None:
    if not block.strip():
        return None
    event, payload = parse_sse_block(block)
    if event == "tool_activity":
        label = label_from_tool_payload(payload)
        if not label:
            return None
        return (
            "event: tool_activity\n"
            f"data: {json.dumps({'label': label}, ensure_ascii=False)}\n\n"
        ).encode()
    ending = "\r\n\r\n" if "\r\n" in block else "\n\n"
    return (block.strip() + ending).encode()
