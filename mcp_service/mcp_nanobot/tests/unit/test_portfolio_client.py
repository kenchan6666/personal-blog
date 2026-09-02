from __future__ import annotations

import pytest

from mcp_portfolio.server import PortfolioApi, _merge


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
