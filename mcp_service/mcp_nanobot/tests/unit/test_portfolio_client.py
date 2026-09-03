from __future__ import annotations

import pytest

from mcp_portfolio.server import (
    PortfolioApi,
    _clip_text,
    _find,
    _guard_status_on_update,
    _merge,
    _publish_path,
    _repo_parts,
    _resolve_repo,
)


def test_portfolio_client_requires_service_token(monkeypatch) -> None:
    monkeypatch.delenv("PORTFOLIO_SERVICE_TOKEN", raising=False)
    api = PortfolioApi()

    with pytest.raises(RuntimeError, match="SERVICE_TOKEN"):
        api.request("GET", "/api/owner/site")


def test_portfolio_writes_are_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PORTFOLIO_WRITE_ENABLED", raising=False)
    api = PortfolioApi()

    with pytest.raises(RuntimeError, match="disabled"):
        api.require_write()


def test_merge_preserves_omitted_locales() -> None:
    current = {
        "title": {"zh-Hant": "舊標題", "zh-Hans": "旧标题", "en": "Old"},
        "status": "draft",
    }

    merged = _merge(current, {"title": {"en": "New"}})

    assert merged["title"] == {
        "zh-Hant": "舊標題",
        "zh-Hans": "旧标题",
        "en": "New",
    }
    assert merged["status"] == "draft"


def test_update_payload_cannot_promote_draft_to_published() -> None:
    with pytest.raises(RuntimeError, match="portfolio_publish_content"):
        _guard_status_on_update(
            {"status": "draft"},
            {"status": "published", "title": "A"},
        )
    kept = _guard_status_on_update(
        {"status": "published", "title": "A"},
        {"status": "published", "title": "B"},
    )
    assert kept["status"] == "published"
    drafted = _guard_status_on_update(
        {"status": "published"},
        {"status": "draft"},
    )
    assert drafted["status"] == "draft"


def test_publish_path_rejects_category() -> None:
    assert _publish_path("project", "abc") == "/api/owner/projects/abc/publish"
    assert _publish_path("about", "xyz") == "/api/owner/about-modules/xyz/publish"
    with pytest.raises(RuntimeError, match="Categories"):
        _publish_path("category", "abc")


def test_fragment_enables_publish_tool() -> None:
    import json
    from pathlib import Path

    fragment_path = (
        Path(__file__).resolve().parents[2] / "mcp_common" / "fragment.json"
    )
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    assert "portfolio_publish_content" in fragment["portfolio"]["enabledTools"]


def test_clip_text_keeps_short_source_and_marks_long_source() -> None:
    assert _clip_text("short") == "short"
    clipped = _clip_text("x" * 9000, 100)
    assert clipped.endswith("[truncated]")
    assert len(clipped) < 9000


def test_repo_parts_accept_owner_name_or_short_name() -> None:
    assert _repo_parts("kenchan6666/secret-lab") == ("kenchan6666", "secret-lab")
    assert _repo_parts("taiko_bot_qq") == ("", "taiko_bot_qq")
    with pytest.raises(RuntimeError, match="owner/name"):
        _repo_parts("")


def test_next_knowledge_order_puts_new_facts_on_top() -> None:
    class FakeApi:
        def request(self, method, path, json=None):
            assert path == "/api/owner/agent/knowledge"
            return [{"order": 2}, {"order": 5}, {"order": 1}]

    from mcp_portfolio.server import _next_knowledge_order

    assert _next_knowledge_order(FakeApi()) == 6


def test_find_about_rejects_homepage_alias_named_main() -> None:
    modules = [
        {
            "id": "abc",
            "slug": "self-intro",
            "kind": "summary",
            "title": {"zh-Hans": "自我描述", "en": "About me"},
        }
    ]
    with pytest.raises(RuntimeError, match="SiteProfile"):
        _find(modules, "main", kind="about")
    found = _find(modules, "summary", kind="about")
    assert found["slug"] == "self-intro"
    assert _find(modules, "自我描述", kind="about")["id"] == "abc"


def test_resolve_repo_accepts_unique_short_name() -> None:
    class FakeApi:
        def request(self, method, path, json=None):
            assert path == "/api/owner/github/repos"
            return [
                {
                    "fullName": "kenchan6666/taiko_bot_qq",
                    "owner": "kenchan6666",
                    "name": "taiko_bot_qq",
                    "private": True,
                    "description": "",
                    "htmlUrl": "https://github.com/kenchan6666/taiko_bot_qq",
                    "defaultBranch": "main",
                }
            ]

    assert _resolve_repo(FakeApi(), "taiko_bot_qq") == (
        "kenchan6666",
        "taiko_bot_qq",
    )
    assert _resolve_repo(FakeApi(), "KENCHAN6666/Taiko_Bot_QQ") == (
        "kenchan6666",
        "taiko_bot_qq",
    )
