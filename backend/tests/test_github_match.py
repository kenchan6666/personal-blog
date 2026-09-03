from app.github import match_authorized_repo, match_blob_path


REPOS = [
    {
        "fullName": "kenchan6666/secret-lab",
        "owner": "kenchan6666",
        "name": "secret-lab",
    },
    {
        "fullName": "kenchan6666/taiko_bot_qq",
        "owner": "kenchan6666",
        "name": "taiko_bot_qq",
    },
]


def test_match_authorized_repo_ignores_case_and_accepts_short_name() -> None:
    assert match_authorized_repo(REPOS, "KENCHAN6666/Taiko_Bot_QQ")["name"] == (
        "taiko_bot_qq"
    )
    assert match_authorized_repo(REPOS, "", owner="anyone", name="secret-lab")[
        "fullName"
    ] == "kenchan6666/secret-lab"
    assert match_authorized_repo(REPOS, "missing") is None


def test_match_blob_path_finds_readme_regardless_of_case() -> None:
    paths = ["readme.md", "src/app.py"]
    assert match_blob_path(paths, "README.md") == "readme.md"
    assert match_blob_path(paths, "src/APP.py") == "src/app.py"
    assert match_blob_path(paths, "missing") is None
