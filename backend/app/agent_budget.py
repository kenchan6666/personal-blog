from __future__ import annotations

import re

SHORT_MAX_TOKENS = 1024
TOOL_MAX_TOKENS = 4096
LONG_MAX_TOKENS = 8192

_TOOL_HINTS = (
    "readme",
    "github",
    "仓库",
    "倉庫",
    "repository",
    "源码",
    "源碼",
)

_LONG_FORM = (
    "全文",
    "长文",
    "長文",
    "逐字",
    "写一篇",
    "寫一篇",
    "写文章",
    "寫文章",
    "write the article",
    "write an article",
    "draft the article",
    "complete article",
)

_TOOL_NOISE = re.compile(
    r"(?is)"
    r"(?:<tool_call\b.*?</tool_call>)"
    r"|(?:<tool_result\b.*?</tool_result>)"
    r"|(?:```(?:json|xml)?\s*\{\s*\"(?:name|tool|function)\"[\s\S]*?```)"
)


def owner_chat_max_tokens(message: str, *, editor_context: str = "") -> int:
    if editor_context.strip():
        return LONG_MAX_TOKENS
    lowered = (message or "").casefold()
    if any(hint.casefold() in lowered for hint in _LONG_FORM):
        return LONG_MAX_TOKENS
    if any(hint.casefold() in lowered for hint in _TOOL_HINTS):
        return TOOL_MAX_TOKENS
    return SHORT_MAX_TOKENS


def strip_tool_noise(text: str) -> str:
    cleaned = _TOOL_NOISE.sub("", text or "")
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
