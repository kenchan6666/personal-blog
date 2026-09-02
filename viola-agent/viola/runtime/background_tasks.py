"""Cron + heartbeat wiring for ``viola serve`` (WhatsApp / API channel)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from viola.runtime.whatsapp_outbound import (
    deliver_whatsapp_text,
    whatsapp_recipient_from_session_key,
)

if TYPE_CHECKING:
    from viola.agent.loop import AgentLoop
    from viola.config.schema import Config
    from viola.cron.registry import CronRegistry
    from viola.cron.service import CronService
    from viola.cron.types import CronJob
    from viola.heartbeat.service import HeartbeatService
    from viola.session.manager import SessionManager


@dataclass
class ApiBackgroundHandles:
    cron: CronService | CronRegistry
    heartbeat: HeartbeatService
    _startup_task: asyncio.Task | None = None


def _pick_api_heartbeat_target(session_manager: SessionManager) -> tuple[str, str, str | None]:
    """Return (channel, chat_id, session_key) for the most recent WhatsApp API session."""
    for item in session_manager.list_sessions():
        key = item.get("key") or ""
        if not key.startswith("api:"):
            continue
        if whatsapp_recipient_from_session_key(key):
            return "api", "default", key
    return "api", "default", None


def install_api_background_tasks(
    config: Config,
    agent: AgentLoop,
    session_manager: SessionManager,
) -> ApiBackgroundHandles | None:
    """Create cron/heartbeat services for API mode when enabled in config."""
    if not config.api.background_tasks:
        return None

    from viola.agent.tools.cron import CronTool
    from viola.agent.tools.message import MessageTool
    from viola.cron.registry import CronRegistry, create_cron_backend
    from viola.cron.types import CronJob, CronPayload
    from viola.heartbeat.service import HeartbeatService

    hb_cfg = config.gateway.heartbeat
    cron = agent.cron_service
    if cron is None:
        cron = create_cron_backend(
            config.workspace_path,
            per_user_workspaces=config.agents.defaults.per_user_workspaces,
        )
        agent.cron_service = cron
    if isinstance(cron, CronRegistry):
        cron.bind(agent)

    message_tool = agent.tools.get("message")

    async def on_cron_job(job: CronJob) -> str | None:
        if job.name == "dream":
            try:
                seen: set[int] = set()
                for runtime in agent._workspace_runtimes.values():
                    token = id(runtime.dream)
                    if token in seen:
                        continue
                    seen.add(token)
                    await runtime.dream.run()
                logger.info("Dream cron job completed")
            except Exception:
                logger.exception("Dream cron job failed")
            return None

        from viola.utils.evaluator import evaluate_response

        reminder_note = (
            "The scheduled time has arrived. Deliver this reminder to the user now, "
            "as a brief and natural message in their language. Speak directly to them — "
            "do not narrate progress, summarize, include user IDs, or add status reports "
            "like 'Done' or 'Reminded'.\n\n"
            f"Reminder: {job.payload.message}"
        )

        cron_tool = agent.tools.get("cron")
        cron_token = None
        if isinstance(cron_tool, CronTool):
            cron_token = cron_tool.set_cron_context(True)

        async def _silent(*_args: Any, **_kwargs: Any) -> None:
            pass

        session_key = job.payload.session_key or f"api:{job.payload.to}"
        try:
            resp = await agent.process_direct(
                reminder_note,
                session_key=session_key,
                channel=job.payload.channel or "api",
                chat_id=job.payload.to or "default",
                on_progress=_silent,
            )
        finally:
            if isinstance(cron_tool, CronTool) and cron_token is not None:
                cron_tool.reset_cron_context(cron_token)

        response = resp.content if resp else ""

        if job.payload.deliver and isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
            return response

        if job.payload.deliver and response:
            should_notify = await evaluate_response(
                response, reminder_note, agent.provider, agent.model,
            )
            if should_notify:
                delivered = await deliver_whatsapp_text(
                    response,
                    session_key=session_key,
                    channel_meta=job.payload.channel_meta,
                    session_manager=session_manager,
                )
                if not delivered:
                    logger.warning(
                        "Cron job '{}' deliver failed (no WhatsApp recipient for session_key={})",
                        job.name,
                        session_key,
                    )
        return response

    cron.on_job = on_cron_job

    heartbeat_preamble = (
        "[Your response will be delivered directly to the user's WhatsApp. "
        "Output ONLY the final user-facing message. Never reference internal "
        "files (HEARTBEAT.md, AWARENESS.md, etc.), your instructions, or your "
        "decision process. If nothing needs reporting, respond with just "
        "'All clear.' and nothing else.]\n\n"
    )

    async def on_heartbeat_execute(tasks: str) -> str:
        channel, chat_id, session_key = _pick_api_heartbeat_target(session_manager)

        async def _silent(*_args: Any, **_kwargs: Any) -> None:
            pass

        resp = await agent.process_direct(
            heartbeat_preamble + tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

        session = agent.sessions.get_or_create("heartbeat")
        session.retain_recent_legal_suffix(hb_cfg.keep_recent_messages)
        agent.sessions.save(session)

        return resp.content if resp else ""

    async def on_heartbeat_notify(response: str) -> None:
        _, _, session_key = _pick_api_heartbeat_target(session_manager)
        if not session_key:
            logger.info("Heartbeat: no API WhatsApp session to deliver to")
            return
        await deliver_whatsapp_text(
            response,
            session_key=session_key,
            session_manager=session_manager,
        )

    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        llm_runtime=agent.llm_runtime,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
        timezone=config.agents.defaults.timezone,
    )

    dream_cfg = config.agents.defaults.dream
    if dream_cfg.model_override:
        agent.dream.model = dream_cfg.model_override
    agent.dream.max_batch_size = dream_cfg.max_batch_size
    agent.dream.max_iterations = dream_cfg.max_iterations
    agent.dream.annotate_line_ages = dream_cfg.annotate_line_ages
    cron.register_system_job(CronJob(
        id="dream",
        name="dream",
        schedule=dream_cfg.build_schedule(config.agents.defaults.timezone),
        payload=CronPayload(kind="system_event"),
    ))

    agent.cron_service = cron
    return ApiBackgroundHandles(cron=cron, heartbeat=heartbeat)


async def start_api_background_tasks(handles: ApiBackgroundHandles) -> None:
    await handles.cron.start()
    await handles.heartbeat.start()
    logger.info(
        "API background tasks started (cron jobs={}, heartbeat every {}s)",
        len(handles.cron.list_jobs(include_disabled=True)),
        handles.heartbeat.interval_s,
    )


def stop_api_background_tasks(handles: ApiBackgroundHandles) -> None:
    handles.heartbeat.stop()
    handles.cron.stop()
