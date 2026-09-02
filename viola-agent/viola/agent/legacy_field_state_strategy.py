"""Executable field strategy for migrated legacy step4 behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FIELD_STRATEGY_VERSION = "legacy-step4-field-v1"
FIELD_PRIORITY = ("state", "user_input", "candidate")
_CORRECTION_RE = re.compile(r"(改為|改成|更新|更正|change to|update to)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class FieldStrategyResult:
    strategy_version: str
    resolved_fields: dict[str, str] = field(default_factory=dict)
    protected_fields: tuple[str, ...] = ("product_no", "name", "phone", "location")
    overwrite_allowed: bool = False
    missing_field_prompt_limit: int = 1

    def to_prompt_block(self) -> str:
        pairs = "; ".join(f"{k}={v}" for k, v in self.resolved_fields.items() if v) or "none"
        return (
            "[Legacy-Field-Executable-Strategy]\n"
            f"strategy_version={self.strategy_version}\n"
            f"field_priority={' > '.join(FIELD_PRIORITY)}\n"
            f"overwrite_allowed={str(self.overwrite_allowed).lower()}\n"
            f"missing_field_prompt_limit={self.missing_field_prompt_limit}\n"
            f"resolved_fields={pairs}"
        )


def execute_field_strategy(
    *,
    user_text: str,
    candidate_fields: dict[str, str],
    confirmed_state_fields: dict[str, str] | None = None,
) -> FieldStrategyResult:
    state_fields = {k: (v or "").strip() for k, v in (confirmed_state_fields or {}).items() if (v or "").strip()}
    user_fields = {k: (v or "").strip() for k, v in candidate_fields.items() if (v or "").strip()}
    overwrite_allowed = bool(_CORRECTION_RE.search(user_text or ""))

    resolved: dict[str, str] = {}
    for key in ("product_no", "name", "phone", "location"):
        if state_fields.get(key) and not overwrite_allowed:
            resolved[key] = state_fields[key]
            continue
        if user_fields.get(key):
            resolved[key] = user_fields[key]
            continue
        if state_fields.get(key):
            resolved[key] = state_fields[key]

    return FieldStrategyResult(
        strategy_version=FIELD_STRATEGY_VERSION,
        resolved_fields=resolved,
        overwrite_allowed=overwrite_allowed,
    )
