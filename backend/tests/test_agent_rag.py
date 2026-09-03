from __future__ import annotations

import httpx
import pytest

from app.agent_rag import AgentRag, knowledge_context
from app.config import Settings
from app.models import KnowledgeRecord, utc_now


def record(title: str, category: str, content: str, tags: list[str]) -> KnowledgeRecord:
    now = utc_now()
    return KnowledgeRecord.model_construct(
        id="000000000000000000000001",
        title=title,
        category=category,
        content=content,
        tags=tags,
        order=0,
        vector_synced=False,
        created_at=now,
        updated_at=now,
    )


class ScriptedClient:
    def __init__(self, responses: list[httpx.Response], timeout: float | None = None) -> None:
        self.responses = list(responses)
        self.payloads: list[dict[str, object]] = []
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs) -> httpx.Response:
        payload = kwargs.get("json")
        if isinstance(payload, dict):
            self.payloads.append(payload)
        return self.responses.pop(0)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return self.responses.pop(0)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return self.responses.pop(0)


def json_response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("POST", "https://api.uniapi.io/v1/embeddings"),
    )


@pytest.mark.asyncio
async def test_rag_falls_back_to_readable_keyword_search() -> None:
    rag = AgentRag(Settings(uni_api_key=""))
    records = [
        record("工作经历", "experience", "我使用 FastAPI 开发个人博客后端。", ["Python"]),
        record("摄影偏好", "preference", "我喜欢拍摄城市夜景。", ["摄影"]),
    ]

    matches = await rag.search("我的 Python FastAPI 经历", records)

    assert [item.title for item in matches] == ["工作经历"]
    assert "不要虚构" in knowledge_context(matches)
    clipped = knowledge_context(
        [
            record(
                "长资料",
                "other",
                "字" * 500,
                [],
            )
        ]
    )
    assert "…" in clipped
    assert clipped.count("字") < 500


@pytest.mark.asyncio
async def test_sync_reports_missing_embedding_configuration() -> None:
    rag = AgentRag(Settings(uni_api_key=""))

    synced, error = await rag.sync_with_status(
        record("技能", "skills", "FastAPI", ["Python"])
    )

    assert synced is False
    assert error == "embedding_not_configured"


@pytest.mark.asyncio
async def test_sync_classifies_channel_unavailable_after_fallbacks() -> None:
    client = ScriptedClient(
        [
            json_response(400, {"error": {"message": "当前模型无可用渠道"}}),
            json_response(400, {"error": {"message": "当前模型无可用渠道"}}),
            json_response(400, {"error": {"message": "当前模型无可用渠道"}}),
            json_response(400, {"error": {"message": "当前模型无可用渠道"}}),
        ]
    )
    rag = AgentRag(
        Settings(uni_api_key="test-key", agent_embedding_model="gemini-embedding-001"),
        client_factory=lambda **kwargs: client,
    )

    synced, error = await rag.sync_with_status(
        record("技能", "skills", "FastAPI", ["Python"])
    )

    assert synced is False
    assert error == "embedding_model_unavailable"
    assert [item.get("model") for item in client.payloads][:1] == [
        "gemini-embedding-001"
    ]
    assert len(client.payloads) == 4


@pytest.mark.asyncio
async def test_sync_uses_fallback_embedding_model_then_writes_qdrant() -> None:
    vector = [0.1, 0.2, 0.3]
    client = ScriptedClient(
        [
            json_response(400, {"error": {"message": "当前模型无可用渠道"}}),
            json_response(200, {"data": [{"embedding": vector}]}),
            json_response(404, {"status": {"error": "Not found"}}),
            json_response(200, {"result": True}),
            json_response(200, {"result": {"status": "ok"}}),
        ]
    )
    rag = AgentRag(
        Settings(uni_api_key="test-key", agent_embedding_model="gemini-embedding-001"),
        client_factory=lambda **kwargs: client,
    )

    synced, error = await rag.sync_with_status(
        record("技能", "skills", "FastAPI", ["Python"])
    )

    assert synced is True
    assert error == ""
    assert client.payloads[0]["model"] == "gemini-embedding-001"
    assert client.payloads[1]["model"] == "text-embedding-3-small"
    assert rag._resolved_model == "text-embedding-3-small"

