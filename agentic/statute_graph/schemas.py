"""Structured schemas for statute graph diagnosis and control decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


IssueSeverity = Literal["low", "medium", "high", "critical"]
LikelyFaultStage = Literal[
    "run_classification",
    "run_hierarchy",
    "run_article_fetch",
    "run_parse",
    "run_manifest",
    "run_validators",
    "unknown",
]
RecommendedAction = Literal[
    "continue",
    "retry_pipeline",
    "retry_from_hierarchy",
    "retry_from_parse",
    "stop_and_human_review",
]
WorkflowNextStep = Literal["end_success", "retry", "stop", "human_review", "patch_candidate"]


@dataclass(slots=True)
class ValidatorIssue:
    issue_code: str
    severity: IssueSeverity
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_target_file: str = ""
    suggested_target_function: str = ""


@dataclass(slots=True)
class DiagnosisResult:
    root_cause_summary: str
    likely_fault_stage: LikelyFaultStage
    target_file: str
    target_function: str
    confidence: float
    recommended_action: RecommendedAction


@dataclass(slots=True)
class PatchProposal:
    target_file: str
    target_symbols: list[str]
    strategy: str
    safety_notes: list[str]
    patch_text_summary: str


@dataclass(slots=True)
class WorkflowDecision:
    next_step: WorkflowNextStep
    should_retry: bool
    should_stop: bool
    requires_human_review: bool
    rationale: str


def issue_to_dict(issue: ValidatorIssue) -> dict[str, Any]:
    return asdict(issue)


def diagnosis_to_dict(result: DiagnosisResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    payload = asdict(result)
    payload["confidence"] = round(float(payload["confidence"]), 4)
    return payload


def patch_to_dict(result: PatchProposal | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return asdict(result)


def decision_to_dict(result: WorkflowDecision | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return asdict(result)
