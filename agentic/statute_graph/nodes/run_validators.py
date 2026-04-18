from __future__ import annotations

from pathlib import Path

from agentic.statute_graph.schemas import issue_to_dict
from agentic.statute_graph.state import StatuteGraphState
from agentic.statute_graph.validators.validate_article_sequence import validate_article_sequence
from agentic.statute_graph.validators.validate_article_text_quality import validate_article_text_quality
from agentic.statute_graph.validators.validate_hierarchy_paths import validate_hierarchy_paths


def run_validators(state: StatuteGraphState) -> StatuteGraphState:
    state.current_stage = "run_validators"

    article_path = Path(state.artifacts.get("articles_structured_path", "data/parsed/statutes/civil_code/articles/articles_structured.jsonl"))

    validator_results = {
        "validate_article_sequence": [issue_to_dict(issue) for issue in validate_article_sequence(article_path)],
        "validate_hierarchy_paths": [issue_to_dict(issue) for issue in validate_hierarchy_paths(article_path)],
        "validate_article_text_quality": [issue_to_dict(issue) for issue in validate_article_text_quality(article_path)],
    }

    all_issues = [issue for result in validator_results.values() for issue in result]
    state.validator_results = validator_results
    state.failure_summary = all_issues
    state.success = len(all_issues) == 0

    state.stage_summaries.append(
        {
            "stage": state.current_stage,
            "validator_issue_count": len(all_issues),
            "validator_breakdown": {name: len(rows) for name, rows in validator_results.items()},
        }
    )
    return state
