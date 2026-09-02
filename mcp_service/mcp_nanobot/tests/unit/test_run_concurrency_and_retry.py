from __future__ import annotations


def test_run_retry_rules(task_tools, run_tools, store) -> None:
    task_id = task_tools.task_create(title="Retry flow", bearer="token-ok")["task"]["task_id"]
    run = run_tools.run_trigger(task_id=task_id, bearer="token-ok")
    run_id = run["run"]["run_id"]
    store.runs[run_id].status = "failed"

    retried = run_tools.run_retry(run_id=run_id, bearer="token-ok")
    assert retried["ok"] is True
    assert retried["run"]["attempt"] == 2


def test_run_cancel_conflict(task_tools, run_tools, store) -> None:
    task_id = task_tools.task_create(title="Cancel flow", bearer="token-ok")["task"]["task_id"]
    run = run_tools.run_trigger(task_id=task_id, bearer="token-ok")
    run_id = run["run"]["run_id"]
    store.runs[run_id].status = "succeeded"

    canceled = run_tools.run_cancel(run_id=run_id, bearer="token-ok")
    assert canceled["ok"] is False
    assert canceled["error"]["code"] == "STATE_CONFLICT"
