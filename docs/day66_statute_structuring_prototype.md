# Day 66 - Statute Structuring Prototype（澳門民法典）

## 目標
在不影響既有 case metadata generation 主線的前提下，建立 statute ingestion/structuring 的最小可用底座。

## 本輪範圍（有做）
- Playwright CLI index snapshot + raw capture
- index line extraction
- Ollama line-level node_type classification（6 類）
- deterministic hierarchy rebuild（line order + stack）
- article URL 批次抓取
- article-level parsing + JSONL 輸出
- manifest v1
- 可複用 skill docs 沉澱

## 本輪範圍（刻意不做）
- statute dense retrieval
- mixed mode runtime
- reranker
- statute metadata 大規模生成

## Pipeline
1. `fetch_civil_code_index_with_playwright_cli.py`
2. `classify_civil_code_index_lines_with_ollama.py`
3. `build_civil_code_hierarchy.py`
4. `fetch_civil_code_article_pages.py`
5. `parse_civil_code_articles.py`
6. `build_civil_code_manifest.py`

## 輸出分層
- Raw capture：`data/raw/statutes/civil_code/...`
- Intermediate：`data/parsed/statutes/civil_code/index/...`
- Structured：`data/parsed/statutes/civil_code/articles/articles_structured.jsonl`
- Manifest：`data/parsed/statutes/civil_code/manifest/civil_code_manifest_v1.json`

## 資料模型
### Structured statute unit（article level）
- code_id
- code_name_zh
- article_canonical_id
- article_number
- article_heading
- hierarchy_path
- article_text
- language
- source_url
- parse_method
- confidence
- needs_review

### Hierarchy nodes
- node_type
- label
- title
- hierarchy_path
- order_index
- source_url
