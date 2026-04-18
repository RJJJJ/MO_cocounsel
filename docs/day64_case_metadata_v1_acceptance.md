# Day 64 Acceptance - Case Metadata v1 (Post-merge Attach)

## 本輪對應功能
對應功能總表：
- A. CoCounsel 核心能力清單
  - 法律研究 Research
    - 案例導向研究摘要
    - 法條導向研究摘要
    - Issue decomposition / query-to-issue matching
  - 起草與工作成果生成 Drafting / Work Product
    - 案例 brief 生成
    - 研究 memo 生成

本輪僅交付 metadata 最小可用能力：
1. 固定 6 欄 case-level metadata schema
2. authoritative identity 採 `sentence_id`
3. post-merge attach pipeline
4. metadata case-level 可消費 demo

## 新增檔案
- `docs/metadata_schema_v1.md`
- `crawler/prep/build_case_metadata_v1.py`
- `crawler/prep/attach_case_metadata_v1.py`
- `retrieval/debug/demo_case_metadata_usage.py`
- `docs/day64_case_metadata_v1_acceptance.md`

## Local run
```bash
python crawler/prep/build_case_metadata_v1.py
python crawler/prep/attach_case_metadata_v1.py
python retrieval/debug/demo_case_metadata_usage.py --issue-query '量刑過重' --legal-basis-query '第40條' --top-k 3
```

## 輸出路徑
- metadata builder output:
  - `data/corpus/metadata/case_metadata_v1.jsonl`
  - `data/corpus/metadata/case_metadata_v1_report.json`
- attach output (new path, non-destructive):
  - `data/corpus/raw/macau_court_cases_full_metadata_v1/manifest.metadata_attached_v1.jsonl`
  - `data/corpus/raw/macau_court_cases_full_metadata_v1/case_metadata_v1.jsonl`
  - `data/corpus/raw/macau_court_cases_full_metadata_v1/attach_case_metadata_v1_report.json`

## 6 欄用途
1. `case_summary`: 案件概覽 / 研究 memo 前置摘要
2. `holding`: 直接回答「法院怎麼判」
3. `disputed_issues`: query-to-issue matching
4. `legal_basis`: 法律依據召回
5. `reasoning_summary`: 裁判理由摘要
6. `doctrinal_point`: 法官釋法 / 裁判要旨

## Demo 結果（sample）
### A) holding 回答「法院怎麼判」
- case `36/2026` (sentence_id `42353`) 可直接輸出 holding 文字回答。

### B) disputed_issues 做 query-to-issue matching
- query: `量刑過重`
- top hit examples:
  - `1073/2025` issues 含 `量刑過重`
  - `757/2025` issues 含 `量刑過重`
  - `34/2026` issues 含 `量刑過重`

### C) legal_basis 做法律依據召回
- query: `第40條`
- top hit examples:
  - `1073/2025` legal_basis 含 `《刑法典》第40條`
  - `757/2025` legal_basis 含 `第40條`
  - `206/2026` legal_basis 含 `第40條`

## 本地執行統計（本次環境）
- total cases processed: 3120
- full 6 欄都非空：0
- 各欄非空比例：
  - `case_summary`: 2.47%
  - `holding`: 2.47%
  - `disputed_issues`: 2.47%
  - `legal_basis`: 2.47%
  - `reasoning_summary`: 0.00%
  - `doctrinal_point`: 0.00%

## Known limitations
1. 目前 repository 內未附 full text case files（manifest 可用，但 case full_text/metadata 檔多數不在 repo），導致 deterministic fallback 的文字抽取覆蓋有限。
2. model/baseline metadata 既有產物多只含 4 欄（case_summary/holding/disputed_issues/legal_basis），因此 `reasoning_summary` 與 `doctrinal_point` 目前主要依賴 full-text fallback。
3. holding 品質仍受來源文本段落噪音影響（仍已限制短輸出與固定 schema，後續可再加句段過濾規則）。
4. 本輪未更動 BM25+ 主路徑、未加入 reranker/agent/dense 擴張，符合 scope 限制。
