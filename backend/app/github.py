from __future__ import annotations

from typing import Protocol
from urllib.parse import urlencode

import httpx


class GitHubOAuthError(Exception):
    pass


class GitHubClient(Protocol):
    def authorization_url(self, *, state: str) -> str: ...

    async def exchange_code(self, *, code: str) -> str: ...

    async def list_repos(self, *, access_token: str) -> list[dict[str, object]]: ...


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
            },
            {
                "fullName": "kenchan6666/secret-lab",
                "owner": "kenchan6666",
                "name": "secret-lab",
                "private": True,
                "htmlUrl": "https://github.com/kenchan6666/secret-lab",
                "defaultBranch": "main",
            },
        ]


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
                        }
                    )
                url = response.links.get("next", {}).get("url")
        return repos
