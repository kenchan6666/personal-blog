from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

ContentKind = Literal["project", "article", "journal", "about", "category"]
KnowledgeCategory = Literal[
    "identity",
    "experience",
    "education",
    "skills",
    "project",
    "preference",
    "other",
]

_COLLECTION_PATHS: dict[ContentKind, str] = {
    "project": "/api/owner/projects",
    "article": "/api/owner/articles",
    "journal": "/api/owner/journals",
    "about": "/api/owner/about-modules",
    "category": "/api/owner/article-categories",
}


class PortfolioApi:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "BACKEND_API_BASE_URL", "http://127.0.0.1:8000"
        ).rstrip("/")
        self.token = os.getenv("PORTFOLIO_SERVICE_TOKEN", "").strip()
        self.write_enabled = os.getenv(
            "PORTFOLIO_WRITE_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if not self.token:
            raise RuntimeError("PORTFOLIO_SERVICE_TOKEN is not configured")
        response = httpx.request(
            method,
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            json=json,
            timeout=45.0,
        )
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = str(response.json().get("detail") or detail)
            except (ValueError, AttributeError):
                detail = response.text
            raise RuntimeError(f"Portfolio API {response.status_code}: {detail[:300]}")
        return response.json() if response.content else None

    def require_write(self) -> None:
        if not self.write_enabled:
            raise RuntimeError("Portfolio writes are disabled")


def _merge(current: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _find(items: list[dict[str, Any]], identifier: str) -> dict[str, Any]:
    wanted = identifier.strip().lower().strip("/")
    for item in items:
        if str(item.get("id", "")) == identifier:
            return item
        if str(item.get("slug", "")).lower().strip("/") == wanted:
            return item
    raise RuntimeError(f"Content not found: {identifier}")


def _repo_parts(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.strip().strip("/").split("/") if part]
    if len(parts) != 2:
        raise RuntimeError("full_name must be owner/name")
    return parts[0], parts[1]


def _github_snapshot(api: PortfolioApi) -> dict[str, Any]:
    try:
        items = api.request("GET", "/api/owner/github/repos")
    except RuntimeError as exc:
        detail = str(exc)
        if "409" in detail or "github_not_connected" in detail:
            return {
                "connected": False,
                "repos": [],
                "hint": "Connect GitHub in the admin GitHub tab, then ask again.",
            }
        return {"connected": False, "repos": [], "error": detail[:200]}
    return {
        "connected": True,
        "repos": [
            {
                "fullName": item.get("fullName"),
                "private": item.get("private"),
                "description": item.get("description"),
                "htmlUrl": item.get("htmlUrl"),
                "defaultBranch": item.get("defaultBranch"),
            }
            for item in items
        ],
    }


def create_server() -> FastMCP:
    server = FastMCP("portfolio")
    api = PortfolioApi()

    @server.tool()
    def portfolio_overview() -> dict[str, Any]:
        """Read the complete owner-visible site overview, including drafts and comments."""
        return {
            "site": api.request("GET", "/api/owner/site"),
            "projects": api.request("GET", "/api/owner/projects"),
            "articles": api.request("GET", "/api/owner/articles"),
            "articleCategories": api.request("GET", "/api/owner/article-categories"),
            "journals": api.request("GET", "/api/owner/journals"),
            "about": api.request("GET", "/api/owner/about-modules"),
            "comments": api.request("GET", "/api/owner/comments"),
            "github": _github_snapshot(api),
        }

    @server.tool()
    def portfolio_get_site() -> dict[str, Any]:
        """Read all editable profile, hero, page-lead, skill, experience and link fields."""
        return api.request("GET", "/api/owner/site")

    @server.tool()
    def portfolio_list_content(
        kind: ContentKind,
        query: str = "",
        status: Literal["draft", "published", "all"] = "all",
        limit: int = 50,
    ) -> dict[str, Any]:
        """List owner-visible projects, articles, journals, About modules or article categories."""
        items = api.request("GET", _COLLECTION_PATHS[kind])
        query_lower = query.strip().lower()
        if status != "all":
            items = [item for item in items if item.get("status") == status]
        if query_lower:
            items = [
                item
                for item in items
                if query_lower
                in (
                    str(item.get("slug", ""))
                    + " "
                    + " ".join(str(v) for v in item.get("title", {}).values())
                ).lower()
            ]
        return {"items": items[: max(1, min(limit, 200))], "total": len(items)}

    @server.tool()
    def portfolio_get_content(kind: ContentKind, identifier: str) -> dict[str, Any]:
        """Get one content record by id or slug, including every language and draft field."""
        items = api.request("GET", _COLLECTION_PATHS[kind])
        return _find(items, identifier)

    @server.tool()
    def portfolio_create_content(
        kind: ContentKind,
        slug: str,
        title: dict[str, str],
        summary: dict[str, str] | None = None,
        body: dict[str, str] | None = None,
        order: int = 0,
        related_project_slug: str = "",
        category_slug: str = "",
        about_kind: str = "custom",
    ) -> dict[str, Any]:
        """Create a content record or category. Content records are always created as Draft."""
        api.require_write()
        payload: dict[str, Any] = {
            "slug": slug,
            "title": title,
            "body": body or {},
            "status": "draft",
            "order": order,
        }
        if kind in {"project", "article", "journal"}:
            payload["summary"] = summary or {}
        if kind == "article":
            payload["relatedProjectSlug"] = related_project_slug
            payload["categorySlug"] = category_slug
        if kind == "about":
            payload["kind"] = about_kind
        if kind == "category":
            payload = {"slug": slug, "title": title, "order": order}
        return api.request("POST", _COLLECTION_PATHS[kind], json=payload)

    @server.tool()
    def portfolio_update_content(
        kind: ContentKind,
        identifier: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Update editable fields on an existing record. Read current data first and preserve omitted fields."""
        api.require_write()
        if "id" in changes or "sourceRepo" in changes:
            raise RuntimeError("id and sourceRepo cannot be changed with this tool")
        items = api.request("GET", _COLLECTION_PATHS[kind])
        current = _find(items, identifier)
        item_id = str(current["id"])
        payload = _merge(current, changes)
        payload.pop("id", None)
        payload.pop("sourceRepo", None)
        payload.pop("protected", None)
        return api.request(
            "PUT", f"{_COLLECTION_PATHS[kind]}/{item_id}", json=payload
        )

    @server.tool()
    def portfolio_update_site(changes: dict[str, Any]) -> dict[str, Any]:
        """Update selected site/profile fields while preserving all omitted fields."""
        api.require_write()
        current = api.request("GET", "/api/owner/site")
        payload = _merge(current, changes)
        payload.pop("avatarUrl", None)
        payload.pop("heroVisualUrl", None)
        return api.request("PUT", "/api/owner/site", json=payload)

    @server.tool()
    def portfolio_list_comments(
        status: Literal["pending", "approved", "rejected", "all"] = "all",
        target_type: Literal["article", "journal", "all"] = "all",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Read owner-visible comments, including email, moderation status and owner reply."""
        items = api.request("GET", "/api/owner/comments")
        if status != "all":
            items = [item for item in items if item.get("status") == status]
        if target_type != "all":
            items = [item for item in items if item.get("targetType") == target_type]
        return {"items": items[: max(1, min(limit, 200))], "total": len(items)}

    @server.tool()
    def portfolio_list_knowledge() -> dict[str, Any]:
        """Read the Owner's modular About Me knowledge records used for RAG."""
        items = api.request("GET", "/api/owner/agent/knowledge")
        return {"items": items, "total": len(items)}

    @server.tool()
    def portfolio_remember_knowledge(
        title: str,
        category: KnowledgeCategory,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save a personal fact or experience after the Owner explicitly asks to remember it."""
        api.require_write()
        return api.request(
            "POST",
            "/api/owner/agent/knowledge",
            json={
                "title": title,
                "category": category,
                "content": content,
                "tags": tags or [],
                "order": 0,
            },
        )

    @server.tool()
    def portfolio_update_knowledge(
        record_id: str,
        title: str,
        category: KnowledgeCategory,
        content: str,
        tags: list[str] | None = None,
        order: int = 0,
    ) -> dict[str, Any]:
        """Update one About Me record after the Owner identifies the record and desired change."""
        api.require_write()
        return api.request(
            "PUT",
            f"/api/owner/agent/knowledge/{record_id}",
            json={
                "title": title,
                "category": category,
                "content": content,
                "tags": tags or [],
                "order": order,
            },
        )

    @server.tool()
    def portfolio_list_github_repos() -> dict[str, Any]:
        """List every GitHub repository the Owner has authorized, including private ones."""
        snapshot = _github_snapshot(api)
        repos = snapshot.get("repos") or []
        return {**snapshot, "items": repos, "total": len(repos)}

    @server.tool()
    def portfolio_get_github_source(
        full_name: str,
        ref: str = "",
        path: str = "",
    ) -> dict[str, Any]:
        """Read README/tree for any authorized GitHub repo by owner/name. Binding a Project is not required."""
        owner, name = _repo_parts(full_name)
        suffix = "/tree" if path else ""
        params = httpx.QueryParams({"ref": ref, "path": path})
        return api.request(
            "GET",
            f"/api/owner/github/repos/{quote(owner, safe='')}/{quote(name, safe='')}{suffix}?{params}",
        )

    @server.tool()
    def portfolio_get_github_file(
        full_name: str,
        path: str,
        ref: str = "",
    ) -> dict[str, Any]:
        """Read one file from any authorized GitHub repo, including private repositories."""
        owner, name = _repo_parts(full_name)
        params = httpx.QueryParams({"ref": ref, "path": path})
        return api.request(
            "GET",
            f"/api/owner/github/repos/{quote(owner, safe='')}/{quote(name, safe='')}/blob?{params}",
        )

    @server.tool()
    def portfolio_get_project_source(
        project_slug: str,
        ref: str = "",
        path: str = "",
    ) -> dict[str, Any]:
        """Read a bound SourceRepo overview or directory. Private repos are allowed here."""
        suffix = "/source"
        if path:
            suffix += "/tree"
        params = httpx.QueryParams({"ref": ref, "path": path})
        slug = quote(project_slug.strip(), safe="")
        return api.request(
            "GET",
            f"/api/owner/projects/{slug}{suffix}?{params}",
        )

    @server.tool()
    def portfolio_get_source_file(
        project_slug: str,
        path: str,
        ref: str = "",
    ) -> dict[str, Any]:
        """Read one file from a bound SourceRepo, including private repositories."""
        params = httpx.QueryParams({"ref": ref, "path": path})
        slug = quote(project_slug.strip(), safe="")
        return api.request(
            "GET",
            f"/api/owner/projects/{slug}/source/blob?{params}",
        )

    @server.tool()
    def portfolio_comment_action(
        comment_id: str,
        action: Literal["approve", "reject", "reply"],
        reply_body: str = "",
    ) -> dict[str, Any]:
        """Moderate or reply to a comment only after the Owner explicitly requests that action."""
        api.require_write()
        path = f"/api/owner/comments/{comment_id}/{action}"
        payload = {"body": reply_body} if action == "reply" else None
        return api.request("POST", path, json=payload)

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
