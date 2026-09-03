from pathlib import Path

_TEMPLATES = Path(__file__).resolve().parents[2] / "viola" / "templates"


def test_agents_prompt_maps_homepage_to_siteprofile() -> None:
    agents = (_TEMPLATES / "AGENTS.md").read_text(encoding="utf-8")
    tools = (_TEMPLATES / "TOOLS.md").read_text(encoding="utf-8")

    assert "SiteProfile" in agents
    assert "portfolio_get_site" in agents
    assert "portfolio_update_site" in agents
    assert "summary / education / experience" in agents
    assert "名叫 main 的 About" in tools
    assert "kind=`about`" in tools
