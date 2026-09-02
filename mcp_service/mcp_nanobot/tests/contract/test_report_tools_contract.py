from __future__ import annotations


def test_report_tool_contract(task_tools, run_tools, report_tools) -> None:
    task_id = task_tools.task_create(title="Report flow", bearer="token-ok")["task"]["task_id"]
    run_tools.run_trigger(task_id=task_id, bearer="token-ok")

    summary = report_tools.report_task_summary(bearer="token-ok")
    assert summary["ok"] is True
    assert "by_status" in summary

    failure = report_tools.report_failure_breakdown(bearer="token-ok")
    assert failure["ok"] is True

    latency = report_tools.report_runtime_latency(bearer="token-ok")
    assert latency["ok"] is True
    assert "p95_ms" in latency
