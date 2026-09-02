"""Shared workspace path resolution for tools that walk or touch the workspace.

The interactive agent does not expose generic read/write/list-dir tools; durable
artifacts are persisted via MCP / backend APIs. This module only provides the
path sandbox (_FsTool) used by grep, glob, notebook editing, and Dream's
internal consolidation helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from viola.agent.tools.base import Tool
from viola.agent.tools.file_state import FileStates, current_file_states
from viola.config.paths import get_media_dir

_FS_WORKSPACE_BOUNDARY_NOTE = (
    " (this is a hard policy boundary, not a transient failure; "
    "do not retry with shell tricks or alternative tools, and ask "
    "the user how to proceed if the resource is genuinely required)"
)


def _resolve_path(
    path: str,
    workspace: Path | None = None,
    allowed_dir: Path | None = None,
    extra_allowed_dirs: list[Path] | None = None,
) -> Path:
    """Resolve path against workspace (if relative) and enforce directory restriction."""
    p = Path(path).expanduser()
    if not p.is_absolute() and workspace:
        p = workspace / p
    resolved = p.resolve()
    if allowed_dir:
        media_path = get_media_dir().resolve()
        all_dirs = [allowed_dir] + [media_path] + (extra_allowed_dirs or [])
        if not any(_is_under(resolved, d) for d in all_dirs):
            raise PermissionError(
                f"Path {path} is outside allowed directory {allowed_dir}"
                + _FS_WORKSPACE_BOUNDARY_NOTE
            )
    return resolved


def _is_under(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory.resolve())
        return True
    except ValueError:
        return False


# Default directories skipped when walking the workspace (grep/glob).
IGNORE_WALK_DIRS: frozenset[str] = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".coverage", "htmlcov",
})


class _FsTool(Tool):
    """Shared base — workspace roots and path resolution for workspace-scoped tools."""

    def __init__(
        self,
        workspace: Path | None = None,
        allowed_dir: Path | None = None,
        extra_allowed_dirs: list[Path] | None = None,
        file_states: FileStates | None = None,
    ):
        self._workspace = workspace
        self._allowed_dir = allowed_dir
        self._extra_allowed_dirs = extra_allowed_dirs
        self._explicit_file_states = file_states
        self._fallback_file_states = FileStates()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        from viola.agent.skills import BUILTIN_SKILLS_DIR

        restrict = (
            ctx.config.restrict_to_workspace
            or ctx.config.exec.sandbox
        )
        allowed_dir = Path(ctx.workspace) if restrict else None
        extra_read = [BUILTIN_SKILLS_DIR] if allowed_dir else None
        return cls(
            workspace=Path(ctx.workspace),
            allowed_dir=allowed_dir,
            extra_allowed_dirs=extra_read,
            file_states=ctx.file_state_store,
        )

    @property
    def _file_states(self) -> FileStates:
        if self._explicit_file_states is not None:
            return self._explicit_file_states
        return current_file_states(self._fallback_file_states)

    def _resolve(self, path: str) -> Path:
        return _resolve_path(path, self._workspace, self._allowed_dir, self._extra_allowed_dirs)
