from viola.utils.inline_tools import looks_like_tool_preamble, recover_inline_tool_calls


def test_recovers_announced_github_readme() -> None:
    text = (
        "我将继续分析您的GitHub仓库。\n\n"
        "我将尝试读取 fabric_demo 仓库的 README.md 文件。"
    )
    calls = recover_inline_tool_calls(
        text,
        available_names=["mcp_portfolio_portfolio_get_github_file"],
    )
    assert len(calls) == 1
    assert calls[0].name == "mcp_portfolio_portfolio_get_github_file"
    assert calls[0].arguments["full_name"] == "fabric_demo"
    assert calls[0].arguments["path"] == "README.md"
    assert looks_like_tool_preamble(text)


def test_recovers_json_tool_fence() -> None:
    text = (
        '```json\n{"name":"mcp_portfolio_portfolio_get_github_file",'
        '"arguments":{"full_name":"customer","path":"README.md"}}\n```'
    )
    calls = recover_inline_tool_calls(text)
    assert calls[0].arguments["full_name"] == "customer"


def test_plain_chat_is_not_a_preamble() -> None:
    assert not looks_like_tool_preamble("这个项目用 FastAPI 和 Next.js。")
    assert recover_inline_tool_calls("这个项目用 FastAPI 和 Next.js。") == []
