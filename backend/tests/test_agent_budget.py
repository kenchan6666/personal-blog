from app.agent_budget import (
    LONG_MAX_TOKENS,
    SHORT_MAX_TOKENS,
    owner_chat_max_tokens,
    strip_tool_noise,
)
from app.owner_actor import force_draft_if_service, owner_actor


def test_owner_chat_uses_short_budget_for_ordinary_questions() -> None:
    assert owner_chat_max_tokens("这个项目做什么") == SHORT_MAX_TOKENS


def test_owner_chat_uses_long_budget_for_article_or_editor() -> None:
    assert owner_chat_max_tokens("写一篇介绍文章") == LONG_MAX_TOKENS
    assert owner_chat_max_tokens("hello", editor_context="正文") == LONG_MAX_TOKENS
    assert owner_chat_max_tokens("write the article in English") == LONG_MAX_TOKENS


def test_strip_tool_noise_removes_tool_blocks() -> None:
    raw = "结论：可用。\n<tool_call>read README</tool_call>\n<tool_result>huge</tool_result>"
    assert strip_tool_noise(raw) == "结论：可用。"


def test_service_actor_cannot_publish() -> None:
    token = owner_actor.set("service")
    try:
        assert force_draft_if_service("published") == "draft"
        assert force_draft_if_service("draft") == "draft"
    finally:
        owner_actor.reset(token)
    token = owner_actor.set("session")
    try:
        assert force_draft_if_service("published") == "published"
    finally:
        owner_actor.reset(token)
