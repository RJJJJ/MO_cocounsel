from __future__ import annotations

from collections import Counter

from agentic.statute_graph.schemas import (
    DiagnosisResult,
    PatchProposal,
    diagnosis_to_dict,
    patch_to_dict,
)
from agentic.statute_graph.state import StatuteGraphState


def _mock_diagnosis(state: StatuteGraphState) -> tuple[DiagnosisResult, PatchProposal]:
    issue_codes = [issue.get("issue_code", "") for issue in state.failure_summary]
    code_counter = Counter(issue_codes)
    top_issue = code_counter.most_common(1)[0][0] if code_counter else "unknown"

    likely_stage = "run_hierarchy" if "nested_article_hierarchy_path" in code_counter else "run_parse"
    if "article_number_gap_detected" in code_counter or "article_number_duplicate" in code_counter:
        likely_stage = "run_classification"

    diagnosis = DiagnosisResult(
        root_cause_summary=f"Top validator signal: {top_issue}. Deterministic pipeline likely degraded before parsing output stabilized.",
        likely_fault_stage=likely_stage,
        target_file="crawler/statutes/build_civil_code_hierarchy.py",
        target_function="build_path",
        confidence=0.62,
        recommended_action="retry_pipeline" if state.retry_count < state.max_retries else "stop_and_human_review",
    )

    patch = PatchProposal(
        target_file="crawler/statutes/build_civil_code_hierarchy.py",
        target_symbols=["build_path", "extract_article_number"],
        strategy="Constrain hierarchy assembly so article nodes cannot become parents of article nodes.",
        safety_notes=[
            "Keep deterministic hierarchy rule set as source of truth.",
            "Do not auto-apply patch without human confirmation in v1 skeleton.",
        ],
        patch_text_summary="Add guardrails in hierarchy builder to strip article labels from parent stack before path assembly.",
    )
    return diagnosis, patch


def diagnose_failures(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "diagnose_failures"

    if state.success:
        state.diagnosis = None
        state.patch_proposal = None
        state.stage_summaries.append({"stage": state.current_stage, "message": "No failures detected; diagnosis skipped."})
        return state

    diagnosis, patch = _mock_diagnosis(state)
    state.diagnosis = diagnosis_to_dict(diagnosis)
    state.patch_proposal = patch_to_dict(patch)
    state.stage_summaries.append(
        {
            "stage": state.current_stage,
            "mode": "mock_llm" if state.mock_llm else "llm_stub",
            "diagnosis": state.diagnosis,
            "patch_proposal": state.patch_proposal,
        }
    )
    return state
