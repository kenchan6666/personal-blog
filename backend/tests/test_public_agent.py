from __future__ import annotations

import pytest
from app.github import HttpGitHub
from app.models import Project
from app.public_agent import (
    _chat_url,
    _is_portfolio_question,
    _limited,
    _system_prompt,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl


def project(slug: str, title: str) -> Project:
    return Project.model_construct(
        slug=slug,
        title={"zh-Hant": title, "zh-Hans": title, "en": title},
        summary={},
        body={},
        status="published",
        order=0,
        source_repo=None,
    )


def test_public_agent_uses_uniapi_v1_chat_endpoint() -> None:
    assert (
        _chat_url("https://api.uniapi.io")
        == "https://api.uniapi.io/v1/chat/completions"
    )
    assert (
        _chat_url("https://api.uniapi.io/v1")
        == "https://api.uniapi.io/v1/chat/completions"
    )


def test_topic_gate_accepts_portfolio_questions_and_project_names() -> None:
    projects = [project("personal-blog", "Personal Blog")]

    assert _is_portfolio_question("你有哪些代表项目？", projects)
    assert _is_portfolio_question("Explain Personal Blog", projects)
    assert not _is_portfolio_question("Write a sorting algorithm for me", projects)


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_configured_allowance() -> None:
    redis = FakeRedis()

    assert await _limited(redis, "visitor", 2, 60) is False
    assert await _limited(redis, "visitor", 2, 60) is False
    assert await _limited(redis, "visitor", 2, 60) is True
    assert redis.expirations["visitor"] == 60


def test_public_prompt_is_read_only_and_source_bound() -> None:
    prompt = _system_prompt("en", '{"projects":[]}')

    assert "read-only" in prompt
    assert "You have no tools" in prompt
    assert "Use only the PUBLIC_CONTEXT" in prompt


def test_github_anonymous_requests_do_not_send_empty_bearer() -> None:
    client = HttpGitHub(client_id="", client_secret="", callback_url="")

    assert "Authorization" not in client._headers("")
