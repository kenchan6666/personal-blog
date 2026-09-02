"""Executable role strategy for migrated legacy step3 behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LegacyServiceRole = Literal["general_staff", "tech_staff", "manager"]
ROLE_STRATEGY_VERSION = "legacy-step3-role-v1"


@dataclass(frozen=True, slots=True)
class RoleStrategyResult:
    strategy_version: str
    role: LegacyServiceRole
    intro_behavior: str
    followup_behavior: str
    escalation_hint: str

    def to_prompt_block(self) -> str:
        return (
            "[Legacy-Role-Executable-Strategy]\n"
            f"strategy_version={self.strategy_version}\n"
            f"role={self.role}\n"
            f"intro_behavior={self.intro_behavior}\n"
            f"followup_behavior={self.followup_behavior}\n"
            f"escalation_hint={self.escalation_hint}"
        )


def execute_role_strategy(role: str) -> RoleStrategyResult:
    normalized = (role or "general_staff").strip().lower()
    if normalized not in {"general_staff", "tech_staff", "manager"}:
        normalized = "general_staff"

    if normalized == "tech_staff":
        return RoleStrategyResult(
            strategy_version=ROLE_STRATEGY_VERSION,
            role="tech_staff",
            intro_behavior="acknowledge_and_analyze",
            followup_behavior="single_technical_followup_when_required",
            escalation_hint="if unresolved_after_attempts_then_manager",
        )
    if normalized == "manager":
        return RoleStrategyResult(
            strategy_version=ROLE_STRATEGY_VERSION,
            role="manager",
            intro_behavior="stabilize_and_take_ownership",
            followup_behavior="summarize_resolution_path",
            escalation_hint="manager_final_escalation_channel",
        )
    return RoleStrategyResult(
        strategy_version=ROLE_STRATEGY_VERSION,
        role="general_staff",
        intro_behavior="answer_question_first",
        followup_behavior="ask_one_missing_field_if_needed",
        escalation_hint="escalate_when_customer_requests_or_risk_detected",
    )
