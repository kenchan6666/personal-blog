from __future__ import annotations

import pytest

from mcp_portfolio.server import (
    PortfolioApi,
    _clip_text,
    _merge,
    _repo_parts,
    _resolve_repo,
    _without_publish,
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


def test_update_payload_cannot_publish() -> None:
    assert _without_publish({"status": "published", "title": "A"})["status"] == "draft"
    assert _without_publish({"status": "draft"})["status"] == "draft"


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
