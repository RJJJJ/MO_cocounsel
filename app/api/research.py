"""Day 54: minimal FastAPI integration surface for research response envelope."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from app.schemas.research import ResearchQueryRequest, ResearchQueryResponse
from crawler.pipeline.build_api_ready_response_envelope import (
    build_api_ready_response_envelope,
)
from crawler.pipeline.integrate_metadata_into_research_pipeline import (
    DEFAULT_BASELINE_METADATA_PATH,
    DEFAULT_MODEL_METADATA_PATH,
)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/query", response_model=ResearchQueryResponse)
def query_research(payload: ResearchQueryRequest) -> ResearchQueryResponse:
    """Expose existing API-ready response envelope through FastAPI transport."""
    envelope = build_api_ready_response_envelope(
        query=payload.query,
        top_k=payload.top_k,
        model_metadata_path=DEFAULT_MODEL_METADATA_PATH,
        baseline_metadata_path=DEFAULT_BASELINE_METADATA_PATH,
        model_metadata_explicit_override=False,
    )

    return ResearchQueryResponse.model_validate(asdict(envelope))
