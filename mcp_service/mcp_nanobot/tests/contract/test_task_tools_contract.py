from __future__ import annotations


def test_task_tool_flow_contract(task_tools) -> None:
    created = task_tools.task_create(title="Demo", bearer="token-ok")
    assert created["ok"] is True
    task_id = created["task"]["task_id"]

    fetched = task_tools.task_get(task_id=task_id, bearer="token-ok")
    assert fetched["ok"] is True
    assert fetched["task"]["task_id"] == task_id

    updated = task_tools.task_update(
        task_id=task_id,
        updates={"description": "updated"},
        bearer="token-ok",
    )
    assert updated["ok"] is True
    assert updated["task"]["description"] == "updated"
