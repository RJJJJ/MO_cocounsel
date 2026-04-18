"""Shared node helpers for statute graph workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from agentic.statute_graph.state import StatuteGraphState

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_python_script(
    *,
    script_relpath: str,
    args: list[str],
    stage_name: str,
    state: StatuteGraphState,
) -> dict[str, Any]:
    script_path = REPO_ROOT / script_relpath
    cmd = [sys.executable, str(script_path), *args]
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    summary: dict[str, Any] = {
        "stage": stage_name,
        "script": script_relpath,
        "command": " ".join(cmd),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }

    if completed.returncode != 0:
        state.stage_errors.append(summary)
        raise RuntimeError(f"{stage_name} failed with return code {completed.returncode}")

    state.stage_summaries.append(summary)
    return summary


def write_state_checkpoint(state: StatuteGraphState, checkpoint_path: Path) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
