from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import research as research_api


@dataclass
class StubDiagnostics:
    retrieved_cases_count: int = 5
    case_cards_built: int = 5
    model_generated_metadata_used_count: int = 3
    deterministic_fallback_used_count: int = 2
    success_flag: bool = True
    selected_model_metadata_path: str = "local/model-metadata.jsonl"
    selected_model_metadata_case_count: int = 3


@dataclass
class StubResultItem:
    authoritative_case_number: str = "113年度上字第1號"
    authoritative_decision_date: str = "2024-02-20"
    court: str = "最高法院"
    language: str = "zh-TW"
    case_type: str = "刑事"
    case_summary: str = "案件摘要"
    holding: str = "判決主文"
    legal_basis: list[str] = None  # type: ignore[assignment]
    disputed_issues: list[str] = None  # type: ignore[assignment]
    metadata_source: str = "model_generated"
    pdf_url: str = "https://example.com/case.pdf"
    text_url_or_action: str = "https://example.com/case.txt"
    card_title: str = "測試卡片標題"
    card_subtitle: str = "測試卡片副標"
    card_tags: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.legal_basis is None:
            self.legal_basis = ["刑法第77條"]
        if self.disputed_issues is None:
            self.disputed_issues = ["是否符合假釋要件"]
        if self.card_tags is None:
            self.card_tags = ["假釋", "刑事"]


@dataclass
class StubEnvelope:
    schema_version: str = "v1"
    query: str = "假釋"
    top_k: int = 5
    result_count: int = 1
    diagnostics: StubDiagnostics = field(default_factory=StubDiagnostics)
    results: list[StubResultItem] = field(default_factory=lambda: [StubResultItem()])


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(research_api.router)
    return TestClient(app)


def test_query_research_happy_path(monkeypatch) -> None:
    def stub_build_api_ready_response_envelope(**_: object) -> StubEnvelope:
        return StubEnvelope()

    monkeypatch.setattr(
        research_api,
        "build_api_ready_response_envelope",
        stub_build_api_ready_response_envelope,
    )
    client = _build_test_client()

    response = client.post("/api/research/query", json={"query": "假釋", "top_k": 5})

    assert response.status_code == 200
    payload = response.json()
    assert "schema_version" in payload
    assert "query" in payload
    assert "top_k" in payload
    assert "result_count" in payload
    assert "diagnostics" in payload
    assert "results" in payload

    diagnostics = payload["diagnostics"]
    assert "retrieved_cases_count" in diagnostics
    assert "case_cards_built" in diagnostics
    assert "model_generated_metadata_used_count" in diagnostics
    assert "deterministic_fallback_used_count" in diagnostics
    assert "success_flag" in diagnostics


def test_query_research_missing_query_returns_validation_error() -> None:
    client = _build_test_client()

    response = client.post("/api/research/query", json={"top_k": 5})

    assert response.status_code == 422


def test_query_research_invalid_top_k_returns_validation_error() -> None:
    client = _build_test_client()

    for invalid_top_k in (0, -1, "five"):
        response = client.post(
            "/api/research/query",
            json={"query": "假釋", "top_k": invalid_top_k},
        )
        assert response.status_code == 422


def test_query_research_empty_or_blank_query_returns_validation_error() -> None:
    client = _build_test_client()

    for invalid_query in ("", "   "):
        response = client.post(
            "/api/research/query",
            json={"query": invalid_query, "top_k": 5},
        )
        assert response.status_code == 422
