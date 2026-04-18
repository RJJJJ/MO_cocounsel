from __future__ import annotations

from agentic.statute_graph.schemas import WorkflowDecision, decision_to_dict
from agentic.statute_graph.state import StatuteGraphState


def _has_critical_issues(state: StatuteGraphState) -> bool:
    for issue in state.failure_summary:
        if str(issue.get("severity", "")).lower() == "critical":
            return True
    return False


def decide_next_step(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "decide_next_step"

    if state.success:
        decision = WorkflowDecision(
            next_step="end_success",
            should_retry=False,
            should_stop=True,
            requires_human_review=False,
            rationale="No validator issues detected; workflow succeeded.",
        )
        state.stop_reason = "validators_passed"
        state.workflow_decision = decision_to_dict(decision)
        state.stage_summaries.append({"stage": state.current_stage, "decision": state.workflow_decision})
        return state

    has_critical = _has_critical_issues(state)
    if has_critical:
        state.human_review_required = True

    if state.retry_count < state.max_retries and not has_critical:
        decision = WorkflowDecision(
            next_step="retry",
            should_retry=True,
            should_stop=False,
            requires_human_review=False,
            rationale="Non-critical validator failures and retry budget available.",
        )
        state.retry_count += 1
        state.stop_reason = ""
    elif has_critical:
        decision = WorkflowDecision(
            next_step="human_review",
            should_retry=False,
            should_stop=True,
            requires_human_review=True,
            rationale="Critical deterministic validation failures require manual investigation.",
        )
        state.stop_reason = "critical_validation_failure"
    else:
        decision = WorkflowDecision(
            next_step="stop",
            should_retry=False,
            should_stop=True,
            requires_human_review=True,
            rationale="Retry budget exhausted; stopping for diagnosis review.",
        )
        state.human_review_required = True
        state.stop_reason = "max_retries_exhausted"

    state.workflow_decision = decision_to_dict(decision)
    state.stage_summaries.append({"stage": state.current_stage, "decision": state.workflow_decision})
    return state
