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


def test_recovers_homepage_confused_with_about_main() -> None:
    text = (
        "我无法直接更新您的主页，因为我未能找到名为 \"main\" 的 About 页面。\n\n"
        "我需要先列出所有 About 页面，以确定正确的标识符。"
    )
    calls = recover_inline_tool_calls(
        text,
        available_names=[
            "mcp_portfolio_portfolio_get_site",
            "mcp_portfolio_portfolio_list_content",
        ],
    )
    names = {call.name for call in calls}
    assert "mcp_portfolio_portfolio_get_site" in names
    assert "mcp_portfolio_portfolio_list_content" in names
    listed = next(
        call for call in calls if "list_content" in call.name
    )
    assert listed.arguments["kind"] == "about"
    assert looks_like_tool_preamble(text)
