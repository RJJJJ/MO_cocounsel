"""LangGraph statute ingestion orchestration skeleton."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agentic.statute_graph.nodes.decide_next_step import decide_next_step
from agentic.statute_graph.nodes.diagnose_failures import diagnose_failures
from agentic.statute_graph.nodes.run_article_fetch import run_article_fetch
from agentic.statute_graph.nodes.run_classification import run_classification
from agentic.statute_graph.nodes.run_hierarchy import run_hierarchy
from agentic.statute_graph.nodes.run_manifest import run_manifest
from agentic.statute_graph.nodes.run_parse import run_parse
from agentic.statute_graph.nodes.run_validators import run_validators
from agentic.statute_graph.state import StatuteGraphState


def _route_after_decision(state: StatuteGraphState) -> Literal["retry", "end", "human_review", "patch_candidate"]:
    decision = state.workflow_decision or {}
    next_step = str(decision.get("next_step", "stop"))
    if next_step == "retry":
        return "retry"
    if next_step == "human_review":
        return "human_review"
    if next_step == "patch_candidate":
        return "patch_candidate"
    return "end"


def _patch_candidate_placeholder(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "patch_candidate_placeholder"
    state.human_review_required = True
    state.stop_reason = "patch_node_not_implemented"
    state.stage_summaries.append(
        {
            "stage": state.current_stage,
            "message": "Future patch-apply node hook. No auto patching in this skeleton.",
        }
    )
    return state


def build_statute_workflow(*, checkpointer: InMemorySaver | None = None):
    graph = StateGraph(StatuteGraphState)

    graph.add_node("run_classification", run_classification)
    graph.add_node("run_hierarchy", run_hierarchy)
    graph.add_node("run_article_fetch", run_article_fetch)
    graph.add_node("run_parse", run_parse)
    graph.add_node("run_manifest", run_manifest)
    graph.add_node("run_validators", run_validators)
    graph.add_node("diagnose_failures", diagnose_failures)
    graph.add_node("decide_next_step", decide_next_step)
    graph.add_node("patch_candidate", _patch_candidate_placeholder)

    graph.add_edge(START, "run_classification")
    graph.add_edge("run_classification", "run_hierarchy")
    graph.add_edge("run_hierarchy", "run_article_fetch")
    graph.add_edge("run_article_fetch", "run_parse")
    graph.add_edge("run_parse", "run_manifest")
    graph.add_edge("run_manifest", "run_validators")
    graph.add_edge("run_validators", "diagnose_failures")
    graph.add_edge("diagnose_failures", "decide_next_step")

    graph.add_conditional_edges(
        "decide_next_step",
        _route_after_decision,
        {
            "retry": "run_classification",
            "human_review": END,
            "patch_candidate": "patch_candidate",
            "end": END,
        },
    )
    graph.add_edge("patch_candidate", END)

    compiled = graph.compile(checkpointer=checkpointer or InMemorySaver())
    return compiled


def checkpoint_path_for_run(run_id: str) -> Path:
    return Path("data/parsed/statutes/civil_code/workflow") / run_id / "state_checkpoint.json"
