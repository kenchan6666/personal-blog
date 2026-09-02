from __future__ import annotations

import pytest
from app.agent_rag import AgentRag, knowledge_context
from app.config import Settings
from app.models import KnowledgeRecord, utc_now


def record(title: str, category: str, content: str, tags: list[str]) -> KnowledgeRecord:
    now = utc_now()
    return KnowledgeRecord.model_construct(
        title=title,
        category=category,
        content=content,
        tags=tags,
        order=0,
        vector_synced=False,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_rag_falls_back_to_readable_keyword_search() -> None:
    rag = AgentRag(Settings(uni_api_key=""))
    records = [
        record("工作经历", "experience", "我使用 FastAPI 开发个人博客后端。", ["Python"]),
        record("摄影偏好", "preference", "我喜欢拍摄城市夜景。", ["摄影"]),
    ]

    matches = await rag.search("我的 Python FastAPI 经历", records)

    assert [record.title for record in matches] == ["工作经历"]
    assert "不要虚构" in knowledge_context(matches)


@pytest.mark.asyncio
async def test_sync_reports_missing_embedding_configuration() -> None:
    rag = AgentRag(Settings(uni_api_key=""))

    synced, error = await rag.sync_with_status(
        record("技能", "skills", "FastAPI", ["Python"])
    )

    assert synced is False
    assert error == "embedding_not_configured"
