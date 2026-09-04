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


def _next_knowledge_order(api: PortfolioApi) -> int:
    items = api.request("GET", "/api/owner/agent/knowledge") or []
    orders = [int(item.get("order") or 0) for item in items if isinstance(item, dict)]
    return (max(orders) if orders else 0) + 1


def _guard_status_on_update(
    current: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    current_status = str(current.get("status") or "draft")
    next_status = str(payload.get("status") or current_status)
    if next_status == "published" and current_status != "published":
        raise RuntimeError(
            "Cannot publish with portfolio_update_content. "
            "Call portfolio_publish_content after the Owner explicitly asks to publish."
        )
    return payload


def _publish_path(kind: ContentKind, item_id: str) -> str:
    if kind == "category":
        raise RuntimeError(
            "Categories have no draft/published status. "
            "portfolio_publish_content is for project, article, journal, and about."
        )
    return f"{_COLLECTION_PATHS[kind]}/{item_id}/publish"


_HOMEPAGE_ALIASES = frozenset(
    {
        "main",
        "home",
        "homepage",
        "index",
        "hero",
        "首页",
        "首頁",
        "主页",
        "主頁",
    }
)


def _known_labels(items: list[dict[str, Any]]) -> str:
    labels: list[str] = []
    for item in items[:12]:
        slug = str(item.get("slug") or item.get("id") or "")
        kind = str(item.get("kind") or "")
        labels.append(f"{slug} ({kind})" if kind else slug)
    return ", ".join(labels) or "(none)"


def _title_values(item: dict[str, Any]) -> list[str]:
    title = item.get("title")
    if isinstance(title, dict):
        return [str(value).strip() for value in title.values() if value]
    if isinstance(title, str) and title.strip():
        return [title.strip()]
    return []


def _find(
    items: list[dict[str, Any]],
    identifier: str,
    *,
    kind: str = "",
) -> dict[str, Any]:
    wanted = identifier.strip().lower().strip("/")
    if kind == "about" and wanted in _HOMEPAGE_ALIASES:
        raise RuntimeError(
            "Homepage `/` is SiteProfile, not an About module. "
            "Call portfolio_get_site / portfolio_update_site. "
            "About `/about` is a list of modules "
            "(summary, education, experience, achievement, custom); "
            "list them with portfolio_list_content kind=about. "
            f"There is no About page named {identifier}."
        )

    def matches(item: dict[str, Any], field: str) -> bool:
        if field == "id":
            return str(item.get("id", "")) == identifier
        if field == "slug":
            return str(item.get("slug", "")).lower().strip("/") == wanted
        if field == "kind":
            return str(item.get("kind", "")).lower() == wanted
        if field == "title":
            return any(value.lower() == wanted for value in _title_values(item))
        return False

    for field in ("id", "slug", "kind", "title"):
        hits = [item for item in items if matches(item, field)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise RuntimeError(
                f"Ambiguous {kind or 'content'} {identifier}. "
                f"Matches: {_known_labels(hits)}"
            )
    raise RuntimeError(
        f"Content not found: {identifier}. Known: {_known_labels(items)}"
    )


_SOURCE_CLIP = 8000


def _clip_text(value: str, limit: int = _SOURCE_CLIP) -> str:
    text = value or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[truncated]"


def _clip_source_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    clipped = dict(payload)
    readme = clipped.get("readme")
    if isinstance(readme, dict) and isinstance(readme.get("content"), str):
        clipped["readme"] = {**readme, "content": _clip_text(str(readme["content"]))}
    if isinstance(clipped.get("content"), str):
        clipped["content"] = _clip_text(str(clipped["content"]))
    return clipped


def _repo_parts(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.strip().strip("/").split("/") if part]
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return "", parts[0]
    raise RuntimeError("full_name must be owner/name or a repository name")


def _resolve_repo(api: PortfolioApi, full_name: str) -> tuple[str, str]:
    owner, name = _repo_parts(full_name)
    snapshot = _github_snapshot(api)
    if not snapshot.get("connected"):
        raise RuntimeError(
            snapshot.get("hint") or "GitHub is not connected. Open the admin GitHub tab."
        )
    wanted = f"{owner}/{name}".strip("/") if owner else name
    full_hits: list[str] = []
    name_hits: list[str] = []
    for item in snapshot.get("repos") or []:
        item_full = str(item.get("fullName") or "")
        item_name = item_full.rsplit("/", 1)[-1]
        if item_full.casefold() == wanted.casefold():
            full_hits.append(item_full)
        if item_name.casefold() == name.casefold():
            name_hits.append(item_full)
    unique = list(dict.fromkeys(full_hits or name_hits))
    if len(unique) != 1:
        known = ", ".join(
            str(item.get("fullName")) for item in (snapshot.get("repos") or [])[:12]
        )
        raise RuntimeError(
            f"Repository not found: {full_name}. Authorized repos: {known or '(none)'}"
        )
    owner_name, repo_name = unique[0].split("/", 1)
    return owner_name, repo_name


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
                "owner": item.get("owner") or str(item.get("fullName") or "").split("/", 1)[0],
                "name": item.get("name")
                or str(item.get("fullName") or "").rsplit("/", 1)[-1],
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
        """Read the owner-visible site: homepage SiteProfile, About modules, drafts and comments."""
        return {
            "surfaces": {
                "homepage": {
                    "route": "/",
                    "tools": ["portfolio_get_site", "portfolio_update_site"],
                    "fields": [
                        "heroHeadline",
                        "heroSupport",
                        "bio",
                        "skills",
                        "experience",
                        "links",
                        "aboutLead",
                    ],
                },
                "about": {
                    "route": "/about",
                    "tools": ["portfolio_list_content kind=about"],
                    "note": (
                        "About is modules (summary, education, experience, "
                        "achievement, custom), not a page named main."
                    ),
                },
                "resume": {
                    "route": "/resume",
                    "tools": [
                        "portfolio_list_resume_templates",
                        "portfolio_list_resumes",
                        "portfolio_create_resume",
                        "portfolio_generate_resume",
                        "portfolio_publish_resume",
                    ],
                    "note": (
                        "Resume is a one-language CV document plus a ResumeTemplate. "
                        "It is not About and not a SiteProfile link."
                    ),
                },
            },
            "site": api.request("GET", "/api/owner/site"),
            "projects": api.request("GET", "/api/owner/projects"),
            "articles": api.request("GET", "/api/owner/articles"),
            "articleCategories": api.request("GET", "/api/owner/article-categories"),
            "journals": api.request("GET", "/api/owner/journals"),
            "about": api.request("GET", "/api/owner/about-modules"),
            "resumeTemplates": api.request("GET", "/api/owner/resume-templates"),
            "resumes": api.request("GET", "/api/owner/resumes"),
            "comments": api.request("GET", "/api/owner/comments"),
            "github": _github_snapshot(api),
        }

    @server.tool()
    def portfolio_get_site() -> dict[str, Any]:
        """Read homepage `/` SiteProfile: hero, bio, skills, experience, links, page leads. Not About; there is no page named main."""
        return api.request("GET", "/api/owner/site")

    @server.tool()
    def portfolio_list_content(
        kind: ContentKind,
        query: str = "",
        status: Literal["draft", "published", "all"] = "all",
        limit: int = 50,
    ) -> dict[str, Any]:
        """List projects, articles, journals, About modules (`kind=about` is `/about`, not the homepage), or article categories."""
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
        """Get one record by id, slug, About kind, or title. About identifier is never `main`; homepage is portfolio_get_site."""
        items = api.request("GET", _COLLECTION_PATHS[kind])
        return _find(items, identifier, kind=kind)

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
        current = _find(items, identifier, kind=kind)
        item_id = str(current["id"])
        payload = _merge(current, changes)
        payload.pop("id", None)
        payload.pop("sourceRepo", None)
        payload.pop("protected", None)
        payload = _guard_status_on_update(current, payload)
        return api.request(
            "PUT", f"{_COLLECTION_PATHS[kind]}/{item_id}", json=payload
        )

    @server.tool()
    def portfolio_publish_content(kind: ContentKind, identifier: str) -> dict[str, Any]:
        """Publish a Draft record. Only after the Owner explicitly asks to publish. Not for category or homepage SiteProfile."""
        api.require_write()
        items = api.request("GET", _COLLECTION_PATHS[kind])
        current = _find(items, identifier, kind=kind)
        return api.request("POST", _publish_path(kind, str(current["id"])))

    @server.tool()
    def portfolio_update_site(changes: dict[str, Any]) -> dict[str, Any]:
        """Update homepage `/` SiteProfile. Use for 首页, Hero, 简介, 技能, 经历条. Pass only changed fields. About modules use update_content kind=about."""
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
        """Save a confirmed personal fact. Used in the same turn as a site write; do not invent facts."""
        api.require_write()
        return api.request(
            "POST",
            "/api/owner/agent/knowledge",
            json={
                "title": title,
                "category": category,
                "content": content,
                "tags": tags or [],
                "order": _next_knowledge_order(api),
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
        """Update one About Me record with confirmed facts after listing knowledge."""
        api.require_write()
        return api.request(
            "PUT",
            f"/api/owner/agent/knowledge/{record_id}",
            json={
                "title": title,
                "category": category,
                "content": content,
                "tags": tags or [],
                "order": _next_knowledge_order(api),
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
        """Read README and file tree. Accepts owner/name or a unique repo name such as taiko_bot_qq."""
        owner, name = _resolve_repo(api, full_name)
        suffix = "/tree" if path else ""
        params = httpx.QueryParams({"ref": ref, "path": path})
        return _clip_source_payload(
            api.request(
                "GET",
                f"/api/owner/github/repos/{quote(owner, safe='')}/{quote(name, safe='')}{suffix}?{params}",
            )
        )

    @server.tool()
    def portfolio_get_github_file(
        full_name: str,
        path: str,
        ref: str = "",
    ) -> dict[str, Any]:
        """Read one file. Prefer this for README.md; the name is matched case-insensitively."""
        owner, name = _resolve_repo(api, full_name)
        params = httpx.QueryParams({"ref": ref, "path": path})
        return _clip_source_payload(
            api.request(
                "GET",
                f"/api/owner/github/repos/{quote(owner, safe='')}/{quote(name, safe='')}/blob?{params}",
            )
        )

    @server.tool()
    def portfolio_get_project_source(
        project_slug: str,
        ref: str = "",
        path: str = "",
    ) -> dict[str, Any]:
        """Read a bound Project SourceRepo. If the slug is actually a GitHub repo name, that repo is used."""
        suffix = "/source"
        if path:
            suffix += "/tree"
        params = httpx.QueryParams({"ref": ref, "path": path})
        slug = quote(project_slug.strip(), safe="")
        try:
            return _clip_source_payload(
                api.request(
                    "GET",
                    f"/api/owner/projects/{slug}{suffix}?{params}",
                )
            )
        except RuntimeError as exc:
            if "404" not in str(exc) and "not_found" not in str(exc):
                raise
            return portfolio_get_github_source(project_slug, ref, path)

    @server.tool()
    def portfolio_get_source_file(
        project_slug: str,
        path: str,
        ref: str = "",
    ) -> dict[str, Any]:
        """Read one file from a bound Project, or from a GitHub repo if the slug is a repo name."""
        params = httpx.QueryParams({"ref": ref, "path": path})
        slug = quote(project_slug.strip(), safe="")
        try:
            return _clip_source_payload(
                api.request(
                    "GET",
                    f"/api/owner/projects/{slug}/source/blob?{params}",
                )
            )
        except RuntimeError as exc:
            if "404" not in str(exc) and "not_found" not in str(exc):
                raise
            return portfolio_get_github_file(project_slug, path, ref)

    def _resume_by_id(identifier: str) -> dict[str, Any]:
        items = api.request("GET", "/api/owner/resumes") or []
        return _find(items, identifier, kind="resume")

    def _template_by_id(identifier: str) -> dict[str, Any]:
        items = api.request("GET", "/api/owner/resume-templates") or []
        return _find(items, identifier, kind="template")

    @server.tool()
    def portfolio_list_resume_templates() -> dict[str, Any]:
        """List ResumeTemplate layouts. classic-a4 is the built-in A4 single-column contract."""
        items = api.request("GET", "/api/owner/resume-templates")
        return {"items": items, "total": len(items)}

    @server.tool()
    def portfolio_get_resume_template(identifier: str) -> dict[str, Any]:
        """Get one ResumeTemplate by id or slug."""
        return _template_by_id(identifier)

    @server.tool()
    def portfolio_create_resume_template(
        slug: str,
        name: dict[str, str],
        sections: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a ResumeTemplate. sections are summary, education, internship, projects, activities, skillsOthers."""
        api.require_write()
        return api.request(
            "POST",
            "/api/owner/resume-templates",
            json={
                "slug": slug,
                "name": name,
                "sections": sections
                or ["summary", "education", "projects", "skillsOthers"],
            },
        )

    @server.tool()
    def portfolio_update_resume_template(
        identifier: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a ResumeTemplate. Built-in classic-a4 should not be deleted."""
        api.require_write()
        current = _template_by_id(identifier)
        payload = _merge(current, changes)
        payload.pop("id", None)
        payload.pop("builtin", None)
        return api.request(
            "PUT",
            f"/api/owner/resume-templates/{current['id']}",
            json=payload,
        )

    @server.tool()
    def portfolio_list_resumes(
        status: Literal["draft", "published", "all"] = "all",
    ) -> dict[str, Any]:
        """List Resume documents. Each is one language and one template fill-in."""
        items = api.request("GET", "/api/owner/resumes") or []
        if status != "all":
            items = [item for item in items if item.get("status") == status]
        return {"items": items, "total": len(items)}

    @server.tool()
    def portfolio_get_resume(identifier: str) -> dict[str, Any]:
        """Get one Resume by id or slug."""
        return _resume_by_id(identifier)

    @server.tool()
    def portfolio_create_resume(
        slug: str,
        title: str,
        template_slug: str = "classic-a4",
        locale: str = "en",
        header: dict[str, Any] | None = None,
        summary: list[str] | None = None,
        education: list[dict[str, Any]] | None = None,
        internships: list[dict[str, Any]] | None = None,
        projects: list[dict[str, Any]] | None = None,
        activities: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
        languages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a Draft Resume filled from structured fields. Always draft."""
        api.require_write()
        return api.request(
            "POST",
            "/api/owner/resumes",
            json={
                "slug": slug,
                "title": title,
                "templateSlug": template_slug,
                "locale": locale,
                "status": "draft",
                "header": header or {},
                "summary": summary or [],
                "education": education or [],
                "internships": internships or [],
                "projects": projects or [],
                "activities": activities or [],
                "skills": skills or [],
                "languages": languages or [],
            },
        )

    @server.tool()
    def portfolio_update_resume(
        identifier: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a Resume. Cannot publish here; call portfolio_publish_resume after the Owner asks."""
        api.require_write()
        current = _resume_by_id(identifier)
        payload = _merge(current, changes)
        payload.pop("id", None)
        payload.pop("pdfUrl", None)
        payload = _guard_status_on_update(current, payload)
        return api.request(
            "PUT",
            f"/api/owner/resumes/{current['id']}",
            json=payload,
        )

    @server.tool()
    def portfolio_generate_resume(identifier: str) -> dict[str, Any]:
        """Render the Resume PDF with Python from its ResumeTemplate."""
        api.require_write()
        current = _resume_by_id(identifier)
        return api.request(
            "POST", f"/api/owner/resumes/{current['id']}/generate"
        )

    @server.tool()
    def portfolio_publish_resume(identifier: str) -> dict[str, Any]:
        """Publish a Resume after the Owner explicitly asks. Generates PDF if missing."""
        api.require_write()
        current = _resume_by_id(identifier)
        return api.request(
            "POST", f"/api/owner/resumes/{current['id']}/publish"
        )

    @server.tool()
    def portfolio_import_resume_from_github(
        full_name: str,
        path: str,
        slug: str,
        ref: str = "",
        title: str = "",
        template_slug: str = "",
    ) -> dict[str, Any]:
        """Import a Resume JSON from an authorized GitHub file. Accepts the extracted format.json shape."""
        api.require_write()
        return api.request(
            "POST",
            "/api/owner/resumes/import-github",
            json={
                "fullName": full_name,
                "path": path,
                "ref": ref,
                "slug": slug,
                "title": title,
                "templateSlug": template_slug,
            },
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
