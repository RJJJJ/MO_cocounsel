from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.nodes._shared import run_python_script
from agentic.statute_graph.state import StatuteGraphState


def run_manifest(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_manifest"

    manifest_path = Path("data/parsed/statutes/civil_code/manifest/civil_code_manifest_v1.json")

    run_python_script(
        script_relpath="crawler/statutes/build_civil_code_manifest.py",
        args=[
            "--hierarchy-path",
            state.artifacts.get("hierarchy_nodes_path", "data/parsed/statutes/civil_code/index/hierarchy_nodes.jsonl"),
            "--article-jsonl-path",
            state.artifacts.get("articles_structured_path", "data/parsed/statutes/civil_code/articles/articles_structured.jsonl"),
            "--manifest-path",
            str(manifest_path),
            "--code-id",
            state.target_code_id,
        ],
        stage_name=state.current_stage,
        state=state,
    )

    state.artifacts["manifest_path"] = str(manifest_path)
    return state
