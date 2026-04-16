#!/usr/bin/env python3
"""Traditional Chinese normalization helpers for model-generated metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CJK_RE = re.compile(r"[\u3400-\u9FFF]")

# Minimal fallback map for common Simplified -> Traditional conversions
# used in legal summary style text when OpenCC is unavailable.
_FALLBACK_SIMP_TO_TRAD = {
    "这": "這",
    "为": "為",
    "与": "與",
    "争": "爭",
    "议": "議",
    "点": "點",
    "审": "審",
    "查": "查",
    "确认": "確認",
    "维": "維",
    "处": "處",
    "罚": "罰",
    "诉": "訴",
    "讼": "訟",
    "条": "條",
    "体": "體",
    "后": "後",
    "发": "發",
    "门": "門",
    "国": "國",
    "应": "應",
    "执": "執",
    "认": "認",
    "实": "實",
}


@dataclass(frozen=True)
class NormalizationResult:
    text: str
    changed: bool
    output_script: str


def _fallback_to_traditional(text: str) -> str:
    output = text
    for simp, trad in sorted(_FALLBACK_SIMP_TO_TRAD.items(), key=lambda item: len(item[0]), reverse=True):
        output = output.replace(simp, trad)
    return output


def _opencc_to_traditional(text: str) -> str:
    try:
        from opencc import OpenCC  # type: ignore

        return OpenCC("s2t").convert(text)
    except Exception:
        return _fallback_to_traditional(text)


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def normalize_text_to_traditional(text: str) -> NormalizationResult:
    if not text or not _contains_cjk(text):
        return NormalizationResult(text=text, changed=False, output_script="not_applicable")

    normalized = _opencc_to_traditional(text)
    changed = normalized != text
    output_script = "traditional_chinese" if _contains_cjk(normalized) else "unknown"
    return NormalizationResult(text=normalized, changed=changed, output_script=output_script)
