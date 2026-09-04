from __future__ import annotations

import base64
from typing import Protocol
from urllib.parse import quote, urlencode

import httpx


class GitHubOAuthError(Exception):
    pass


class GitHubBrowseError(Exception):
    pass


def is_readme_filename(name: str) -> bool:
    lower = name.lower()
    return lower == "readme" or lower.startswith("readme.")


def match_authorized_repo(
    repos: list[dict[str, object]],
    query: str,
    *,
    owner: str = "",
    name: str = "",
) -> dict[str, object] | None:
    wanted = query.strip().strip("/").casefold()
    owner_part = owner.strip().casefold()
    name_part = name.strip().casefold()
    if owner_part and name_part:
        wanted = f"{owner_part}/{name_part}"
    if not wanted:
        return None
    full_matches = [
        item
        for item in repos
        if str(item.get("fullName") or "").casefold() == wanted
    ]
    if len(full_matches) == 1:
        return full_matches[0]
    short = wanted.rsplit("/", 1)[-1]
    name_matches = [
        item
        for item in repos
        if str(item.get("name") or str(item.get("fullName") or "").rsplit("/", 1)[-1]).casefold()
        == short
    ]
    if len(name_matches) == 1:
        return name_matches[0]
    return None


def match_blob_path(paths: list[str], path: str) -> str | None:
    wanted = path.strip("/")
    if not wanted:
        return None
    if wanted in paths:
        return wanted
    folded = {item.casefold(): item for item in paths}
    exact = folded.get(wanted.casefold())
    if exact:
        return exact
    if is_readme_filename(wanted.rsplit("/", 1)[-1]):
        root_readmes = [
            item for item in paths if "/" not in item and is_readme_filename(item)
        ]
        if root_readmes:
            return root_readmes[0]
    return None


class GitHubClient(Protocol):
    def authorization_url(self, *, state: str) -> str: ...

    async def exchange_code(self, *, code: str) -> str: ...

    async def list_repos(self, *, access_token: str) -> list[dict[str, object]]: ...

    async def repo_is_private(
        self, *, access_token: str, owner: str, name: str
    ) -> bool: ...

    async def list_branches(
        self, *, access_token: str, owner: str, name: str
    ) -> list[str]: ...

    async def get_readme(
        self, *, access_token: str, owner: str, name: str, ref: str
    ) -> dict[str, str]: ...

    async def list_tree(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> list[dict[str, str]]: ...

    async def get_blob(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> dict[str, str]: ...


class RecordingGitHub:
    """In-memory GitHub for HTTP-seam tests. Never talks to api.github.com."""

    def __init__(self, *, client_id: str = "test-client") -> None:
        self.client_id = client_id
        self.exchanged: list[str] = []

    def authorization_url(self, *, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "state": state,
                "scope": "repo read:user",
            }
        )
        return f"https://github.com/login/oauth/authorize?{query}"

    async def exchange_code(self, *, code: str) -> str:
        self.exchanged.append(code)
        if code != "ok":
            raise GitHubOAuthError("oauth_failed")
        return "gho_test"

    async def list_repos(self, *, access_token: str) -> list[dict[str, object]]:
        if access_token != "gho_test":
            raise GitHubOAuthError("bad_token")
        return [
            {
                "fullName": "kenchan6666/personal-blog",
                "owner": "kenchan6666",
                "name": "personal-blog",
                "private": False,
                "htmlUrl": "https://github.com/kenchan6666/personal-blog",
                "defaultBranch": "master",
                "description": "Job-seeking portfolio",
            },
            {
                "fullName": "kenchan6666/secret-lab",
                "owner": "kenchan6666",
                "name": "secret-lab",
                "private": True,
                "htmlUrl": "https://github.com/kenchan6666/secret-lab",
                "defaultBranch": "main",
                "description": "",
            },
            {
                "fullName": "kenchan6666/empty-box",
                "owner": "kenchan6666",
                "name": "empty-box",
                "private": False,
                "htmlUrl": "https://github.com/kenchan6666/empty-box",
                "defaultBranch": "main",
                "description": "",
            },
        ]

    FILES = {
        "kenchan6666/personal-blog": {
            "master": {
                "README.md": "# Glass\nHello\n",
                "src/app.py": "print('hi')\n",
                "cv/classic.format.json": (
                    '{"instance":{"header":{"name":"Chan YatNam",'
                    '"phone":"+852 63058683","email":"ynchanhk@gmail.com",'
                    '"city":"Newcastle upon Tyne"},'
                    '"summary":["Seeking a programming internship."],'
                    '"education":[{"institution":"Newcastle University",'
                    '"field":"Computer Science","degree":"Bachelor",'
                    '"start":"2022-06","end":"2026-06","city":"Newcastle",'
                    '"honor":"First Honor Degree","related_courses":'
                    '["Web Development"]}],'
                    '"projects":[{"name":"Pantry pal","start":"2024-05",'
                    '"end":"2024-06","tech_stack":["Python","Flask"],'
                    '"description":["Track food items and expiry dates."]}],'
                    '"skills":["Python","Flask"],'
                    '"languages":[{"name":"English","level":"Fluent"}]}}'
                ),
            },
            "feature": {
                "Readme.md": "# Feature\nnext\n",
                "src/app.py": "print('feat')\n",
            },
        },
        "kenchan6666/empty-box": {
            "main": {
                "src/app.py": "print('empty')\n",
            },
        },
        "kenchan6666/secret-lab": {
            "main": {
                "README.md": "# Secret\nprivate notes\n",
                "secret.txt": "do-not-leak\n",
            },
        },
    }

    async def repo_is_private(
        self, *, access_token: str, owner: str, name: str
    ) -> bool:
        full_name = f"{owner}/{name}"
        if full_name == "kenchan6666/secret-lab":
            return True
        if full_name in self.FILES:
            return False
        raise GitHubBrowseError("not_found")

    def _files(self, owner: str, name: str, ref: str) -> dict[str, str]:
        repo = self.FILES.get(f"{owner}/{name}")
        if repo is None or ref not in repo:
            raise GitHubBrowseError("not_found")
        return repo[ref]

    async def list_branches(
        self, *, access_token: str, owner: str, name: str
    ) -> list[str]:
        repo = self.FILES.get(f"{owner}/{name}")
        if repo is None:
            raise GitHubBrowseError("not_found")
        return sorted(repo)

    async def get_readme(
        self, *, access_token: str, owner: str, name: str, ref: str
    ) -> dict[str, str]:
        files = self._files(owner, name, ref)
        for path, content in files.items():
            if "/" in path:
                continue
            if is_readme_filename(path):
                return {"path": path, "content": content}
        raise GitHubBrowseError("not_found")

    async def list_tree(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> list[dict[str, str]]:
        files = self._files(owner, name, ref)
        prefix = path.strip("/")
        entries: dict[str, dict[str, str]] = {}
        for file_path in files:
            relative = file_path
            if prefix:
                if relative == prefix or not relative.startswith(prefix + "/"):
                    continue
                rest = relative[len(prefix) + 1 :]
            else:
                rest = relative
            part = rest.split("/", 1)[0]
            child_path = f"{prefix}/{part}" if prefix else part
            kind = "dir" if "/" in rest else "file"
            entries[child_path] = {"name": part, "path": child_path, "type": kind}
        return sorted(entries.values(), key=lambda item: (item["type"] != "dir", item["name"]))

    async def get_blob(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> dict[str, str]:
        files = self._files(owner, name, ref)
        resolved = match_blob_path(list(files), path)
        if resolved is None:
            raise GitHubBrowseError("not_found")
        return {"path": resolved, "content": files[resolved]}


class HttpGitHub:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        callback_url: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url

    def authorization_url(self, *, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.callback_url,
                "state": state,
                "scope": "repo read:user",
            }
        )
        return f"https://github.com/login/oauth/authorize?{query}"

    async def exchange_code(self, *, code: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.callback_url,
                    },
                )
            payload = response.json()
        except Exception as exc:
            raise GitHubOAuthError("oauth_failed") from exc
        token = payload.get("access_token")
        if not token:
            raise GitHubOAuthError(str(payload.get("error", "oauth_failed")))
        return str(token)

    async def list_repos(self, *, access_token: str) -> list[dict[str, object]]:
        repos: list[dict[str, object]] = []
        url = "https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            while url:
                response = await client.get(url, headers=headers)
                if response.status_code >= 400:
                    raise GitHubOAuthError("repos_failed")
                for item in response.json():
                    repos.append(
                        {
                            "fullName": item["full_name"],
                            "owner": item["owner"]["login"],
                            "name": item["name"],
                            "private": bool(item["private"]),
                            "htmlUrl": item["html_url"],
                            "defaultBranch": item.get("default_branch") or "main",
                            "description": item.get("description") or "",
                        }
                    )
                url = response.links.get("next", {}).get("url")
        return repos

    async def repo_is_private(
        self, *, access_token: str, owner: str, name: str
    ) -> bool:
        url = f"https://api.github.com/repos/{owner}/{name}"
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers(access_token))
        if response.status_code >= 400:
            raise GitHubBrowseError("not_found")
        return bool(response.json().get("private"))

    def _headers(self, access_token: str) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def list_branches(
        self, *, access_token: str, owner: str, name: str
    ) -> list[str]:
        url = f"https://api.github.com/repos/{owner}/{name}/branches?per_page=100"
        names: list[str] = []
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            while url:
                response = await client.get(url, headers=self._headers(access_token))
                if response.status_code >= 400:
                    raise GitHubBrowseError("not_found")
                names.extend(item["name"] for item in response.json())
                url = response.links.get("next", {}).get("url")
        return sorted(names)

    async def get_readme(
        self, *, access_token: str, owner: str, name: str, ref: str
    ) -> dict[str, str]:
        url = f"https://api.github.com/repos/{owner}/{name}/readme"
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers=self._headers(access_token),
                params={"ref": ref},
            )
        if response.status_code < 400:
            payload = response.json()
            raw = base64.b64decode(payload.get("content") or "")
            return {
                "path": str(payload.get("path") or "README.md"),
                "content": raw.decode("utf-8", errors="replace"),
            }
        listing = await self._contents(access_token, owner, name, ref, "")
        if isinstance(listing, list):
            match = next(
                (
                    item
                    for item in listing
                    if is_readme_filename(str(item.get("name") or ""))
                    and item.get("type") == "file"
                ),
                None,
            )
            if match is not None:
                return await self.get_blob(
                    access_token=access_token,
                    owner=owner,
                    name=name,
                    ref=ref,
                    path=str(match.get("path") or match.get("name")),
                )
        raise GitHubBrowseError("not_found")

    async def list_tree(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> list[dict[str, str]]:
        payload = await self._contents(access_token, owner, name, ref, path)
        if not isinstance(payload, list):
            raise GitHubBrowseError("not_a_directory")
        entries = []
        for item in payload:
            kind = "dir" if item.get("type") == "dir" else "file"
            entries.append(
                {
                    "name": str(item["name"]),
                    "path": str(item["path"]),
                    "type": kind,
                }
            )
        return sorted(entries, key=lambda item: (item["type"] != "dir", item["name"]))

    async def get_blob(
        self,
        *,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> dict[str, str]:
        try:
            payload = await self._contents(access_token, owner, name, ref, path)
        except GitHubBrowseError:
            if is_readme_filename(path.rsplit("/", 1)[-1]):
                return await self.get_readme(
                    access_token=access_token,
                    owner=owner,
                    name=name,
                    ref=ref,
                )
            parent = path.strip("/").rsplit("/", 1)
            directory = parent[0] if len(parent) == 2 else ""
            listing = await self._contents(
                access_token, owner, name, ref, directory
            )
            if not isinstance(listing, list):
                raise
            resolved = match_blob_path(
                [str(item.get("path") or item.get("name") or "") for item in listing],
                path,
            )
            if resolved is None:
                raise GitHubBrowseError("not_found") from None
            payload = await self._contents(
                access_token, owner, name, ref, resolved
            )
        if isinstance(payload, list) or payload.get("type") != "file":
            raise GitHubBrowseError("not_a_file")
        raw = base64.b64decode(payload.get("content") or "")
        return {
            "path": str(payload.get("path") or path),
            "content": raw.decode("utf-8", errors="replace"),
        }

    async def _contents(
        self,
        access_token: str,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> object:
        suffix = quote(path.strip("/")) if path.strip("/") else ""
        url = f"https://api.github.com/repos/{owner}/{name}/contents"
        if suffix:
            url = f"{url}/{suffix}"
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers=self._headers(access_token),
                params={"ref": ref},
            )
        if response.status_code >= 400:
            raise GitHubBrowseError("not_found")
        return response.json()
