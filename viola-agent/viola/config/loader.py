"""Configuration loading utilities."""

import json
import os
import re
from pathlib import Path
from typing import Any

import pydantic
from loguru import logger
from pydantic import BaseModel

from viola.config.schema import Config, MCPServerConfig
from viola.providers.registry import normalize_uniapi_api_base

# Global variable to store current config path (for multi-instance support)
_current_config_path: Path | None = None


def set_config_path(path: Path) -> None:
    """Set the current config path (used to derive data directory)."""
    global _current_config_path
    _current_config_path = path


def get_config_path() -> Path:
    """Get the configuration file path."""
    if _current_config_path:
        return _current_config_path
    return Path.home() / ".viola" / "config.json"


def _mcp_base_url() -> str:
    """Docker-internal backend URL for MCP stdio servers (not the public nginx URL)."""
    raw = os.environ.get("BACKEND_API_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    if raw:
        return raw
    return "http://127.0.0.1:8000"



def _load_mcp_fragment() -> dict[str, Any]:
    """Load and merge MCP fragments from installed helper packages."""
    from importlib.resources import files as _res_files

    merged: dict[str, Any] = {}
    candidates = ("mcp_common", "mcp_nanobot.mcp_common")
    for package_name in candidates:
        try:
            text = (_res_files(package_name) / "fragment.json").read_text(encoding="utf-8")
            fragment = json.loads(text)
            if isinstance(fragment, dict):
                merged.update(fragment)
                logger.info("Loaded MCP fragment from {}", package_name)
        except (ImportError, FileNotFoundError) as exc:
            logger.info("{} not available, skipping MCP auto-registration: {}", package_name, exc)
    return merged


def _resolve_fragment_env(raw_env: dict[str, str]) -> dict[str, str]:
    """Resolve ``${VAR}`` placeholders in a fragment env dict.

    ``BACKEND_API_BASE_URL`` uses ``_mcp_base_url()`` for its default fallback.
    Other vars are taken directly from the process environment; absent vars are skipped
    so unset optional secrets (e.g. ``INTERNAL_SECRET``) are not passed as empty strings.
    ``PUBLIC_URL`` is appended when set, regardless of whether it appears in the fragment.
    """
    resolved: dict[str, str] = {}
    for key, value in raw_env.items():
        m = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
        if m:
            var_name = m.group(1)
            if var_name == "BACKEND_API_BASE_URL":
                resolved[key] = _mcp_base_url()
            else:
                v = os.environ.get(var_name, "").strip()
                if v:
                    resolved[key] = v
        else:
            resolved[key] = value
    public = os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
    if public and "PUBLIC_URL" not in resolved:
        resolved["PUBLIC_URL"] = public
    return resolved


def _apply_backend_mcp_from_fragment(config: Config) -> None:

    fragment = _load_mcp_fragment()
    for server_name, server_cfg in fragment.items():
        if server_name in config.tools.mcp_servers:
            logger.debug("MCP server '{}' already configured explicitly, fragment skipped", server_name)
            continue
        opt_out_var = f"VIOLA_TOOLS_{server_name.upper().replace('-', '_')}_MCP"
        if os.environ.get(opt_out_var, "").strip().lower() in ("0", "false", "no", "off"):
            continue

        env = _resolve_fragment_env(server_cfg.get("env", {}))
        base = env.get("BACKEND_API_BASE_URL", _mcp_base_url())
        logger.info("Registering {} MCP (stdio) → {!r}", server_name, base)

        config.tools.mcp_servers[server_name] = MCPServerConfig(
            type=server_cfg.get("type", "stdio"),
            command=server_cfg.get("command", "python3"),
            args=server_cfg.get("args", []),
            env=env,
            tool_timeout=server_cfg.get("toolTimeout", 120),
            enabled_tools=server_cfg.get("enabledTools", []),
        )


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Loaded configuration object.
    """
    path = config_path or get_config_path()

    config = Config()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_config(data)
            config = Config.model_validate(data)
        except (json.JSONDecodeError, ValueError, pydantic.ValidationError) as e:
            logger.warning("Failed to load config from {}: {}", path, e)
            logger.warning("Using default configuration.")

    _apply_channels_env_overrides(config)
    _apply_providers_env_overrides(config)
    _apply_agent_defaults_env_overrides(config)
    _apply_backend_mcp_from_fragment(config)
    _apply_tools_env_overrides(config)
    _apply_api_env_overrides(config)
    _apply_ssrf_whitelist(config)
    return config


def _apply_api_env_overrides(config: Config) -> None:
    """Overlay ``VIOLA_API__*`` env for serve-mode options."""
    v = os.environ.get("VIOLA_API__BACKGROUND_TASKS", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        config.api.background_tasks = True
    elif v in ("0", "false", "no", "off"):
        config.api.background_tasks = False


def _apply_tools_env_overrides(config: Config) -> None:
    """Overlay ``VIOLA_TOOLS__*`` env for fields not merged from JSON file validation."""
    v = os.environ.get("VIOLA_TOOLS__PERSISTENCE_VIA_MCP_ONLY", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        config.tools.persistence_via_mcp_only = True
    elif v in ("0", "false", "no", "off"):
        config.tools.persistence_via_mcp_only = False
    sched = os.environ.get("VIOLA_TOOLS__ALLOW_SCHEDULED_TASKS_ON_API", "").strip().lower()
    if sched in ("1", "true", "yes", "on"):
        config.tools.allow_scheduled_tasks_on_api = True
    elif sched in ("0", "false", "no", "off"):
        config.tools.allow_scheduled_tasks_on_api = False
    elif config.tools.mcp_servers:
        # Any MCP server present implies a backend is wired up. Default to MCP-only
        # persistence so the model cannot bypass it via exec or workspace writes.
        config.tools.persistence_via_mcp_only = True
    if config.tools.persistence_via_mcp_only:
        logger.info(
            "tools.persistenceViaMcpOnly: exec, workspace write tools, and Dream file edits are off; "
            "persist via MCP tools only."
        )


def _apply_providers_env_overrides(config: Config) -> None:
    """Overlay provider credentials from env when set (Docker / secrets).

    Values loaded from ``config.json`` via ``model_validate`` do not pick up
    nested ``BaseSettings`` env sources; inject keys here so compose ``environment``
    overrides the file.
    """
    uni_key = _first_nonempty_env(
        "UNI_API_KEY",
        "VIOLA_PROVIDERS__UNIAPI__API_KEY",
        "OPENROUTER_API_KEY",
    )
    if uni_key:
        config.providers.uniapi.api_key = uni_key

    uni_base = _first_nonempty_env(
        "VIOLA_PROVIDERS__UNIAPI__API_BASE",
        "UNI_API_BASE",
        "OPENROUTER_BASE_URL",
        "OPENAI_API_BASE",
    )
    if uni_base:
        config.providers.uniapi.api_base = uni_base

    if config.providers.uniapi.api_base:
        config.providers.uniapi.api_base = normalize_uniapi_api_base(
            config.providers.uniapi.api_base
        )

    ak = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if ak:
        config.providers.anthropic.api_key = ak

    ok_openai = os.environ.get("OPENAI_API_KEY", "").strip()
    if ok_openai:
        config.providers.openai.api_key = ok_openai


def _normalize_env_value(raw: str) -> str:
    """Strip whitespace and optional surrounding quotes from env_file values."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def _first_nonempty_env(*keys: str) -> str:
    """Return the first non-empty env value from *keys* (after normalization)."""
    for key in keys:
        value = _normalize_env_value(os.environ.get(key, ""))
        if value:
            return value
    return ""


def _apply_agent_defaults_env_overrides(config: Config) -> None:
    """Overlay ``VIOLA_AGENTS__DEFAULTS__*`` so Docker can set model/provider/timezone."""
    model = _first_nonempty_env(
        "VIOLA_AGENTS__DEFAULTS__MODEL",
        "VIOLA_AGENTS_DEFAULTS_MODEL",
        "OPENROUTER_CHAT_MODEL",
        "OPENROUTER_MODEL",
        "CHATGPT_MODEL",
    )
    if model:
        config.agents.defaults.model = model
    provider = _first_nonempty_env(
        "VIOLA_AGENTS__DEFAULTS__PROVIDER",
        "VIOLA_AGENTS_DEFAULTS_PROVIDER",
    )
    if provider:
        config.agents.defaults.provider = provider
    tz = _first_nonempty_env(
        "VIOLA_AGENTS__DEFAULTS__TIMEZONE",
        "VIOLA_AGENTS_DEFAULTS_TIMEZONE",
    )
    if tz:
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(tz)
        except Exception:
            logger.warning(
                "Ignoring invalid VIOLA_AGENTS__DEFAULTS__TIMEZONE={!r} (unknown IANA timezone)",
                tz,
            )
        else:
            config.agents.defaults.timezone = tz
    per_user = (
        _first_nonempty_env(
            "VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACES",
            "VIOLA_AGENTS_DEFAULTS_PER_USER_WORKSPACES",
        )
        .strip()
        .lower()
    )
    if per_user in ("1", "true", "yes", "on"):
        config.agents.defaults.per_user_workspaces = True
    elif per_user in ("0", "false", "no", "off"):
        config.agents.defaults.per_user_workspaces = False
    workspace_root = _first_nonempty_env(
        "VIOLA_AGENTS__DEFAULTS__PER_USER_WORKSPACE_ROOT",
        "VIOLA_AGENTS_DEFAULTS_PER_USER_WORKSPACE_ROOT",
    )
    if workspace_root:
        config.agents.defaults.per_user_workspace_root = workspace_root


def _apply_channels_env_overrides(config: Config) -> None:
    """Overlay ``VIOLA_CHANNELS__*`` env vars (e.g. Docker / .env) onto ``channels``."""
    p = os.environ.get("VIOLA_CHANNELS__TRANSCRIPTION_PROVIDER")
    if p and p.strip():
        config.channels.transcription_provider = p.strip()
    m = os.environ.get("VIOLA_CHANNELS__TRANSCRIPTION_MODEL")
    if m and m.strip():
        config.channels.transcription_model = m.strip()
    lang = os.environ.get("VIOLA_CHANNELS__TRANSCRIPTION_LANGUAGE")
    if lang and lang.strip():
        config.channels.transcription_language = lang.strip()


def _apply_ssrf_whitelist(config: Config) -> None:
    """Apply SSRF whitelist from config to the network security module."""
    from viola.security.network import configure_ssrf_whitelist

    configure_ssrf_whitelist(config.tools.ssrf_whitelist)


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(mode="json", by_alias=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


_ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def resolve_config_env_vars(config: Config) -> Config:
    """Return *config* with ``${VAR}`` env-var references resolved.

    Walks in place so fields declared with ``exclude=True`` (e.g.
    ``DreamConfig.cron``) survive; returns the same instance when no
    references are present. Raises ``ValueError`` if a referenced
    variable is not set.
    """
    return _resolve_in_place(config)


def _resolve_in_place(obj: Any) -> Any:
    if isinstance(obj, str):
        new = _ENV_REF_PATTERN.sub(_env_replace, obj)
        return new if new != obj else obj
    if isinstance(obj, BaseModel):
        updates: dict[str, Any] = {}
        for name in type(obj).model_fields:
            old = getattr(obj, name)
            new = _resolve_in_place(old)
            if new is not old:
                updates[name] = new
        extras = obj.__pydantic_extra__
        new_extras: dict[str, Any] | None = None
        if extras:
            resolved = {k: _resolve_in_place(v) for k, v in extras.items()}
            if any(resolved[k] is not extras[k] for k in extras):
                new_extras = resolved
        if not updates and new_extras is None:
            return obj
        copy = obj.model_copy(update=updates) if updates else obj.model_copy()
        if new_extras is not None:
            copy.__pydantic_extra__ = new_extras
        return copy
    if isinstance(obj, dict):
        resolved = {k: _resolve_in_place(v) for k, v in obj.items()}
        return resolved if any(resolved[k] is not obj[k] for k in obj) else obj
    if isinstance(obj, list):
        resolved = [_resolve_in_place(v) for v in obj]
        return resolved if any(nv is not ov for nv, ov in zip(resolved, obj)) else obj
    return obj


def _resolve_env_vars(obj: object) -> object:
    """Recursively resolve ``${VAR}`` patterns in plain strings/dicts/lists."""
    if isinstance(obj, str):
        return _ENV_REF_PATTERN.sub(_env_replace, obj)
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(v) for v in obj]
    return obj


def _env_replace(match: re.Match[str]) -> str:
    name = match.group(1)
    value = os.environ.get(name)
    if value is None:
        raise ValueError(
            f"Environment variable '{name}' referenced in config is not set"
        )
    return value


def _migrate_config(data: dict) -> dict:
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")

    # Move tools.myEnabled / tools.mySet → tools.my.{enable, allowSet}.
    # The old flat keys shipped in the initial MyTool landing; wrapping them in a
    # sub-config keeps `web` / `exec` / `my` symmetric and gives room to grow.
    if "myEnabled" in tools or "mySet" in tools:
        my_cfg = tools.setdefault("my", {})
        if "myEnabled" in tools and "enable" not in my_cfg:
            my_cfg["enable"] = tools.pop("myEnabled")
        else:
            tools.pop("myEnabled", None)
        if "mySet" in tools and "allowSet" not in my_cfg:
            my_cfg["allowSet"] = tools.pop("mySet")
        else:
            tools.pop("mySet", None)

    return data
