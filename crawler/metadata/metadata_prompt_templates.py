#!/usr/bin/env python3
"""Prompt template helpers for local metadata generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptContext:
    prompt_version: str
    authoritative_case_number: str
    language: str
    case_type: str
    clipped_text: str


def render_metadata_prompt(context: PromptContext) -> str:
    prompt_version = context.prompt_version.strip()

    if prompt_version == "day47_prompt_a":
        return _render_day47_prompt_a(context)

    if prompt_version in {"day45_prompt_b_tch_norm", "day44_prompt_b", "day44_prompt_a"}:
        return _render_legacy_prompt(context)

    return _render_legacy_prompt(context)


def _render_day47_prompt_a(context: PromptContext) -> str:
    return (
        "你是澳門法院判決的結構化資訊抽取助手。"
        "請只輸出一個合法 JSON 物件，不可輸出 Markdown、註解、前後綴文字。\\n"
        f"prompt_version: {context.prompt_version}\\n"
        "輸出必須完全符合以下 schema 與型別：\\n"
        "{"
        '"case_summary": "string", '
        '"holding": "string", '
        '"legal_basis": ["string"], '
        '"disputed_issues": ["string"]'
        "}\\n"
        "欄位規則（務必遵守）：\\n"
        "1) case_summary：以繁體中文撰寫 1-2 句，聚焦案情與程序結論，避免贅述；建議 40-90 字。\\n"
        "2) holding：僅抽取具處分性/裁判主文效果的結論（例如駁回、撤銷、改判、維持、發回），避免重複案情。\\n"
        "3) legal_basis：僅列出文本中可辨識的法條/法律依據；若無明確依據，回傳空陣列。\\n"
        "4) disputed_issues：僅列爭點（法律或事實爭執點）；去除程序噪音與泛化描述；每點盡量短句。\\n"
        "5) 資訊不足時，字串欄位用空字串，陣列欄位用空陣列。\\n"
        "6) 強制使用繁體中文（zh-Hant）；嚴禁簡體字。\\n"
        f"案件編號: {context.authoritative_case_number}\\n"
        f"案件語言: {context.language}\\n"
        f"案件類型: {context.case_type}\\n"
        "案件文本：\\n"
        f"{context.clipped_text}"
    )


def _render_legacy_prompt(context: PromptContext) -> str:
    return (
        "你是法律判決摘要與結構化資訊抽取助手。"
        "請根據以下案件文本，僅輸出 JSON，不要輸出其他文字。\\n"
        f"prompt_version: {context.prompt_version}\\n"
        "JSON 結構必須包含這四個欄位："
        "case_summary (string), holding (string), legal_basis (string array), disputed_issues (string array)。\\n"
        "要求：\\n"
        "1) 絕對必須使用繁體中文（Traditional Chinese, zh-TW/zh-HK）輸出，嚴禁使用簡體字；\\n"
        "2) 內容要精簡但忠於文本；\\n"
        "3) legal_basis 只填在文本中可辨識的法條或法律依據；\\n"
        "4) 如果資訊不足，請使用空字串或空陣列。\\n"
        f"案件編號: {context.authoritative_case_number}\\n"
        f"案件語言: {context.language}\\n"
        f"案件類型: {context.case_type}\\n"
        "案件文本：\\n"
        f"{context.clipped_text}"
    )
