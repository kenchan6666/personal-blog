from pathlib import Path

_TEMPLATES = Path(__file__).resolve().parents[2] / "viola" / "templates"


def test_agents_prompt_maps_homepage_to_siteprofile() -> None:
    agents = (_TEMPLATES / "AGENTS.md").read_text(encoding="utf-8")
    tools = (_TEMPLATES / "TOOLS.md").read_text(encoding="utf-8")

    assert "SiteProfile" in agents
    assert "portfolio_get_site" in agents
    assert "portfolio_update_site" in agents
    assert "summary / education / experience" in agents
    assert "## Constitution" in agents
    assert "同一轮必须把已确认事实写入「关于我」RAG" in agents
    assert "portfolio_publish_content" in agents
    assert "名叫 main 的 About" in tools
    assert "kind=`about`" in tools
    assert "portfolio_publish_content" in tools
    assert "同一轮把已确认事实写入 RAG" in tools
