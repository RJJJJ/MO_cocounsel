# Metadata Schema v1 (Case-level, Post-merge Attach)

## Scope
本文件定義 Day 64 的最小可用案件級 metadata schema，僅覆蓋 authoritative merged full-case corpus 的 post-merge attach 階段。

authoritative flow 固定為：

`per-court convergence crawl -> merge/dedupe authoritative corpus -> retrieval consumption -> metadata attach post-merge`

## Authoritative identity
- Primary key: `sentence_id`
- 若無 `sentence_id`：不納入 authoritative metadata attach（保留空值並記錄原因）

## Schema definition (v1)
每筆 `sentence_id` 對應一個 `case_metadata_v1` 物件，固定 6 欄：

1. `case_summary` (string)
   - 案件事實摘要
   - 供案例概覽、研究 memo 前置摘要使用

2. `holding` (string)
   - 裁判結果 / 主文結論
   - 優先 1–3 句，可直接回答「法院怎麼判」

3. `disputed_issues` (array[string])
   - 爭議焦點
   - 格式偏檢索可消費（短語列表），供 query-to-issue matching

4. `legal_basis` (array[string])
   - 主要法條 / 法律依據
   - 格式偏檢索可消費（法條片語列表），供法律依據召回

5. `reasoning_summary` (string)
   - 裁判理由摘要
   - 承接「裁判理由」類問答與 memo 理由段落草稿

6. `doctrinal_point` (string)
   - 法官釋法 / 裁判要旨 / 抽象法理命題
   - 承接法理命題、可遷移原則生成

## Source selection policy
- Preferred: model-generated metadata（若可用）
- Fallback: deterministic extraction（可重跑、穩定）
- 若仍無法抽取：允許空值，但必須在 `field_sources` 記錄 `empty`

## Output contract (builder output row)
每列 JSONL 至少包含：
- `sentence_id` (string)
- `authoritative_case_number` (string)
- `authoritative_decision_date` (string)
- `language` (string)
- `case_metadata_v1` (object, fixed 6 fields)
- `field_sources` (object, 6 fields each in `{model_generated, deterministic_fallback, empty}`)

## Stability / rerun requirements
- deterministic rules 不依賴外部服務
- 固定欄位名稱與輸出 shape
- list 欄位去重、保序、限制最大長度
- holding 控制短輸出（1–3 句）

## Non-goals (Day 64)
- 不替換 BM25+ 主路徑
- 不新增 reranker / agent / planner
- 不做 dense retrieval 擴張
- 不做大型 API 改造
