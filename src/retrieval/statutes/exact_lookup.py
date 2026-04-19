"""Local exact statute lookup service backed by authoritative corpus files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .loaders import load_articles, load_statute_exact_lookup, load_statute_summary

REQUIRED_OUTPUT_FIELDS = (
    "statute_id",
    "code_label",
    "article_no",
    "article_title",
    "hierarchy_path",
    "full_text",
    "source_url",
    "flags",
)


@dataclass(slots=True)
class StatuteExactLookupService:
    exact_lookup: dict[str, Any]
    summary: Any
    articles: list[dict[str, Any]]

    @classmethod
    def from_default_paths(cls) -> "StatuteExactLookupService":
        return cls(
            exact_lookup=load_statute_exact_lookup(),
            summary=load_statute_summary(),
            articles=load_articles(),
        )

    def lookup_by_statute_id(self, statute_id: str) -> dict[str, Any] | None:
        sid = statute_id.strip()
        if not sid:
            return None

        by_id = self._find_index("by_statute_id", "statute_id", "statute_id_index", "id_to_article")
        if isinstance(by_id, dict) and sid in by_id:
            return self._normalize_result(by_id[sid])

        for key in ("records", "entries", "articles"):
            records = self.exact_lookup.get(key)
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict) and str(record.get("statute_id", "")).strip() == sid:
                        return self._normalize_result(record)

        for record in self.articles:
            if str(record.get("statute_id", "")).strip() == sid:
                return self._normalize_result(record)
        return None

    def lookup_by_code_slug_and_article_no(self, code_slug: str, article_no: str) -> dict[str, Any] | None:
        slug = code_slug.strip().lower()
        article = article_no.strip()
        if not slug or not article:
            return None

        combo = self._find_index(
            "by_code_slug_and_article_no",
            "code_slug_article_no",
            "slug_article_index",
            "code_slug_to_article_no",
        )
        if isinstance(combo, dict):
            candidate = self._lookup_combined_key(combo, slug, article)
            if candidate is not None:
                return self._normalize_result(candidate)

        by_slug = self._find_index("by_code_slug", "code_slug_index")
        if isinstance(by_slug, dict):
            scoped = by_slug.get(slug)
            if isinstance(scoped, dict):
                candidate = self._lookup_key_aliases(scoped, article)
                if candidate is not None:
                    return self._normalize_result(candidate)

        return self._fallback_scan(code_key="code_slug", code_value=slug, article_no=article, lower_code=True)

    def lookup_by_code_label_and_article_no(self, code_label: str, article_no: str) -> dict[str, Any] | None:
        label = code_label.strip()
        article = article_no.strip()
        if not label or not article:
            return None

        combo = self._find_index(
            "by_code_label_and_article_no",
            "code_label_article_no",
            "label_article_index",
            "code_label_to_article_no",
        )
        if isinstance(combo, dict):
            candidate = self._lookup_combined_key(combo, label, article)
            if candidate is not None:
                return self._normalize_result(candidate)

        by_label = self._find_index("by_code_label", "code_label_index")
        if isinstance(by_label, dict):
            scoped = by_label.get(label)
            if isinstance(scoped, dict):
                candidate = self._lookup_key_aliases(scoped, article)
                if candidate is not None:
                    return self._normalize_result(candidate)

        return self._fallback_scan(code_key="code_label", code_value=label, article_no=article, lower_code=False)

    def _find_index(self, *keys: str) -> Any:
        for key in keys:
            if key in self.exact_lookup:
                return self.exact_lookup[key]
        return None

    def _lookup_combined_key(self, mapping: dict[str, Any], code: str, article_no: str) -> Any:
        for key in (
            f"{code}#{article_no}",
            f"{code}:{article_no}",
            f"{code}|{article_no}",
            f"{code}/{article_no}",
            f"{code}::{article_no}",
            f"{code}_{article_no}",
        ):
            if key in mapping:
                return mapping[key]
        return None

    def _lookup_key_aliases(self, mapping: dict[str, Any], article_no: str) -> Any:
        for key in (article_no, article_no.lower(), article_no.upper()):
            if key in mapping:
                return mapping[key]
        return None

    def _fallback_scan(
        self,
        code_key: str,
        code_value: str,
        article_no: str,
        lower_code: bool,
    ) -> dict[str, Any] | None:
        def code_match(record: dict[str, Any]) -> bool:
            raw = str(record.get(code_key, "")).strip()
            value = raw.lower() if lower_code else raw
            return value == code_value

        for key in ("records", "entries", "articles"):
            records = self.exact_lookup.get(key)
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    if code_match(record) and str(record.get("article_no", "")).strip() == article_no:
                        return self._normalize_result(record)

        for record in self.articles:
            if code_match(record) and str(record.get("article_no", "")).strip() == article_no:
                return self._normalize_result(record)

        return None

    def _normalize_result(self, raw: Any) -> dict[str, Any]:
        record = raw[0] if isinstance(raw, list) and raw else raw
        if not isinstance(record, dict):
            return {field: None for field in REQUIRED_OUTPUT_FIELDS}

        normalized: dict[str, Any] = {}
        for field in REQUIRED_OUTPUT_FIELDS:
            value = record.get(field)
            if field == "flags" and value is None:
                value = {}
            normalized[field] = value
        return normalized
