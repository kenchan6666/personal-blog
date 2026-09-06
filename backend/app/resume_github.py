from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.agent_proxy import _agent_headers
from app.github import GitHubBrowseError, match_authorized_repo
from app.resume import split_resume_lines

_EXT_STACK = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".css": "CSS",
}
_NAME_STACK = {
    "package.json": "Node.js",
    "pnpm-lock.yaml": "Node.js",
    "yarn.lock": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "pipfile": "Python",
    "go.mod": "Go",
    "cargo.toml": "Rust",
    "dockerfile": "Docker",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "fastapi": "FastAPI",
    "manage.py": "Django",
}
_JSON_RE = re.compile(r"\{.*\}", re.S)
_FILLER_BULLET_RE = re.compile(
    r"^(primary features of|key features of|overview of|主要功能|的主要功能)\b",
    re.I,
)


async def analyze_github_project(
    *,
    github: Any,
    access_token: str,
    full_name: str,
    locale: str,
    settings: Any,
) -> dict[str, Any]:
    try:
        repos = await github.list_repos(access_token=access_token)
        repo = match_authorized_repo(repos, full_name)
        if repo is None:
            raise GitHubBrowseError("not_found")
        owner = str(repo["owner"])
        name = str(repo["name"])
        ref = str(repo.get("defaultBranch") or "main")
        try:
            readme = await github.get_readme(
                access_token=access_token,
                owner=owner,
                name=name,
                ref=ref,
            )
            readme_text = str(readme.get("content") or "")
        except GitHubBrowseError:
            readme_text = ""
        names = await _collect_names(
            github,
            access_token=access_token,
            owner=owner,
            name=name,
            ref=ref,
        )
    except (GitHubBrowseError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="github_repo_not_found",
        ) from exc

    inferred = _heuristic_project(
        name=name,
        description=str(repo.get("description") or ""),
        readme=readme_text,
        names=names,
        locale=locale,
    )
    completed = await _complete_project_copy(
        settings,
        name=name,
        locale=locale,
        readme=readme_text,
        description=str(repo.get("description") or ""),
        names=names,
    )
    tech = _limit_stack((completed or {}).get("tech_stack") or inferred["tech_stack"])
    bullets = _usable_bullets(
        (completed or {}).get("description") or inferred["description"],
        name,
    )
    return {
        "name": name,
        "tech_stack": tech,
        "description": bullets[:5],
    }


async def _collect_names(
    github: Any,
    *,
    access_token: str,
    owner: str,
    name: str,
    ref: str,
) -> list[str]:
    root = await github.list_tree(
        access_token=access_token,
        owner=owner,
        name=name,
        ref=ref,
        path="",
    )
    names = [str(item.get("name") or "") for item in root]
    for item in root:
        if item.get("type") != "dir":
            continue
        child = await github.list_tree(
            access_token=access_token,
            owner=owner,
            name=name,
            ref=ref,
            path=str(item.get("path") or ""),
        )
        names.extend(str(entry.get("name") or "") for entry in child)
    return [item for item in names if item]


def _heuristic_project(
    *,
    name: str,
    description: str,
    readme: str,
    names: list[str],
    locale: str,
) -> dict[str, list[str]]:
    del locale
    stack = _stack_from_names(names)
    bullets = _readme_bullets(readme, name)
    if description.strip():
        bullets = _usable_bullets(description, name) + bullets
    return {"tech_stack": stack, "description": bullets[:5]}


def _usable_bullets(values: Any, name: str) -> list[str]:
    return [
        line
        for line in split_resume_lines(values)
        if _usable_bullet(line, name)
    ]


def _usable_bullet(text: str, name: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 8:
        return False
    if _FILLER_BULLET_RE.search(cleaned):
        return False
    slug = re.sub(r"[\W_]+", "", name).lower()
    compact = re.sub(r"[\W_]+", "", cleaned).lower()
    if slug and (compact == slug or compact.startswith(slug) and len(compact) <= len(slug) + 6):
        return False
    if cleaned.lower() in {"readme", "overview", "introduction", "features"}:
        return False
    return True


def _stack_from_names(names: list[str]) -> list[str]:
    found: list[str] = []
    for raw in names:
        lower = raw.lower()
        if lower in _NAME_STACK:
            found.append(_NAME_STACK[lower])
            continue
        suffix = ""
        if "." in lower:
            suffix = "." + lower.rsplit(".", 1)[-1]
        if suffix in _EXT_STACK:
            found.append(_EXT_STACK[suffix])
    return _limit_stack(found)


def _limit_stack(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        text = str(item).strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        out.append(text)
        if len(out) == 5:
            break
    return out


def _readme_bullets(readme: str, name: str) -> list[str]:
    lines: list[str] = []
    for raw in readme.splitlines():
        text = raw.strip()
        if not text or text.startswith("```") or text.startswith("![") or text.startswith("|"):
            continue
        if text.startswith("#"):
            heading = text.lstrip("#").strip()
            if _usable_bullet(heading, name):
                lines.append(heading)
            continue
        lines.extend(_usable_bullets([text], name))
        if len(lines) >= 5:
            break
    return lines[:5]


async def _complete_project_copy(
    settings: Any,
    *,
    name: str,
    locale: str,
    readme: str,
    description: str,
    names: list[str],
) -> dict[str, Any] | None:
    url = str(getattr(settings, "agent_api_url", "") or "").strip()
    if not url:
        return None
    prompt = (
        "Fill a resume project from this GitHub repo. Reply with JSON only: "
        '{"tech_stack":["..."],"description":["..."]}. '
        "tech_stack: 3-5 language/framework names only, no library laundry list. "
        "description: 3-5 bullets; each is an application feature and which "
        "tech delivered that feature. No dates. No paragraph. "
        "Never invent filler such as 'Primary features of {name}'. "
        "If the README does not support a feature, omit it. "
        f"Locale: {locale}. Repo: {name}. "
        f"Description: {description[:300]}. "
        f"Files: {', '.join(names[:40])}. "
        f"README:\n{readme[:3500]}"
    )
    target = f"{url.rstrip('/')}/v1/chat/completions"
    headers = _agent_headers(getattr(settings, "agent_internal_token", ""))
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                target,
                headers=headers,
                json={
                    "model": "viola",
                    "stream": False,
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if response.status_code >= 400:
            return None
        payload = response.json()
        text = str(
            (((payload.get("choices") or [{}])[0].get("message") or {}).get("content"))
            or payload.get("content")
            or ""
        )
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None
    return _parse_project_json(text)


def _parse_project_json(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1]
    match = _JSON_RE.search(raw)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    stack = data.get("tech_stack") or data.get("techStack") or []
    bullets = data.get("description") or []
    if isinstance(stack, str):
        stack = [part.strip() for part in stack.split(",") if part.strip()]
    if isinstance(bullets, str):
        bullets = split_resume_lines(bullets)
    if not isinstance(stack, list) or not isinstance(bullets, list):
        return None
    return {"tech_stack": stack, "description": bullets}
