from __future__ import annotations

from viola.agent.legacy_cs_role_templates import (
    detect_legacy_service_role,
    legacy_full_contract_block,
    legacy_role_prompt_block,
)


def test_detect_legacy_service_role_defaults_general() -> None:
    assert detect_legacy_service_role("") == "general_staff"
    assert detect_legacy_service_role("想问一下安装流程") == "general_staff"


def test_detect_legacy_service_role_tech_and_manager() -> None:
    assert detect_legacy_service_role("系统报错 E01，怎么修复") == "tech_staff"
    assert detect_legacy_service_role("我要投诉并找经理处理") == "manager"


def test_legacy_role_prompt_block_contains_role_header() -> None:
    assert "[Legacy-Role-Template: general_staff]" in legacy_role_prompt_block("general_staff")
    assert "[Legacy-Role-Template: tech_staff]" in legacy_role_prompt_block("tech_staff")
    assert "[Legacy-Role-Template: manager]" in legacy_role_prompt_block("manager")


def test_legacy_full_contract_block_contains_global_contract() -> None:
    text = legacy_full_contract_block("tech_staff")
    assert "[Legacy-LangGraph-Full-Contract]" in text
    assert "[Legacy-Role-Template: tech_staff]" in text
