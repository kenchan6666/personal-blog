"""Tests for HeartbeatService._is_deliverable and _tick suppression."""

import pytest

from viola.heartbeat.service import HeartbeatService
from viola.providers.base import LLMResponse, ToolCallRequest


class TestIsDeliverable:
    """Verify the pre-evaluator deliverability filter."""

    def test_normal_report_is_deliverable(self):
        assert HeartbeatService._is_deliverable(
            "2 new emails — invoice from Zain, meeting rescheduled to 3pm."
        )

    def test_short_dismissal_is_deliverable(self):
        assert HeartbeatService._is_deliverable("All clear.")

    def test_finalization_fallback_blocked(self):
        assert not HeartbeatService._is_deliverable(
            "I completed the tool steps but couldn't produce a final answer. "
            "Please try again or narrow the task."
        )

    def test_leaked_heartbeat_md_reference_blocked(self):
        assert not HeartbeatService._is_deliverable(
            "Yes — HEARTBEAT.md has active tasks listed. They are: "
            "Check Gmail for important messages, Check Calendar."
        )

    def test_case_insensitive(self):
        assert not HeartbeatService._is_deliverable(
            "HEARTBEAT.MD has tasks listed."
        )


class TestTickSuppressesNonDeliverable:
    """Non-deliverable Phase-2 output must not reach evaluator or notify."""

    @pytest.mark.asyncio
    async def test_tick_skips_notify_on_leaked_reasoning(self, tmp_path):
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("## Active Tasks\n- Check inbox\n", encoding="utf-8")

        notified: list[str] = []

        async def on_execute(_tasks: str) -> str:
            return "HEARTBEAT.md says to check inbox — decision logic: report."

        async def on_notify(text: str) -> None:
            notified.append(text)

        from viola.utils.llm_runtime import static_llm_runtime

        class _Provider:
            async def chat_with_retry(self, **_kwargs):
                return LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCallRequest(id="1", name="heartbeat", arguments={"action": "run", "tasks": "inbox"}),
                    ],
                    finish_reason="tool_calls",
                )

        svc = HeartbeatService(
            workspace=tmp_path,
            llm_runtime=static_llm_runtime(_Provider(), "test"),
            on_execute=on_execute,
            on_notify=on_notify,
            interval_s=60,
            enabled=True,
        )
        await svc._tick()
        assert notified == []
