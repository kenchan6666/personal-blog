from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_webhook_main_module():
    module_path = Path(__file__).resolve().parents[2] / "main.py"
    project_root = module_path.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    for name in list(sys.modules.keys()):
        if name == "viola" or name.startswith("viola."):
            sys.modules.pop(name, None)
    module_name = "viola_webhook_main_test"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_default_viola_model_prefers_viola_model_env(monkeypatch) -> None:
    mod = _load_webhook_main_module()
    monkeypatch.setenv("VIOLA_MODEL", "openai/gpt-4.1")
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__MODEL", "deepseek/deepseek-chat")
    assert mod._default_viola_model() == "openai/gpt-4.1"


def test_default_viola_model_falls_back_to_agent_default(monkeypatch) -> None:
    mod = _load_webhook_main_module()
    monkeypatch.delenv("VIOLA_MODEL", raising=False)
    monkeypatch.setenv("VIOLA_AGENTS__DEFAULTS__MODEL", "openai/gpt-4o-mini")
    assert mod._default_viola_model() == "openai/gpt-4o-mini"


def test_build_inbound_plaintext_injects_legacy_field_contract() -> None:
    mod = _load_webhook_main_module()
    text = mod.build_inbound_plaintext(
        body="Please create project, model DL001, install at quarry bay",
        profile_name="Test User",
        sender_mobile_digits="85212345678",
        button_payload=None,
        media_urls=[],
        media_content_types=[],
        lat=None,
        lon=None,
        legacy_role="tech_staff",
    )
    assert "[Legacy-Field-Contract]" in text
    assert "[Legacy-Role-Executable-Strategy]" in text
    assert "[Legacy-Field-Executable-Strategy]" in text
    assert "product_no, name, phone, location, issue_description" in text
    assert "产品关键词" in text
    assert "[Legacy-Field-Candidates]" in text
    assert "[Legacy-Service-Role: tech_staff]" in text
    assert "[Legacy-LangGraph-Full-Contract]" in text
    assert "[Legacy-Role-Template: tech_staff]" in text
    assert "product_no=DL001" in text
    assert "location=" in text
    assert "quarry bay" in text


def test_customer_service_only_flag_defaults_on(monkeypatch) -> None:
    mod = _load_webhook_main_module()
    monkeypatch.delenv("VIOLA_CUSTOMER_SERVICE_ONLY", raising=False)
    assert mod._customer_service_only_enabled() is True


def test_customer_service_only_flag_can_disable(monkeypatch) -> None:
    mod = _load_webhook_main_module()
    monkeypatch.setenv("VIOLA_CUSTOMER_SERVICE_ONLY", "false")
    assert mod._customer_service_only_enabled() is False


def test_mutation_detection_uses_generic_write_intent() -> None:
    mod = _load_webhook_main_module()
    assert mod._looks_like_mutation_request("请帮我创建项目") is True
    assert mod._looks_like_mutation_request("please update invoice") is True
    assert mod._looks_like_mutation_request("我想咨询安装地址和营业时间") is False


def test_select_legacy_service_role_routes_manager_and_tech() -> None:
    mod = _load_webhook_main_module()
    assert mod._select_legacy_service_role("我要投诉你们服务，要找经理") == "manager"
    assert mod._select_legacy_service_role("设备报错 E05，如何排查") == "tech_staff"
    assert mod._select_legacy_service_role("请问门市营业时间") == "general_staff"


def test_extract_legacy_field_candidates_captures_dimension_semantics() -> None:
    mod = _load_webhook_main_module()
    c1 = mod._extract_legacy_field_candidates("窗簾尺寸 3000x2000，想報價")
    c2 = mod._extract_legacy_field_candidates("size: 3000 * 2000")
    c3 = mod._extract_legacy_field_candidates("尺寸 3m×2m，幫我估價")

    assert c1["issue_description"] == "尺寸=3000x2000"
    assert c2["issue_description"] == "尺寸=3000x2000"
    assert c3["issue_description"] == "尺寸=3mx2m"
