from __future__ import annotations

import pytest

from app.github import HttpGitHub
from app.models import Project
from app.public_agent import (
    _chat_url,
    _is_portfolio_question,
    _limited,
    _system_prompt,
    guide_chat_payloads,
    looks_incomplete_guide,
    parse_guide_sse_block,
    public_guide_max_tokens,
    should_continue_guide,
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
    assert _is_portfolio_question("他适合后端岗位吗？", projects)
    assert not _is_portfolio_question("Write a sorting algorithm for me", projects)


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_configured_allowance() -> None:
    redis = FakeRedis()

    assert await _limited(redis, "visitor", 2, 60) is False
    assert await _limited(redis, "visitor", 2, 60) is False
    assert await _limited(redis, "visitor", 2, 60) is True
    assert redis.expirations["visitor"] == 60


def test_public_prompt_stays_source_bound_without_lecturing() -> None:
    prompt = _system_prompt("en", '{"projects":[]}')

    assert "You have no tools" in prompt
    assert "Use only PUBLIC_CONTEXT" in prompt
    assert "Do not mention being a guide" in prompt
    assert "Finish every sentence" in prompt or "finish every sentence" in prompt
    assert "220 Chinese" not in prompt
    assert "read-only public portfolio guide" not in prompt
    assert "Private GitHub repositories are out of scope" not in prompt


def test_public_prompt_is_hiring_aware_without_pitching() -> None:
    prompt = _system_prompt("en", '{"projects":[]}')

    assert "Do not sell" in prompt
    assert "colleague" in prompt
    assert "direct answer" in prompt
    assert "Talk about Ken, not about yourself" in prompt
    assert "missing detail is not a weakness" in prompt
    assert "Two short sentences at most" in prompt
    assert "Do not change the subject" in prompt
    assert "Stop when the question is answered" in prompt
    assert "2–5 named facts" not in prompt
    assert "redirect to evidenced strengths" not in prompt
    assert "credible candidate" not in prompt
    assert "Journals only when asked" in prompt


def test_public_guide_floor_stops_mid_sentence_truncation() -> None:
    assert public_guide_max_tokens(350) == 4096
    assert public_guide_max_tokens(1024) == 4096
    assert public_guide_max_tokens(8192) == 8192


def test_guide_continues_when_model_hits_length_or_mid_clause() -> None:
    assert should_continue_guide("length", "完整的一句。")
    assert should_continue_guide("max_tokens", "完整的一句。")
    assert should_continue_guide("stop", "")
    assert should_continue_guide(
        "stop",
        "Ken 的代表项目是 Personal Blog，技术栈包括 FastAPI 和",
    )
    assert not should_continue_guide(
        "stop",
        "详见 [项目](/zh-Hant/projects/personal-blog)。",
    )
    assert looks_incomplete_guide("他主要使用 Next.js 与")
    assert looks_incomplete_guide("他擅长")
    delta, reason = parse_guide_sse_block(
        'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":"length"}]}'
    )
    assert delta == "Hi"
    assert reason == "length"
    parts, parts_reason = parse_guide_sse_block(
        'data: {"choices":[{"delta":{"content":[{"type":"text","text":"完"}]},'
        '"finish_reason":"max_tokens"}]}'
    )
    assert parts == "完"
    assert parts_reason == "max_tokens"
    payloads = guide_chat_payloads("gemini-2.5-flash", [], 4096)
    assert payloads[0]["thinking_budget"] == 0
    assert "thinking_budget" not in payloads[1]


def test_github_anonymous_requests_do_not_send_empty_bearer() -> None:
    client = HttpGitHub(client_id="", client_secret="", callback_url="")

    assert "Authorization" not in client._headers("")
