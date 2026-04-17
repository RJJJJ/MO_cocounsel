#!/usr/bin/env python3
"""Auditable lexical mappings for BM25-oriented legal retrieval strengthening."""

from __future__ import annotations

# Keep canonical mappings deterministic and reviewable.
# Sort by key length at usage sites when replacement order matters.
VARIANT_TO_CANONICAL = {
    "提前釋放": "假釋",
    "提前释放": "假釋",
    "有條件釋放": "假釋",
    "保释": "假釋",
    "保釋": "假釋",
    "量刑明顯過重": "量刑過重",
    "量刑明显过重": "量刑過重",
    "刑罰過重": "量刑過重",
    "刑罚过重": "量刑過重",
    "判刑過重": "量刑過重",
    "判刑过重": "量刑過重",
    "暫緩執行": "緩刑",
    "暂缓执行": "緩刑",
    "假釋申請": "假釋",
    "合約不能履行": "合同不能履行",
    "合同之不能履行": "合同不能履行",
    "不能履行合同": "合同不能履行",
    "損失賠償": "損害賠償",
    "賠償損失": "損害賠償",
    "损害赔偿": "損害賠償",
    "诽谤": "誹謗",
    "名誉损害": "名譽受損",
    "名譽損害": "名譽受損",
    "上诉": "上訴",
    "終審上訴": "上訴",
    "假释": "假釋",
}

# Canonical legal concepts to practical lexical expansions (zh + pt + colloquial).
HIGH_VALUE_EXPANSION = {
    "假釋": ["提前釋放", "有條件釋放", "liberdade condicional", "刑法典第56條"],
    "量刑過重": ["刑罰過重", "判刑過重", "erro ostensivo na apreciação da prova", "改判"],
    "緩刑": ["緩期執行", "暫緩執行"],
    "上訴": ["提起上訴", "recurso", "recorrer"],
    "損害賠償": ["民事賠償", "responsabilidade civil", "indemnização", "dano moral"],
    "合同不能履行": ["履行不能", "債務不履行", "incumprimento contratual"],
    "誹謗": ["名譽", "侮辱", "difamação"],
    "假釋撤銷": ["revogação da liberdade condicional", "撤銷假釋"],
}

# Additional lexical hooks used directly by tokenizer for chinese concept matching.
ZH_LEGAL_MULTI_CHAR_HINTS = {
    "假釋",
    "緩刑",
    "量刑",
    "上訴",
    "損害賠償",
    "合同不能履行",
    "誹謗",
    "詐騙",
    "違令",
    "刑法典",
}
