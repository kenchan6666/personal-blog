from __future__ import annotations


def test_run_tool_contract(task_tools, run_tools) -> None:
    created = task_tools.task_create(title="Run flow", bearer="token-ok")
    task_id = created["task"]["task_id"]

    triggered = run_tools.run_trigger(task_id=task_id, bearer="token-ok")
    assert triggered["ok"] is True
    run_id = triggered["run"]["run_id"]

    fetched = run_tools.run_get(run_id=run_id, bearer="token-ok")
    assert fetched["ok"] is True

    logs = run_tools.run_logs(run_id=run_id, bearer="token-ok")
    assert logs["ok"] is True
    assert isinstance(logs["items"], list)
