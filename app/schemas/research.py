"""Schemas for the Day 54 FastAPI research integration surface."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ResearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Raw legal research query")
    top_k: int = Field(5, ge=1, description="Top-k retrieval results")

    @field_validator("query")
    @classmethod
    def validate_query_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class ResearchResultItem(BaseModel):
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    case_summary: str
    holding: str
    legal_basis: list[str]
    disputed_issues: list[str]
    metadata_source: str
    pdf_url: str
    text_url_or_action: str
    card_title: str
    card_subtitle: str
    card_tags: list[str]


class ResearchDiagnostics(BaseModel):
    retrieved_cases_count: int
    case_cards_built: int
    model_generated_metadata_used_count: int
    deterministic_fallback_used_count: int
    success_flag: bool
    selected_model_metadata_path: str
    selected_model_metadata_case_count: int


class ResearchQueryResponse(BaseModel):
    schema_version: str
    query: str
    top_k: int
    result_count: int
    diagnostics: ResearchDiagnostics
    results: list[ResearchResultItem]
