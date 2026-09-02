"""Executable legacy workflow state machine migrated from LangGraph.

This module ports the critical behavior of step1/step2/step4/step5 into
deterministic runtime logic for viola-agent webhook flow.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Literal

LegacyIntent = Literal["faq", "tech_support", "manager_support"]
LegacyRole = Literal["general_staff", "tech_staff", "manager"]
LegacySentiment = Literal["positive", "neutral", "negative", "terrible"]
LegacyPriority = Literal["low", "medium", "high"]

WORKFLOW_STRATEGY_VERSION = "legacy-step1-2-4-5-workflow-v1"
_NOW = time.time

_TECH_KEYWORDS = (
    "报错",
    "故障",
    "error",
    "failed",
    "failure",
    "维修",
    "維修",
    "技術",
    "technical",
    "engineer",
)
_MANAGER_KEYWORDS = (
    "投诉",
    "投訴",
    "经理",
    "經理",
    "主管",
    "赔偿",
    "賠償",
    "lawyer",
)
_NEGATIVE_KEYWORDS = (
    "唔得",
    "不行",
    "没用",
    "沒有用",
    "失败",
    "失敗",
    "慢",
    "等很久",
    "等好耐",
)
_TERRIBLE_KEYWORDS = (
    "非常不满",
    "極度不滿",
    "马上给经理",
    "立刻給經理",
    "投訴到底",
)
_URGENT_KEYWORDS = ("紧急", "急", "asap", "urgent", "立即", "马上")
_CORRECTION_RE = re.compile(r"(改為|改成|更新|更正|change to|update to)", re.IGNORECASE)
_TECH_ESCALATION_KEYWORDS = (
    "技術支援",
    "技术支援",
    "技術團隊",
    "技术团队",
    "工程師",
    "工程师",
    "轉技術",
    "转技术",
    "轉交技術",
    "转交技术",
    "specialist",
    "escalate",
)
_MANAGER_ESCALATION_KEYWORDS = (
    "經理",
    "经理",
    "主管",
    "上級",
    "上级",
    "投訴",
    "投诉",
    "賠償",
    "赔偿",
)


@dataclass(slots=True)
class LegacyConversationState:
    strategy_version: str = WORKFLOW_STRATEGY_VERSION
    session_key: str = ""
    current_role: LegacyRole = "general_staff"
    intent: LegacyIntent = "faq"
    customer_sentiment: LegacySentiment = "neutral"
    priority: LegacyPriority = "low"
    role_response_count: dict[str, int] = field(default_factory=dict)
    role_history: list[str] = field(default_factory=list)
    max_role_responses: int = 5
    product_no: str = ""
    name: str = ""
    phone: str = ""
    location: str = ""
    issue_description: str = ""
    user_goal: str = ""
    recent_user_messages: list[str] = field(default_factory=list)
    recent_ai_messages: list[str] = field(default_factory=list)
    last_updated_ts: float = field(default_factory=_NOW)

    def to_confirmed_fields(self) -> dict[str, str]:
        return {
            "product_no": (self.product_no or "").strip(),
            "name": (self.name or "").strip(),
            "phone": (self.phone or "").strip(),
            "location": (self.location or "").strip(),
        }

    def to_prompt_block(self) -> str:
        confirmed = self.to_confirmed_fields()
        confirmed_pairs = "; ".join(f"{k}={v}" for k, v in confirmed.items() if v) or "none"
        role_counts = ", ".join(f"{k}:{v}" for k, v in sorted(self.role_response_count.items())) or "none"
        return (
            "[Legacy-Workflow-Executable-State]\n"
            f"strategy_version={self.strategy_version}\n"
            f"current_role={self.current_role}\n"
            f"intent={self.intent}\n"
            f"customer_sentiment={self.customer_sentiment}\n"
            f"priority={self.priority}\n"
            f"max_role_responses={self.max_role_responses}\n"
            f"role_response_count={role_counts}\n"
            f"confirmed_fields={confirmed_pairs}\n"
            f"user_goal={self.user_goal or '(none)'}\n"
            f"issue_description={self.issue_description or '(none)'}"
        )


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _derive_intent(user_text: str) -> LegacyIntent:
    raw = _normalize_text(user_text)
    if any(k.lower() in raw for k in _MANAGER_KEYWORDS):
        return "manager_support"
    if any(k.lower() in raw for k in _TECH_KEYWORDS):
        return "tech_support"
    return "faq"


def _derive_sentiment(
    *,
    user_text: str,
    prior: LegacySentiment,
    response_count_total: int,
) -> LegacySentiment:
    raw = _normalize_text(user_text)
    if any(k.lower() in raw for k in _TERRIBLE_KEYWORDS):
        return "terrible"
    if any(k.lower() in raw for k in _NEGATIVE_KEYWORDS):
        return "negative"
    if response_count_total >= 12:
        return "terrible"
    if response_count_total >= 8 and prior == "neutral":
        return "negative"
    return prior if prior in ("negative", "terrible") else "neutral"


def _derive_priority(user_text: str, sentiment: LegacySentiment) -> LegacyPriority:
    raw = _normalize_text(user_text)
    if sentiment == "terrible":
        return "high"
    if sentiment == "negative":
        return "medium"
    if any(k.lower() in raw for k in _URGENT_KEYWORDS):
        return "medium"
    return "low"


def _detect_user_goal(user_text: str) -> str:
    text = (user_text or "").strip()
    if not text:
        return ""
    return text[:200]


def _update_fields_with_priority(
    state: LegacyConversationState,
    *,
    user_text: str,
    candidate_fields: dict[str, str],
) -> None:
    overwrite_allowed = bool(_CORRECTION_RE.search(user_text or ""))
    for key in ("product_no", "name", "phone", "location"):
        existing = (getattr(state, key) or "").strip()
        incoming = (candidate_fields.get(key) or "").strip()
        if not incoming:
            continue
        if existing and not overwrite_allowed:
            continue
        setattr(state, key, incoming)

    # Keep issue_description as a durable quote context carrier
    # (e.g. extracted size semantics like "尺寸=3000x2000").
    issue_incoming = (candidate_fields.get("issue_description") or "").strip()
    if issue_incoming and (overwrite_allowed or not (state.issue_description or "").strip()):
        state.issue_description = issue_incoming


def _mandatory_fields_ready(state: LegacyConversationState) -> bool:
    return all(
        (getattr(state, f) or "").strip()
        for f in ("product_no", "name", "phone", "location")
    )


def _apply_role_escalation(state: LegacyConversationState) -> None:
    role = state.current_role
    role_count = int(state.role_response_count.get(role, 0))
    total_count = sum(int(v) for v in state.role_response_count.values())
    latest_user = _normalize_text(state.recent_user_messages[-1] if state.recent_user_messages else "")
    has_tech_escalation_signal = any(k.lower() in latest_user for k in _TECH_ESCALATION_KEYWORDS)
    has_manager_escalation_signal = any(k.lower() in latest_user for k in _MANAGER_ESCALATION_KEYWORDS)
    mandatory_ready = _mandatory_fields_ready(state)
    sentiment_bad = state.customer_sentiment in ("negative", "terrible")

    if role == "general_staff":
        # Closer to legacy multi-condition behavior:
        # 1) standard threshold + tech intent,
        # 2) explicit tech escalation request,
        # 3) prolonged loop with required fields collected,
        # 4) sentiment deterioration after enough rounds.
        if (
            mandatory_ready
            and (
                (role_count >= state.max_role_responses and state.intent == "tech_support")
                or (role_count >= state.max_role_responses and has_tech_escalation_signal)
                or (role_count >= state.max_role_responses + 2)
                or (role_count >= state.max_role_responses and sentiment_bad)
            )
        ):
            state.current_role = "tech_staff"
            state.role_history.append("tech_staff")
        return

    if role == "tech_staff":
        # Manager escalation becomes stronger with multiple deterministic paths:
        # - explicit manager complaint signal after some tech attempts
        # - terrible sentiment
        # - prolonged unresolved technical rounds
        if (
            (role_count >= 2 and (state.intent == "manager_support" or has_manager_escalation_signal))
            or (role_count >= 2 and state.customer_sentiment == "terrible")
            or (role_count >= state.max_role_responses and sentiment_bad)
            or (role_count >= state.max_role_responses + 2)
            or (total_count >= 12 and sentiment_bad)
        ):
            state.current_role = "manager"
            state.role_history.append("manager")
        return


def advance_on_user_message(
    state: LegacyConversationState | None,
    *,
    session_key: str,
    user_text: str,
    candidate_fields: dict[str, str],
) -> LegacyConversationState:
    current = state or LegacyConversationState(session_key=session_key)
    current.session_key = session_key
    text = (user_text or "").strip()
    if text:
        current.recent_user_messages = [*current.recent_user_messages[-5:], text]

    current.intent = _derive_intent(text)
    total_responses = sum(int(v) for v in current.role_response_count.values())
    current.customer_sentiment = _derive_sentiment(
        user_text=text,
        prior=current.customer_sentiment,
        response_count_total=total_responses,
    )
    current.priority = _derive_priority(text, current.customer_sentiment)
    current.user_goal = _detect_user_goal(text) or current.user_goal
    _update_fields_with_priority(current, user_text=text, candidate_fields=candidate_fields)
    _apply_role_escalation(current)
    current.last_updated_ts = _NOW()
    return current


def advance_on_assistant_message(
    state: LegacyConversationState,
    *,
    assistant_text: str,
) -> LegacyConversationState:
    text = (assistant_text or "").strip()
    if text:
        state.recent_ai_messages = [*state.recent_ai_messages[-5:], text]
        state.issue_description = text[:500]
    role = state.current_role
    state.role_response_count[role] = int(state.role_response_count.get(role, 0)) + 1
    if not state.role_history or state.role_history[-1] != role:
        state.role_history.append(role)
    _apply_role_escalation(state)
    state.last_updated_ts = _NOW()
    return state
