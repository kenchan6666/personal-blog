from __future__ import annotations


def test_task_transition_enforces_state_machine(task_tools) -> None:
    created = task_tools.task_create(title="Flow", bearer="token-ok")
    task_id = created["task"]["task_id"]

    bad = task_tools.task_transition(task_id=task_id, to_status="completed", bearer="token-ok")
    assert bad["ok"] is False
    assert bad["error"]["code"] == "STATE_CONFLICT"

    ok = task_tools.task_transition(task_id=task_id, to_status="in_progress", bearer="token-ok")
    assert ok["ok"] is True
    assert ok["task"]["status"] == "in_progress"
