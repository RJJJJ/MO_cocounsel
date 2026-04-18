from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.nodes._shared import run_python_script
from agentic.statute_graph.state import StatuteGraphState


def run_hierarchy(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_hierarchy"

    nodes_path = Path("data/parsed/statutes/civil_code/index/hierarchy_nodes.jsonl")
    article_index_path = Path("data/parsed/statutes/civil_code/index/article_index.jsonl")
    report_path = Path("data/parsed/statutes/civil_code/index/hierarchy_build_report.json")

    run_python_script(
        script_relpath="crawler/statutes/build_civil_code_hierarchy.py",
        args=[
            "--nodes-output-path",
            str(nodes_path),
            "--article-index-output-path",
            str(article_index_path),
            "--report-path",
            str(report_path),
        ],
        stage_name=state.current_stage,
        state=state,
    )

    state.artifacts["hierarchy_nodes_path"] = str(nodes_path)
    state.artifacts["article_index_path"] = str(article_index_path)
    state.artifacts["hierarchy_report_path"] = str(report_path)
    return state
