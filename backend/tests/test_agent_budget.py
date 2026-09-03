from app.agent_activity import (
    format_owner_tool_label,
    label_from_tool_payload,
    rewrite_owner_sse_block,
)
from app.agent_budget import (
    LONG_MAX_TOKENS,
    SHORT_MAX_TOKENS,
    TOOL_MAX_TOKENS,
    owner_chat_max_tokens,
    strip_tool_noise,
)
from app.owner_actor import force_draft_if_service, owner_actor


def test_owner_chat_uses_short_budget_for_ordinary_questions() -> None:
    assert owner_chat_max_tokens("这个项目做什么") == SHORT_MAX_TOKENS


def test_owner_chat_uses_tool_budget_for_github_readme() -> None:
    assert owner_chat_max_tokens("读取 customer 仓库的 README.md") == TOOL_MAX_TOKENS
    assert owner_chat_max_tokens("list my github repos") == TOOL_MAX_TOKENS


def test_owner_chat_uses_long_budget_for_article_or_editor() -> None:
    assert owner_chat_max_tokens("写一篇介绍文章") == LONG_MAX_TOKENS
    assert owner_chat_max_tokens("hello", editor_context="正文") == LONG_MAX_TOKENS
    assert owner_chat_max_tokens("write the article in English") == LONG_MAX_TOKENS


def test_owner_tool_activity_uses_repo_and_file_names() -> None:
    assert (
        format_owner_tool_label(
            "mcp_portfolio_portfolio_get_github_file",
            {"full_name": "owner/customer", "path": "README.md"},
        )
        == "customer · README.md"
    )
    assert (
        format_owner_tool_label(
            "mcp_portfolio_portfolio_get_github_source",
            {"full_name": "customer"},
        )
        == "customer"
    )
    assert (
        format_owner_tool_label(
            "mcp_portfolio_portfolio_update_content",
            {"kind": "article", "identifier": "hello-world"},
        )
        == "文章 · hello-world"
    )


def test_tool_activity_sse_rewrites_to_short_label() -> None:
    raw = (
        'event: tool_activity\n'
        'data: {"tools":[{"phase":"start","name":'
        '"mcp_portfolio_portfolio_get_github_file",'
        '"arguments":{"full_name":"customer","path":"docs/README.md"}}]}\n\n'
    )
    rewritten = rewrite_owner_sse_block(raw)
    assert rewritten is not None
    assert rewritten.decode() == (
        'event: tool_activity\ndata: {"label": "customer · docs/README.md"}\n\n'
    )
    assert label_from_tool_payload({"label": "customer · README.md"}) == "customer · README.md"


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
