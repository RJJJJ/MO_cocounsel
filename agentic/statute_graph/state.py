"""State definition for the statute ingestion LangGraph workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class StatuteGraphState:
    run_id: str
    target_code_id: str
    current_stage: str
    artifacts: dict[str, str] = field(default_factory=dict)
    validator_results: dict[str, Any] = field(default_factory=dict)
    browser_checks: list[dict[str, Any]] = field(default_factory=list)
    failure_summary: list[dict[str, Any]] = field(default_factory=list)
    diagnosis: dict[str, Any] | None = None
    patch_proposal: dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 1
    stop_reason: str = ""
    success: bool = False
    human_review_required: bool = False
    workflow_decision: dict[str, Any] | None = None
    stage_summaries: list[dict[str, Any]] = field(default_factory=list)
    stage_errors: list[dict[str, Any]] = field(default_factory=list)
    mock_llm: bool = True
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_initial_state(
    *,
    target_code_id: str,
    max_retries: int,
    mock_llm: bool,
    run_id: str | None = None,
) -> StatuteGraphState:
    return StatuteGraphState(
        run_id=run_id or str(uuid4()),
        target_code_id=target_code_id,
        current_stage="init",
        max_retries=max(0, max_retries),
        mock_llm=mock_llm,
    )
