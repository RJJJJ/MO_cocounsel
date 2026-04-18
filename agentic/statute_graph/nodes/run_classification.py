from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.nodes._shared import run_python_script
from agentic.statute_graph.state import StatuteGraphState


def run_classification(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_classification"
    output_path = Path("data/parsed/statutes/civil_code/index/index_lines_classified.jsonl")
    report_path = Path("data/parsed/statutes/civil_code/index/index_lines_classification_report.json")

    args = ["--output-path", str(output_path), "--report-path", str(report_path)]
    if state.mock_llm:
        args.append("--no-ollama")

    run_python_script(
        script_relpath="crawler/statutes/classify_civil_code_index_lines_with_ollama.py",
        args=args,
        stage_name=state.current_stage,
        state=state,
    )

    state.artifacts["classification_output_path"] = str(output_path)
    state.artifacts["classification_report_path"] = str(report_path)
    return state
