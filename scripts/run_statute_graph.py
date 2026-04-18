#!/usr/bin/env python3
"""CLI entrypoint for statute LangGraph workflow skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentic.statute_graph.nodes._shared import write_state_checkpoint
from agentic.statute_graph.state import StatuteGraphState, build_initial_state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run statute LangGraph self-healing skeleton.")
    parser.add_argument("--target-code-id", default="mo-civil-code")
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--mock-llm", action="store_true", help="Use mock diagnosis mode (default recommended for local prototype).")
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("data/parsed/statutes/civil_code/workflow/latest_run_summary.json"),
    )
    return parser.parse_args()


def print_stage_summaries(state: StatuteGraphState) -> None:
    print("\n=== Stage Summaries ===")
    for idx, summary in enumerate(state.stage_summaries, start=1):
        stage = summary.get("stage", "unknown")
        print(f"[{idx:02d}] {stage}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))


def print_final_summary(state: StatuteGraphState) -> None:
    print("\n=== Final Workflow Summary ===")
    final_summary = {
        "run_id": state.run_id,
        "target_code_id": state.target_code_id,
        "success": state.success,
        "retry_count": state.retry_count,
        "max_retries": state.max_retries,
        "stop_reason": state.stop_reason,
        "human_review_required": state.human_review_required,
        "validator_issue_count": len(state.failure_summary),
        "artifacts": state.artifacts,
        "diagnosis": state.diagnosis,
        "patch_proposal": state.patch_proposal,
        "workflow_decision": state.workflow_decision,
    }
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    try:
        from agentic.statute_graph.graph import build_statute_workflow, checkpoint_path_for_run
    except ModuleNotFoundError as exc:
        if exc.name == "langgraph":
            print("Missing dependency: langgraph. Install with `pip install langgraph`.")
            return 2
        raise

    initial_state = build_initial_state(
        target_code_id=args.target_code_id,
        max_retries=args.max_retries,
        mock_llm=bool(args.mock_llm),
        run_id=args.run_id or None,
    )

    workflow = build_statute_workflow()
    final_state: StatuteGraphState = workflow.invoke(initial_state)

    print_stage_summaries(final_state)
    print_final_summary(final_state)

    checkpoint_path = checkpoint_path_for_run(final_state.run_id)
    write_state_checkpoint(final_state, checkpoint_path)

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(final_state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved run summary: {args.summary_output}")
    print(f"Saved checkpoint: {checkpoint_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
