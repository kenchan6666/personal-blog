from __future__ import annotations

import re
import uuid
from collections.abc import Callable

import httpx

from app.config import Settings
from app.models import KnowledgeRecord

_EMBEDDING_FALLBACKS = (
    "text-embedding-3-small",
    "gemini-embedding-001",
    "text-embedding-004",
    "jina-embeddings-v3",
)


class EmbeddingError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AgentRag:
    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self.settings = settings
        self._client_factory = client_factory or httpx.AsyncClient
        self._resolved_model = ""

    def _embedding_url(self) -> str:
        base = self.settings.uni_api_base.rstrip("/")
        return f"{base}/embeddings" if base.endswith("/v1") else f"{base}/v1/embeddings"

    def _models_to_try(self) -> list[str]:
        preferred = self._resolved_model or self.settings.agent_embedding_model
        ordered: list[str] = []
        for model in (preferred, *_EMBEDDING_FALLBACKS):
            name = model.strip()
            if name and name not in ordered:
                ordered.append(name)
        return ordered

    def _point_id(self, record_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"portfolio-knowledge:{record_id}"))

    def _parse_vector(self, payload: object) -> list[float] | None:
        embedding: object = None
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    embedding = first.get("embedding")
            if embedding is None:
                embedding = payload.get("embedding")
        if isinstance(embedding, dict):
            embedding = embedding.get("values")
        if not isinstance(embedding, list) or not embedding:
            return None
        try:
            return [float(value) for value in embedding]
        except (TypeError, ValueError):
            return None

    def _embed_error_code(self, response: httpx.Response) -> str:
        if response.status_code in {401, 403}:
            return "embedding_unauthorized"
        body = response.text.casefold()
        if any(
            marker in body
            for marker in (
                "无可用渠道",
                "無可用渠道",
                "model",
                "not found",
                "does not exist",
                "unknown",
            )
        ):
            return "embedding_model_unavailable"
        return "embedding_unavailable"

    async def _embed(self, text: str) -> list[float]:
        if not self.settings.uni_api_key.strip():
            raise EmbeddingError("embedding_not_configured")
        last_code = "embedding_unavailable"
        async with self._client_factory(timeout=30.0) as client:
            for model in self._models_to_try():
                try:
                    response = await client.post(
                        self._embedding_url(),
                        headers={
                            "Authorization": f"Bearer {self.settings.uni_api_key}"
                        },
                        json={"model": model, "input": text},
                    )
                except httpx.HTTPError as exc:
                    last_code = "embedding_unavailable"
                    raise EmbeddingError(last_code) from exc
                if response.status_code >= 400:
                    last_code = self._embed_error_code(response)
                    if last_code == "embedding_unauthorized":
                        raise EmbeddingError(last_code)
                    continue
                vector = self._parse_vector(response.json())
                if vector is None:
                    last_code = "embedding_invalid_response"
                    continue
                self._resolved_model = model
                return vector
        raise EmbeddingError(last_code)

    async def sync(self, record: KnowledgeRecord) -> bool:
        synced, _ = await self.sync_with_status(record)
        return synced

    async def sync_with_status(
        self,
        record: KnowledgeRecord,
    ) -> tuple[bool, str]:
        try:
            vector = await self._embed(f"{record.title}\n{record.content}")
        except EmbeddingError as exc:
            return False, exc.code

        try:
            collection_url = (
                f"{self.settings.qdrant_url.rstrip('/')}/collections/"
                f"{self.settings.qdrant_collection}"
            )
            async with self._client_factory(timeout=15.0) as client:
                exists = await client.get(collection_url)
                if exists.status_code == 404:
                    created = await client.put(
                        collection_url,
                        json={
                            "vectors": {
                                "size": len(vector),
                                "distance": "Cosine",
                            }
                        },
                    )
                    created.raise_for_status()
                else:
                    exists.raise_for_status()
                response = await client.put(
                    f"{collection_url}/points?wait=true",
                    json={
                        "points": [
                            {
                                "id": self._point_id(str(record.id)),
                                "vector": vector,
                                "payload": {
                                    "record_id": str(record.id),
                                    "title": record.title,
                                    "category": record.category,
                                    "content": record.content,
                                    "tags": record.tags,
                                },
                            }
                        ]
                    },
                )
                response.raise_for_status()
            return True, ""
        except httpx.HTTPStatusError as exc:
            if "dimension" in exc.response.text.casefold():
                return False, "vector_dimension_mismatch"
            return False, "vector_store_rejected"
        except httpx.HTTPError:
            return False, "vector_store_unavailable"

    async def delete(self, record_id: str) -> None:
        try:
            url = (
                f"{self.settings.qdrant_url.rstrip('/')}/collections/"
                f"{self.settings.qdrant_collection}/points/delete?wait=true"
            )
            async with self._client_factory(timeout=10.0) as client:
                await client.post(
                    url,
                    json={"points": [self._point_id(record_id)]},
                )
        except httpx.HTTPError:
            return

    async def reset_collection(self) -> bool:
        url = (
            f"{self.settings.qdrant_url.rstrip('/')}/collections/"
            f"{self.settings.qdrant_collection}"
        )
        try:
            async with self._client_factory(timeout=15.0) as client:
                response = await client.delete(url)
            if response.status_code not in {200, 404}:
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def search(
        self,
        query: str,
        records: list[KnowledgeRecord],
        limit: int = 5,
    ) -> list[KnowledgeRecord]:
        if not any(record.vector_synced for record in records):
            return self._lexical_search(query, records, limit)
        by_id = {str(record.id): record for record in records}
        try:
            vector = await self._embed(query)
            url = (
                f"{self.settings.qdrant_url.rstrip('/')}/collections/"
                f"{self.settings.qdrant_collection}/points/search"
            )
            async with self._client_factory(timeout=15.0) as client:
                response = await client.post(
                    url,
                    json={
                        "vector": vector,
                        "limit": limit,
                        "with_payload": True,
                    },
                )
                response.raise_for_status()
            matches: list[KnowledgeRecord] = []
            for point in response.json().get("result", []):
                record = by_id.get(str(point.get("payload", {}).get("record_id", "")))
                if record is not None:
                    matches.append(record)
            if matches:
                return matches
        except (httpx.HTTPError, EmbeddingError, KeyError, TypeError, ValueError):
            pass
        return self._lexical_search(query, records, limit)

    def _lexical_search(
        self,
        query: str,
        records: list[KnowledgeRecord],
        limit: int,
    ) -> list[KnowledgeRecord]:
        terms = {
            term.lower()
            for term in re.findall(r"[\w\u3400-\u9fff]+", query)
            if len(term) > 1
        }
        scored: list[tuple[int, KnowledgeRecord]] = []
        for record in records:
            haystack = " ".join(
                [record.title, record.category, record.content, *record.tags]
            ).lower()
            score = sum(
                3 if term in record.title.lower() else 1
                for term in terms
                if term in haystack
            )
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        return [record for _, record in scored[:limit]]


def knowledge_context(records: list[KnowledgeRecord]) -> str:
    if not records:
        return ""
    rows = [
        f"### {record.title}（{record.category}）\n{record.content}"
        for record in records
    ]
    return (
        "\n\n以下是“关于我”知识库中与本次问题最相关的资料。"
        "只在确实相关时使用，不要虚构未提供的信息：\n\n"
        + "\n\n".join(rows)
    )
