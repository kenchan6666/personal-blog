"""Tests for config loader environment overrides."""

from __future__ import annotations

from pathlib import Path

import pytest

from viola.config.loader import load_config
from viola.config.schema import Config

_MISSING_CONFIG = Path("/tmp/viola-test-missing-config.json")


@pytest.fixture
def clean_agent_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "VIOLA_AGENTS__DEFAULTS__MODEL",
        "VIOLA_AGENTS__DEFAULTS__PROVIDER",
        "VIOLA_AGENTS__DEFAULTS__TIMEZONE",
        "VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACES",
        "VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACE_ROOT",
        "VIOLA_AGENTS_DEFAULTS_MODEL",
        "VIOLA_AGENTS_DEFAULTS_PROVIDER",
        "VIOLA_AGENTS_DEFAULTS_TIMEZONE",
        "VIOLA_AGENTS_DEFAULTS_PER_USER_WORKSPACES",
        "VIOLA_AGENTS_DEFAULTS_PER_USER_WORKSPACE_ROOT",
        "UNI_API_BASE",
        "VIOLA_PROVIDERS__UNIAPI__API_BASE",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
        "OPENROUTER_CHAT_MODEL",
        "OPENROUTER_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_timezone_env_override(clean_agent_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__TIMEZONE", "Asia/Hong_Kong")
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.timezone == "Asia/Hong_Kong"


def test_timezone_env_strips_quotes(clean_agent_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__TIMEZONE", '"Asia/Hong_Kong"')
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.timezone == "Asia/Hong_Kong"


def test_invalid_timezone_env_is_ignored(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__TIMEZONE", "Not/A/Timezone")
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.timezone == Config().agents.defaults.timezone


def test_per_user_workspaces_env_override(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"agents": {"defaults": {"perUserWorkspaces": false}}}', encoding="utf-8")
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACES", "true")
    config = load_config(config_path)
    assert config.agents.defaults.per_user_workspaces is True


def test_per_user_workspace_root_env_override(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACE_ROOT", "/data/users")
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.per_user_workspace_root == "/data/users"


def test_legacy_agent_defaults_env_names_are_supported(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIOLA_AGENTS_DEFAULTS_PROVIDER", "uniapi")
    monkeypatch.setenv("VIOLA_AGENTS_DEFAULTS_TIMEZONE", "Asia/Hong_Kong")
    monkeypatch.setenv("VIOLA_AGENTS_DEFAULTS_PER_USER_WORKSPACES", "true")
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.provider == "uniapi"
    assert config.agents.defaults.timezone == "Asia/Hong_Kong"
    assert config.agents.defaults.per_user_workspaces is True


def test_uniapi_base_env_fallback_from_uni_api_base(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNI_API_BASE", "https://api.uniapi.io")
    config = load_config(_MISSING_CONFIG)
    assert config.providers.uniapi.api_base == "https://api.uniapi.io"


def test_uniapi_base_env_normalizes_claude_path(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNI_API_BASE", "https://hk.uniapi.io/claude")
    config = load_config(_MISSING_CONFIG)
    assert config.providers.uniapi.api_base == "https://api.uniapi.io"


def test_uniapi_base_env_normalizes_portal_url(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNI_API_BASE", "https://uniapi.ai")
    config = load_config(_MISSING_CONFIG)
    assert config.providers.uniapi.api_base == "https://api.uniapi.io"


def test_get_api_base_uniapi_claude_model_uses_configured_gateway() -> None:
    config = Config()
    config.providers.uniapi.api_base = "https://hk.uniapi.io/claude"
    config.agents.defaults.model = "claude-sonnet-4-6"
    config.agents.defaults.provider = "uniapi"
    assert config.get_api_base("claude-sonnet-4-6") == "https://api.uniapi.io"


def test_uniapi_key_falls_back_to_openrouter_api_key(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    config = load_config(_MISSING_CONFIG)
    assert config.providers.uniapi.api_key == "or-test-key"


def test_uniapi_base_falls_back_to_openrouter_base_url(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://api.uniapi.io")
    config = load_config(_MISSING_CONFIG)
    assert config.providers.uniapi.api_base == "https://api.uniapi.io"


def test_load_mcp_fragment_reads_mcp_common_package(monkeypatch) -> None:
    from viola.config.loader import _load_mcp_fragment

    class _FakeFiles:
        def __truediv__(self, other: str):
            assert other == "fragment.json"
            return self

        def read_text(self, encoding: str = "utf-8") -> str:
            return '{"nanobot": {"type": "stdio", "command": "python3", "args": ["-m", "mcp_nanobot.server"]}}'

    monkeypatch.setattr(
        "importlib.resources.files",
        lambda package: _FakeFiles() if package == "mcp_common" else (_ for _ in ()).throw(ImportError(package)),
    )
    fragment = _load_mcp_fragment()
    assert "nanobot" in fragment


def test_agent_model_falls_back_to_openrouter_chat_model(
    clean_agent_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL", "gpt-5.1")
    config = load_config(_MISSING_CONFIG)
    assert config.agents.defaults.model == "gpt-5.1"
