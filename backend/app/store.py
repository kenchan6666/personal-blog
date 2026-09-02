from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from beanie import PydanticObjectId
from bson import ObjectId
from pydantic import TypeAdapter

from app.models import Article, ArticleCategory, Comment, Journal, Project, SiteProfile

DocumentModel = TypeVar("DocumentModel")
MODELS = (SiteProfile, Project, ArticleCategory, Article, Journal, Comment)

_STORE: "Store | None" = None


def bind_store(store: "Store | None") -> None:
    global _STORE
    _STORE = store


def current_store() -> "Store":
    if _STORE is None:
        raise RuntimeError("store is not bound")
    return _STORE


def collection_name(model: type[Any]) -> str:
    return model.Settings.name


def new_document(model: type[DocumentModel], **data: Any) -> DocumentModel:
    """Build a document without requiring a live Mongo collection."""
    store = _STORE
    if store is not None and store.kind == "local":
        return _construct_document(model, data)
    return model(**data)


def _construct_document(
    model: type[DocumentModel], data: dict[str, Any]
) -> DocumentModel:
    payload = dict(data)
    doc_id = payload.pop("id", None)
    payload.pop("revision_id", None)
    coerced: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        if name not in payload:
            continue
        coerced[name] = TypeAdapter(field.annotation).validate_python(payload[name])
    doc = model.model_construct(**coerced)
    if doc_id:
        doc.id = PydanticObjectId(str(doc_id))
    return doc


class Store:
    kind: str

    async def find_one(self, model: type[DocumentModel], **filters: Any) -> DocumentModel | None:
        raise NotImplementedError

    async def find(self, model: type[DocumentModel], **filters: Any) -> list[DocumentModel]:
        raise NotImplementedError

    async def find_all(self, model: type[DocumentModel]) -> list[DocumentModel]:
        return await self.find(model)

    async def get(self, model: type[DocumentModel], doc_id: Any) -> DocumentModel | None:
        return await self.find_one(model, id=str(doc_id))

    async def insert(self, doc: DocumentModel) -> DocumentModel:
        raise NotImplementedError

    async def save(self, doc: DocumentModel) -> DocumentModel:
        raise NotImplementedError

    async def delete(self, doc: DocumentModel) -> None:
        raise NotImplementedError

    async def delete_all(self) -> None:
        raise NotImplementedError


class MongoStore(Store):
    kind = "mongo"

    async def find_one(self, model: type[DocumentModel], **filters: Any) -> DocumentModel | None:
        return await model.find_one(*_beanie_eq(model, filters))

    async def find(self, model: type[DocumentModel], **filters: Any) -> list[DocumentModel]:
        return await model.find(*_beanie_eq(model, filters)).to_list()

    async def find_all(self, model: type[DocumentModel]) -> list[DocumentModel]:
        return await model.find_all().to_list()

    async def get(self, model: type[DocumentModel], doc_id: Any) -> DocumentModel | None:
        return await model.get(doc_id)

    async def insert(self, doc: DocumentModel) -> DocumentModel:
        await doc.insert()
        return doc

    async def save(self, doc: DocumentModel) -> DocumentModel:
        await doc.save()
        return doc

    async def delete(self, doc: DocumentModel) -> None:
        await doc.delete()

    async def delete_all(self) -> None:
        for model in MODELS:
            await model.delete_all()


class LocalStore(Store):
    kind = "local"

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._tables: dict[str, list[dict[str, Any]]] = {
            collection_name(model): self._read(collection_name(model))
            for model in MODELS
        }

    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def _read(self, name: str) -> list[dict[str, Any]]:
        path = self._path(name)
        if not path.is_file():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []

    def _write(self, name: str) -> None:
        path = self._path(name)
        path.write_text(
            json.dumps(self._tables[name], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _hydrate(self, model: type[DocumentModel], row: dict[str, Any]) -> DocumentModel:
        return _construct_document(model, row)

    def _dump(self, doc: Any) -> dict[str, Any]:
        if getattr(doc, "id", None) is None:
            doc.id = PydanticObjectId(str(ObjectId()))
        payload = doc.model_dump(mode="json")
        payload["id"] = str(doc.id)
        return payload

    def _match(self, row: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            actual = row.get("id") if key == "id" else row.get(key)
            if key == "id":
                if str(actual) != str(expected):
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, model: type[DocumentModel], **filters: Any) -> DocumentModel | None:
        name = collection_name(model)
        for row in self._tables[name]:
            if self._match(row, filters):
                return self._hydrate(model, row)
        return None

    async def find(self, model: type[DocumentModel], **filters: Any) -> list[DocumentModel]:
        name = collection_name(model)
        return [
            self._hydrate(model, row)
            for row in self._tables[name]
            if self._match(row, filters)
        ]

    async def insert(self, doc: DocumentModel) -> DocumentModel:
        name = collection_name(type(doc))
        row = self._dump(doc)
        self._tables[name].append(row)
        self._write(name)
        return doc

    async def save(self, doc: DocumentModel) -> DocumentModel:
        name = collection_name(type(doc))
        row = self._dump(doc)
        rows = self._tables[name]
        for index, existing in enumerate(rows):
            if existing.get("id") == row["id"]:
                rows[index] = row
                self._write(name)
                return doc
        rows.append(row)
        self._write(name)
        return doc

    async def delete(self, doc: DocumentModel) -> None:
        name = collection_name(type(doc))
        doc_id = str(doc.id)
        self._tables[name] = [row for row in self._tables[name] if row.get("id") != doc_id]
        self._write(name)

    async def delete_all(self) -> None:
        for model in MODELS:
            name = collection_name(model)
            self._tables[name] = []
            self._write(name)


def _beanie_eq(model: type[Any], filters: dict[str, Any]) -> list[Any]:
    return [getattr(model, key) == value for key, value in filters.items()]


def build_store(mongo_uri: str, local_data_dir: str) -> Store:
    if mongo_uri.strip():
        return MongoStore()
    return LocalStore(local_data_dir)
