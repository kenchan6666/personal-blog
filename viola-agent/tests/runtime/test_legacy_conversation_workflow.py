from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for name in list(sys.modules.keys()):
    if name == "viola" or name.startswith("viola."):
        sys.modules.pop(name, None)

workflow = importlib.import_module("viola.agent.legacy_conversation_workflow")
LegacyConversationState = workflow.LegacyConversationState
advance_on_assistant_message = workflow.advance_on_assistant_message
advance_on_user_message = workflow.advance_on_user_message


def test_workflow_escalates_general_to_tech_after_threshold_and_fields() -> None:
    state = LegacyConversationState(
        session_key="api:85212345678",
        current_role="general_staff",
        product_no="DL001",
        name="李太",
        phone="85212345678",
        location="屯門黃金海灣",
        role_response_count={"general_staff": 5},
    )
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="设备报错 E05，想找技术支援",
        candidate_fields={},
    )
    assert state.current_role == "tech_staff"


def test_workflow_protects_confirmed_fields_without_correction() -> None:
    state = LegacyConversationState(
        session_key="api:85212345678",
        phone="61234567",
    )
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="電話 91234567",
        candidate_fields={"phone": "91234567"},
    )
    assert state.phone == "61234567"


def test_workflow_allows_field_overwrite_with_explicit_correction() -> None:
    state = LegacyConversationState(
        session_key="api:85212345678",
        phone="61234567",
    )
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="請更正電話，改為 91234567",
        candidate_fields={"phone": "91234567"},
    )
    assert state.phone == "91234567"


def test_workflow_records_assistant_response_count() -> None:
    state = LegacyConversationState(session_key="api:85212345678", current_role="general_staff")
    state = advance_on_assistant_message(state, assistant_text="您好，請問有什麼可以幫你？")
    assert state.role_response_count["general_staff"] == 1
    assert state.issue_description


def test_workflow_accepts_issue_description_candidate_for_size_context() -> None:
    state = LegacyConversationState(session_key="api:85212345678")
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="窗簾尺寸 3000x2000，請報價",
        candidate_fields={"issue_description": "尺寸=3000x2000"},
    )
    assert state.issue_description == "尺寸=3000x2000"


def test_workflow_escalates_general_to_tech_on_explicit_tech_request() -> None:
    state = LegacyConversationState(
        session_key="api:85212345678",
        current_role="general_staff",
        product_no="DL001",
        name="陈生",
        phone="91234567",
        location="九龙湾",
        role_response_count={"general_staff": 5},
    )
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="可否轉交技術團隊跟進？",
        candidate_fields={},
    )
    assert state.current_role == "tech_staff"


def test_workflow_escalates_tech_to_manager_on_manager_signal_after_attempts() -> None:
    state = LegacyConversationState(
        session_key="api:85212345678",
        current_role="tech_staff",
        intent="tech_support",
        customer_sentiment="negative",
        role_response_count={"tech_staff": 2},
    )
    state = advance_on_user_message(
        state,
        session_key=state.session_key,
        user_text="我要投訴，請轉經理處理",
        candidate_fields={},
    )
    assert state.current_role == "manager"
