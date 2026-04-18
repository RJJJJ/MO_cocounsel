from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.nodes._shared import run_python_script
from agentic.statute_graph.state import StatuteGraphState


def run_parse(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_parse"

    output_path = Path("data/parsed/statutes/civil_code/articles/articles_structured.jsonl")
    report_path = Path("data/parsed/statutes/civil_code/articles/article_parse_report.json")

    run_python_script(
        script_relpath="crawler/statutes/parse_civil_code_articles.py",
        args=[
            "--fetch-log-path",
            state.artifacts.get("fetch_log_path", "data/parsed/statutes/civil_code/articles/article_fetch_log.jsonl"),
            "--article-index-path",
            state.artifacts.get("article_index_path", "data/parsed/statutes/civil_code/index/article_index.jsonl"),
            "--output-path",
            str(output_path),
            "--report-path",
            str(report_path),
        ],
        stage_name=state.current_stage,
        state=state,
    )

    state.artifacts["articles_structured_path"] = str(output_path)
    state.artifacts["parse_report_path"] = str(report_path)
    return state
