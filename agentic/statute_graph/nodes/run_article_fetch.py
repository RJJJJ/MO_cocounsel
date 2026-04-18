from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.nodes._shared import run_python_script
from agentic.statute_graph.state import StatuteGraphState


def run_article_fetch(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_article_fetch"

    output_dir = Path("data/raw/statutes/civil_code/articles")
    fetch_log_path = Path("data/parsed/statutes/civil_code/articles/article_fetch_log.jsonl")

    run_python_script(
        script_relpath="crawler/statutes/fetch_civil_code_article_pages.py",
        args=[
            "--article-index-path",
            state.artifacts.get("article_index_path", "data/parsed/statutes/civil_code/index/article_index.jsonl"),
            "--output-dir",
            str(output_dir),
            "--fetch-log-path",
            str(fetch_log_path),
        ],
        stage_name=state.current_stage,
        state=state,
    )

    state.artifacts["raw_article_dir"] = str(output_dir)
    state.artifacts["fetch_log_path"] = str(fetch_log_path)
    return state
