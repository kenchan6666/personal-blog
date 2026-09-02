"""Context builder for assembling agent prompts."""

import base64
import hashlib
import logging
import mimetypes
import os
import platform
import re
from contextlib import suppress
from importlib.resources import files as pkg_files
from pathlib import Path
from typing import Any
from viola.session.goal_state import goal_state_runtime_lines
from viola.agent.tools import mcp as mcp_tools
from viola.bus.events import InboundMessage
from viola.agent.memory import MemoryStore
from viola.agent.skills import SkillsLoader
from viola.agent.tools.registry import ToolRegistry
from viola.utils.helpers import (
    current_time_str,
    detect_image_mime,
    truncate_text,
)
from typing import Mapping, Sequence

from viola.utils.prompt_templates import render_template

_log = logging.getLogger(__name__)

# Regex that matches the entire backend-generated block (including the leading blank line).
_SOUL_RE = re.compile(
    r"\n*<!-- soulnote-start[^>]*-->\n.*?\n<!-- soulnote-end -->",
    re.DOTALL,
)


# Tools withheld from LLM-facing definitions on ``channel=api`` (WhatsApp / OpenAI-compat API).
API_CHANNEL_HIDDEN_TOOLS: frozenset[str] = frozenset({"cron"})


def api_channel_hidden_tools(*, allow_scheduling: bool) -> frozenset[str]:
    """Return tool names hidden on channel=api."""
    if allow_scheduling:
        return frozenset()
    return API_CHANNEL_HIDDEN_TOOLS


def _load_mcp_fragment() -> dict[str, Any]:
    """Load MCP fragment JSON from installed helper packages; returns {} when absent."""
    import json as _json

    from importlib.resources import files as _res_files

    merged: dict[str, Any] = {}
    for package_name in ("mcp_common", "mcp_nanobot.mcp_common"):
        try:
            text = (_res_files(package_name) / "fragment.json").read_text(encoding="utf-8")
            fragment = _json.loads(text)
            if isinstance(fragment, dict):
                merged.update(fragment)
        except Exception:
            continue
    return merged


def _build_api_channel_discipline(*, allow_scheduling: bool = False) -> str:
    """Build the backend/MCP discipline block injected into every ``channel=api`` system prompt.

    Domain table rows, tool map sections, and capabilities list are generated automatically
    from ``mcp_common/fragment.json`` ``contextMeta`` blocks.  To add a new domain:
    add a server entry with ``contextMeta`` to ``fragment.json`` — no edits here required.

    ``contextMeta`` schema per server entry:
      domain (str)              — logical domain name used in Step 1 table and tool map header
      domainWhen (str)          — "Pick when user talks about…" cell text
      capabilityLabel (str)     — shown in the "You MAY mention" capabilities list
      toolMap (dict)            — {column_label: [tool, ...]} ordered; keys become table headers
      notes (str, optional)     — per-domain note appended after the tool map row
      extraDomainRows (list)    — [{domain, domainWhen}] extra Step 1 rows sharing this server
      extraToolMapNotes (list)  — free-text lines prepended before this server's tool map table
    """
    fragment = _load_mcp_fragment()
    customer_service_only = (
        (os.environ.get("VIOLA_CUSTOMER_SERVICE_ONLY") or "true").strip().lower()
        not in ("0", "false", "no", "off")
    )

    domain_table_rows: list[str] = []
    tool_map_sections: list[str] = []
    capability_labels: list[str] = []

    for server_name, server_cfg in fragment.items():
        meta = server_cfg.get("contextMeta")
        if not meta:
            continue

        domain = meta["domain"]
        prefix = f"mcp_{server_name}_"

        # Extra Step-1 rows sharing this server (e.g. "users" on backend-projects)
        for extra in meta.get("extraDomainRows", []):
            domain_table_rows.append(
                f"| **{extra['domain']}** | {extra['domainWhen']} | ``{server_name}`` | ``{prefix}`` |"
            )

        # Main Step-1 row
        domain_table_rows.append(
            f"| **{domain}** | {meta['domainWhen']} | ``{server_name}`` | ``{prefix}`` |"
        )

        # Extra tool map notes prepended before this server's table
        for note in meta.get("extraToolMapNotes", []):
            tool_map_sections.append(note)

        # Tool map table (column labels = toolMap keys; values = comma-joined tool names)
        tool_map: dict[str, list[str]] = meta.get("toolMap", {})
        col_labels = " | ".join(tool_map.keys())
        col_values = " | ".join(
            (", ".join(f"``{t}``" for t in tools) if tools else "—")
            for tools in tool_map.values()
        )
        section_lines = [
            f"**{domain}** (``{prefix}``):",
            f"| {col_labels} |",
            f"| {col_values} |",
        ]
        if meta.get("notes"):
            section_lines.append(meta["notes"])
        tool_map_sections.append("\n".join(section_lines))

        if meta.get("capabilityLabel"):
            capability_labels.append(meta["capabilityLabel"])

    if not domain_table_rows:
        return ""

    domain_table = (
        "| Domain | Pick when the user talks about… | MCP server | Prefix |\n"
        + "\n".join(domain_table_rows)
    )
    capabilities = ", ".join(capability_labels)

    if customer_service_only:
        return (
            "## HTTP API channel — customer-service-only mode (mandatory)\n\n"
            "This assistant is **customer service only**. It can answer questions and provide guidance, "
            "but it must **not** create/update/delete business entities.\n\n"
            "### Hard rules\n"
            "- Never call mutating tools (create/update/delete/cancel/retry/trigger/transition).\n"
            "- Never claim any project/order/quotation/invoice was created or updated.\n"
            "- If the user asks for create/update/delete actions, clearly refuse and ask them to contact internal staff.\n"
            "- Prefer read-only tools for lookup and explanation; if data is unavailable, state that directly.\n\n"
            "### User-visible scope\n"
            "- You may help with customer support Q&A, issue clarification, troubleshooting guidance, and status explanation.\n"
            "- You must not advertise or imply permissions for backend write operations."
        )

    return (
        "## HTTP API channel \u2014 backend / MCP discipline (mandatory)\n\n"
        "Traffic on this channel often originates from WhatsApp. MCP persistence is **only** via MCP tools.\n"
        "Tool names are **exact strings** (``mcp_<server>_<tool>``; hyphens matter) \u2014 not shorter aliases.\n\n"
        "Before any tool call, run this **two-step classification** (mentally or in one short plan line):\n\n"
        "### Step 1 \u2014 Domain (what entity?)\n\n"
        "Pick **one primary domain** from the user message. If ambiguous, ask once before mutating.\n\n"
        + domain_table + "\n\n"
        "**Cross-domain helper:** creating a **project** or **quotation** usually needs a **read** on **clients** first "
        "(``clients_search`` on the **same server** as the mutation) to get ``client_id``. "
        "That is Step 2 **read**, not a domain change.\n\n"
        "### Step 2 \u2014 Action (CRUD?)\n\n"
        "| Action | User intent | What to do |\n"
        "| **create** | add / new / \u65b0\u5efa | Call the domain\u2019s **create** tool; pass ``mobile_digits`` from ``[Sender mobile_digits: ...]`` |\n"
        "| **read** | list / show / search / count / get / \u67e5 | Call **search**, **list**, or **get**; use JSON ``items`` and ``total`` \u2014 never invent rows |\n"
        "| **update** | change / edit / \u66f4\u65b0 / status | Call **update** only with fields the user **explicitly** gave; if none, read current record and ask what to change \u2014 never claim updated from GET/search alone |\n"
        "| **delete** | remove / \u5220\u9664 | Call **delete** after confirming ``*_id`` when the user was vague |\n\n"
        "If Step 2 is **create** or **update**/**delete** and the user already gave enough detail, "
        "**call tools in the same turn** \u2014 do not end with only \u201cI will\u2026\u201d.\n\n"
        "### Tool map (domain \xd7 action)\n\n"
        "Use tools from **your available tool list** only. Full names = prefix + suffix below.\n\n"
        + "\n\n".join(tool_map_sections) + "\n\n"
        "### Hard rules (all domains)\n"
        "- **Never** claim success without a tool call whose output shows success (HTTP 2xx JSON).\n"
        "- **Never** claim **updated** from GET/search alone; on update with no fields given, read and ask what to change.\n"
        "- **Never** use ``exec`` or workspace files to persist MCP business data.\n"
        "- **Do not** repeat ``clients_search`` with rephrased queries when prior calls already returned no usable ``client_id``.\n"
        "- If no tool fits or the tool errors, say so plainly.\n\n"
        "### User-visible capabilities (mandatory \u2014 this HTTP API channel)\n"
        "When the user asks what you can do, requests a greeting with feature lists, or you summarize how you help "
        "(e.g. \u4f60\u80fd\u505a\u4ec0\u9ebc / \u6709\u4ec0\u9ebc\u529f\u80fd / \u300c\u53ef\u4ee5\u5e6b\u6211\u2026\u300d\u5f15\u8a00):\n\n"
        "**You MAY** mention helping with:\n\n"
        "- Brief general conversation and factual Q&A grounded in reliable sources "
        "(\u5c0d\u8a71\uff0f\u4e00\u822c\u8cc7\u6599\u67e5\u554f\u8207\u89e3\u91cb)\uff1buse tools where facts matter.\n"
        f"- **MCP-backed workflows only**, as documented above: {capabilities}; "
        "plus read-only internal user listing where tools allow.\n\n"
        + (
            ""
            if allow_scheduling
            else (
                "**You MUST NOT** advertise, imply, invite, or list as available \u2014 even if other workspace docs mentioned them \u2014 "
                "**reminders / timers / \u300c\u63d0\u9192\u300d\u300c\u5b9a\u6642\u300d\u300c\u9031\u671f\u4efb\u52d9\u300d\u300c\u6392\u7a0b\u300d\u300ccron\u300d\u300cHEARTBEAT\u300d\u985e\u901a\u77e5\u8a2d\u7f6e**, "
                "nor **analytics, BI dashboards, KPI / trend reports \u300c\u6578\u64da\u5206\u6790\u300d\u300c\u7d71\u8a08\u5831\u8868\u300d\u300c\u5100\u8868\u677f\u300d**. "
                "Those are **\u66ab\u4e0d\u53ef\u7528** on this assistant; if asked directly, say so clearly once instead of "
                "refusing vaguely or promising them later unless product operators re-enable them.\n\n"
                "**Conflict resolution:** Earlier bootstrap snippets (AGENTS.md, TOOLS.md, skill summaries about scheduling or analytics) \u2014 "
                "**defer to this section** when replying through this WhatsApp-linked API."
            )
        )
        + (
            "\n\n**Scheduled tasks (enabled):** Use the `cron` tool for one-shot reminders; use `HEARTBEAT.md` for recurring checks. "
            "Do not claim a reminder is set unless `cron` add succeeded or HEARTBEAT.md was updated."
            if allow_scheduling
            else ""
        )
    )


def _backend_mcp_runtime_hint() -> str:
    """Describe which backend MCP servers are expected at runtime.

    Derived automatically from installed MCP ``fragment.json`` files.
    """
    fragment = _load_mcp_fragment()
    active: list[str] = []
    disabled: list[str] = []
    for server_name, server_cfg in fragment.items():
        opt_out_var = f"VIOLA_TOOLS_{server_name.upper().replace('-', '_')}_MCP"
        tools_summary = ", ".join(server_cfg.get("enabledTools", []))
        if os.environ.get(opt_out_var, "").strip().lower() in ("0", "false", "no", "off"):
            disabled.append(f"``{server_name}`` ({tools_summary})")
        else:
            active.append(f"``{server_name}`` → ``mcp_{server_name}_*`` ({tools_summary})")
    lines = ["[Backend MCP runtime] Backend calls use ``INTERNAL_SECRET`` + ``BACKEND_API_BASE_URL``."]
    if active:
        lines.append("Registered (unless startup failed): " + "; ".join(active) + ".")
    if disabled:
        lines.append(
            "Disabled via env: " + ", ".join(disabled) + ". "
            "If a tool is missing from your list, say which server is off — do not invent data."
        )
    if not os.environ.get("INTERNAL_SECRET", "").strip():
        lines.append(
            "``INTERNAL_SECRET`` is **not** set — MCP HTTP calls to the backend may fail; "
            "report errors plainly."
        )
    return "\n".join(lines)


def _custom_knowledge_prompt_addon() -> str:
    """Optional migration hook for preserving custom knowledge/prompt constraints."""
    rules = (os.environ.get("VIOLA_CUSTOM_KNOWLEDGE_RULES") or "").strip()
    style = (os.environ.get("VIOLA_CUSTOM_STYLE_RULES") or "").strip()
    if not rules and not style:
        return ""
    lines = ["## Migration Knowledge/Style Guardrails"]
    if rules:
        lines.append(f"- Knowledge rules: {rules}")
    if style:
        lines.append(f"- Style rules: {style}")
    lines.append("- Prefer these constraints when they do not conflict with tool outputs.")
    return "\n".join(lines)

def _build_agent_soul_section() -> str:
    """Build the backend business-data rules block injected for **all** channels.

    Generated from installed MCP ``fragment.json`` ``contextMeta`` blocks.
    Returns an empty string when the package is absent so viola-agent stays
    fully decoupled from the backend — no backend content appears unless the
    MCP package is installed.

    ``contextMeta`` fields used here:
      domain, domainWhen   — Step 1 domain table
      toolMap              — tool map table (SOUL.md single-backtick style)
      soulNotes (optional) — detailed per-domain notes; falls back to ``notes``
      extraDomainRows      — extra Step 1 rows sharing this server
      extraToolMapNotes    — free-text lines before this server's tool map table
    """
    fragment = _load_mcp_fragment()
    if not fragment:
        return ""

    domain_rows: list[str] = []
    tool_map_sections: list[str] = []
    domain_list_parts: list[str] = []

    for server_name, server_cfg in fragment.items():
        meta = server_cfg.get("contextMeta")
        if not meta:
            continue

        domain = meta["domain"]
        prefix = f"mcp_{server_name}_"
        domain_list_parts.append(f"`{domain}`")

        # Extra Step-1 rows sharing this server (e.g. "users" on backend-projects)
        for extra in meta.get("extraDomainRows", []):
            domain_rows.append(
                f"| {extra['domain']} | {extra['domainWhen']} | `{prefix}` |"
            )

        # Main Step-1 row
        domain_rows.append(f"| {domain} | {meta['domainWhen']} | `{prefix}` |")

        # Optional free-text notes before the tool map table
        for note in meta.get("extraToolMapNotes", []):
            tool_map_sections.append(note)

        # Tool map table in SOUL.md style (single backtick, Title-case column headers)
        tool_map: dict[str, list[str]] = meta.get("toolMap", {})
        col_labels = " | ".join(c.title() for c in tool_map.keys())
        separator = "|".join("---" for _ in tool_map)
        col_values = " | ".join(
            ", ".join(f"`{t}`" for t in tools) if tools else "—"
            for tools in tool_map.values()
        )
        section_lines = [
            f"**{domain}** (`{prefix}`):\n",
            f"| {col_labels} |",
            f"|{separator}|",
            f"| {col_values} |",
        ]

        # Per-domain notes: prefer soulNotes, fall back to notes (strip double-backticks)
        per_domain_notes = meta.get("soulNotes") or meta.get("notes", "")
        if per_domain_notes:
            section_lines.append(per_domain_notes.replace("``", "`"))

        tool_map_sections.append("\n".join(section_lines))

    if not domain_rows:
        return ""

    domain_table = (
        "| Domain | When to pick | MCP prefix |\n"
        "|---|---|---|\n"
        + "\n".join(domain_rows)
    )
    domain_list = ", ".join(domain_list_parts)

    parts = [
        "## Business Data Rules",
        "**All backend business data MUST go through MCP tools — never local files.**\n"
        "Use **exact** tool names from your tool list (`mcp_<server>_<tool>`; hyphens matter).",
        "### Two-step classification (before every backend tool call)\n\n"
        f"**Step 1 \u2014 Domain:** pick one primary entity \u2014 {domain_list}. If ambiguous, ask once before mutating.\n\n"
        + domain_table + "\n\n"
        "**Cross-domain:** creating a project or quotation often needs **read** on clients first "
        "(`clients_search` on the **same server** as the mutation) to get `client_id` \u2014 "
        "that is Step 2 read, not a domain switch.\n\n"
        "**Step 2 \u2014 Action:** `create` | `read` | `update` | `delete` \u2014 match user intent "
        "(\u65b0\u5efa / \u67e5 / \u66f4\u65b0 / \u5220\u9664). On create with enough detail, call tools in the same turn. "
        "On **update**, call PATCH only when the user named specific fields to change; otherwise read and ask. "
        "On read, use JSON `items` and `total` \u2014 never invent rows.",
        "### Tool map (domain \xd7 action)\n\nFull name = prefix + suffix. Use only tools present in your list.\n\n"
        + "\n\n".join(tool_map_sections),
        "### Hard rules\n\n"
        "- Never use `exec` or workspace files to persist business data (projects, clients, quotations, invoices, etc.).\n"
        "- Never write business data into `memory/MEMORY.md` or other workspace files.\n"
        "- Never claim success without a tool call whose output shows success (HTTP 2xx JSON).\n"
        "- Never claim **updated** from `*_get` / `*_search` alone \u2014 only from a successful **update** tool.\n"
        "- On **update**, pass only fields the user explicitly asked to change; do not re-submit unchanged values from a prior read.\n"
        "- If a tool is missing or errors, report it \u2014 do **not** fall back to local storage.\n"
        "- Do **not** repeat `clients_search` with rephrased queries when prior calls already returned no usable `client_id`.",
        "### WhatsApp sender identity\n\n"
        "WhatsApp messages (including via the HTTP API bridge) include `[Sender mobile_digits: 85264760285]` (digits only). "
        "**Pass this as `mobile_digits` on every backend write** (create / update / delete) \u2014 required for authorization. "
        "Do not ask for their phone number; read it from that line.",
    ]
    return "\n\n".join(parts)


def _sync_agent_soul(workspace: Path) -> None:
    """Sync the backend business-data rules block into ``workspace/SOUL.md``.

    Runs **once per agent startup** (called from ``ContextBuilder.__init__``).
    Uses HTML comment markers to find and replace only the generated section,
    leaving any human-authored content above/below it untouched.

    Skip conditions (no file write):
    - No MCP fragment installed → remove the block if present.
    - Fragment hash hasn't changed since last write → no-op.

    Marker format::

        <!-- soulnote-start hash=<8-char-md5> -->
        ...generated content...
        <!-- soulnote-end -->
    """
    new_section = _build_agent_soul_section()
    content_hash = hashlib.md5(new_section.encode()).hexdigest()[:8] if new_section else ""

    soul_path = workspace / "SOUL.md"

    if soul_path.exists():
        existing = soul_path.read_text(encoding="utf-8")
    else:
        # Bootstrap from the bundled template when the workspace file doesn't exist yet.
        try:
            existing = (pkg_files("viola") / "templates" / "SOUL.md").read_text(encoding="utf-8")
        except Exception:
            existing = ""

    # Fast-path: hash already in file → nothing changed.
    if content_hash and f"<!-- soulnote-start hash={content_hash} -->" in existing:
        return

    if new_section:
        marked = (
            f"\n\n<!-- soulnote-start hash={content_hash} -->\n"
            f"{new_section}\n"
            f"<!-- soulnote-end -->"
        )
        if _SOUL_RE.search(existing):
            updated = _SOUL_RE.sub(marked, existing)
        else:
            updated = existing.rstrip() + marked + "\n"
        _log.info("SOUL.md backend section synced (hash=%s)", content_hash)
    else:
        # mcp_common not installed — remove stale block if present.
        if not _SOUL_RE.search(existing):
            return
        updated = _SOUL_RE.sub("", existing).rstrip() + "\n"
        _log.info("SOUL.md backend section removed (no MCP fragment installed)")

    workspace.mkdir(parents=True, exist_ok=True)
    soul_path.write_text(updated, encoding="utf-8")



def _cli_app_session_extra(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    cli_apps = metadata.get("cli_apps") if isinstance(metadata, Mapping) else None
    return {"cli_apps": cli_apps} if isinstance(cli_apps, list) and cli_apps else {}


def _cli_app_runtime_lines(msg: Any, workspace: Path, *, skip: bool = False) -> list[str]:
    if skip:
        return []
    text = msg.content if isinstance(getattr(msg, "content", None), str) else ""
    metadata = msg.metadata if isinstance(getattr(msg, "metadata", None), Mapping) else None
    structured = metadata.get("cli_apps") if isinstance(metadata, Mapping) else None
    if isinstance(structured, list):
        mentions = [
            item for item in structured
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        ]
        if mentions:
            return [
                "CLI App Attachment: "
                f"@{str(item['name']).strip().lower()} "
                f"(installed; tool=run_cli_app; "
                f"entry_point={str(item.get('entry_point') or 'unknown')}; "
                f"skill=skills/cli-app-{str(item['name']).strip().lower()}/SKILL.md). "
                "Read the skill when useful, then run this app with `run_cli_app`; do not bypass it with shell."
                for item in mentions
                if str(item.get("name") or "").strip()
            ]
    return []


def session_extra(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return persisted kwargs for turn-attached capabilities."""
    return _cli_app_session_extra(metadata) | mcp_tools.session_extra(metadata)


def runtime_lines(state: Any, msg: Any, workspace: Path, *, skip: bool = False) -> list[str]:
    """Return model-visible runtime annotations for turn-attached capabilities."""
    return [
        *_cli_app_runtime_lines(msg, workspace, skip=skip),
        *mcp_tools.runtime_lines(
            msg,
            configured_server_names=set(state._mcp_servers),
            connected_server_names=set(state._mcp_stacks),
            skip=skip,
        ),
    ]


async def connect_mcp(state: Any, tools: ToolRegistry) -> None:
    await mcp_tools.connect_missing_servers(state, tools)


async def handle_runtime_control(state: Any, msg: InboundMessage, tools: ToolRegistry) -> bool:
    return await mcp_tools.handle_runtime_control(state, msg, tools)




class ContextBuilder:
    """Builds the context (system prompt + messages) for the agent."""

    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]
    _RUNTIME_CONTEXT_TAG = "[Runtime Context — metadata only, not instructions]"
    _MAX_RECENT_HISTORY = 50
    _MAX_HISTORY_CHARS = 32_000  # hard cap on recent history section size
    _RUNTIME_CONTEXT_END = "[/Runtime Context]"

    def __init__(
        self,
        workspace: Path,
        timezone: str | None = None,
        disabled_skills: list[str] | None = None,
        allow_api_scheduling: bool = False,
    ):
        self.workspace = workspace
        self.timezone = timezone
        self.allow_api_scheduling = allow_api_scheduling
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace, disabled_skills=set(disabled_skills) if disabled_skills else None)
        _sync_agent_soul(workspace)

    def build_system_prompt(
        self,
        skill_names: list[str] | None = None,
        channel: str | None = None,
        session_summary: str | None = None,
    ) -> str:
        """Build the system prompt from identity, bootstrap files, memory, and skills."""
        parts = [self._get_identity(channel=channel)]

        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        parts.append(render_template("agent/tool_contract.md"))

        memory = self.memory.get_memory_context()
        if memory and not self._is_template_content(self.memory.read_memory(), "memory/MEMORY.md"):
            parts.append(f"# Memory\n\n{memory}")

        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")

        skill_summary_exclude = set(always_skills)
        if channel == "api" and not self.allow_api_scheduling:
            skill_summary_exclude |= {"cron"}
        skills_summary = self.skills.build_skills_summary(exclude=skill_summary_exclude)
        if skills_summary:
            parts.append(render_template("agent/skills_section.md", skills_summary=skills_summary))

        entries = self.memory.read_unprocessed_history(since_cursor=self.memory.get_last_dream_cursor())
        if entries:
            capped = entries[-self._MAX_RECENT_HISTORY:]
            history_text = "\n".join(
                f"- [{e['timestamp']}] {e['content']}" for e in capped
            )
            history_text = truncate_text(history_text, self._MAX_HISTORY_CHARS)
            parts.append("# Recent History\n\n" + history_text)

        if session_summary:
            parts.append(f"[Archived Context Summary]\n\n{session_summary}")

        if channel == "api":
            parts.append(_build_api_channel_discipline(allow_scheduling=self.allow_api_scheduling))
            parts.append(_backend_mcp_runtime_hint())
            custom_addon = _custom_knowledge_prompt_addon()
            if custom_addon:
                parts.append(custom_addon)
            extra = (os.environ.get("VIOLA_API_EXTRA_SYSTEM_PROMPT") or "").strip()
            if extra:
                parts.append(extra)

        return "\n\n---\n\n".join(parts)

    def _get_identity(self, channel: str | None = None) -> str:
        """Get the core identity section."""
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"

        return render_template(
            "agent/identity.md",
            workspace_path=workspace_path,
            runtime=runtime,
            platform_policy=render_template("agent/platform_policy.md", system=system),
            channel=channel or "",
        )

    @staticmethod
    def _build_runtime_context(
        channel: str | None,
        chat_id: str | None,
        timezone: str | None = None,
        sender_id: str | None = None,
        supplemental_lines: Sequence[str] | None = None,
    ) -> str:
        """Build untrusted runtime metadata block for injection before the user message."""
        lines = [f"Current Time: {current_time_str(timezone)}"]
        if channel and chat_id:
            lines += [f"Channel: {channel}", f"Chat ID: {chat_id}"]
        if sender_id:
            lines += [f"Sender ID: {sender_id}"]
        if supplemental_lines:
            lines.extend(supplemental_lines)
        return ContextBuilder._RUNTIME_CONTEXT_TAG + "\n" + "\n".join(lines) + "\n" + ContextBuilder._RUNTIME_CONTEXT_END

    @staticmethod
    def _merge_message_content(left: Any, right: Any) -> str | list[dict[str, Any]]:
        if isinstance(left, str) and isinstance(right, str):
            return f"{left}\n\n{right}" if left else right

        def _to_blocks(value: Any) -> list[dict[str, Any]]:
            if isinstance(value, list):
                return [item if isinstance(item, dict) else {"type": "text", "text": str(item)} for item in value]
            if value is None:
                return []
            return [{"type": "text", "text": str(value)}]

        return _to_blocks(left) + _to_blocks(right)

    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []

        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")

        return "\n\n".join(parts) if parts else ""

    @staticmethod
    def _is_template_content(content: str, template_path: str) -> bool:
        """Check if *content* is identical to the bundled template (user hasn't customized it)."""
        with suppress(Exception):
            tpl = pkg_files("viola") / "templates" / template_path
            if tpl.is_file():
                return content.strip() == tpl.read_text(encoding="utf-8").strip()
        return False

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        current_role: str = "user",
        sender_id: str | None = None,
        session_metadata: Mapping[str, Any] | None = None,
        session_summary: str | None = None,
        current_runtime_lines: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build the complete message list for an LLM call."""
        extra = [
            *goal_state_runtime_lines(session_metadata),
        ]
        if current_runtime_lines:
            extra.extend(line for line in current_runtime_lines if line)

        runtime_ctx = self._build_runtime_context(channel, chat_id, self.timezone, sender_id=sender_id)
        user_content = self._build_user_content(current_message, media)

        # Merge runtime context and user content into a single user message
        # to avoid consecutive same-role messages that some providers reject.
        if isinstance(user_content, str):
            merged = f"{runtime_ctx}\n\n{user_content}"
        else:
            merged = [{"type": "text", "text": runtime_ctx}] + user_content
        messages = [
            {"role": "system", "content": self.build_system_prompt(skill_names, channel=channel, session_summary=session_summary)},
            *history,
        ]
        if messages[-1].get("role") == current_role:
            last = dict(messages[-1])
            last["content"] = self._merge_message_content(last.get("content"), merged)
            messages[-1] = last
            return messages
        messages.append({"role": current_role, "content": merged})
        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text

        images = []
        for path in media:
            p = Path(path)
            if not p.is_file():
                continue
            raw = p.read_bytes()
            mime = detect_image_mime(raw) or mimetypes.guess_type(path)[0]
            if not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(raw).decode()
            images.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
                "_meta": {"path": str(p)},
            })

        if not images:
            return text
        return images + [{"type": "text", "text": text}]

    def add_tool_result(
        self, messages: list[dict[str, Any]],
        tool_call_id: str, tool_name: str, result: Any,
    ) -> list[dict[str, Any]]:
        """Add a tool result to the message list."""
        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": tool_name, "content": result})
        return messages
