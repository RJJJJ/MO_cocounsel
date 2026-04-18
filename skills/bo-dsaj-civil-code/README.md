# bo-dsaj-civil-code skill notes (prototype)

目的：沉澱《澳門民法典》statute ingestion prototype 的可複用方法，供未來其他法典沿用。

## Workflow（第一輪）
1. 用 Playwright CLI 對 index 頁做快照與原始保留（HTML/TXT/PNG）。
2. 抽 index 行文本為 `index_lines.jsonl`。
3. 用 Ollama `qwen3:4b-instruct` 對每行分類（僅 6 種 node_type）。
4. 用 deterministic stack（line order）重建 hierarchy。
5. 從 index 提取 article URL，抓取一批 article page。
6. 解析 article_number / heading / text，對齊 hierarchy_path。
7. 產出 article-level JSONL + manifest。

## Reuse boundaries
- 本輪只做 ingestion/structuring/manifest，不做 dense retrieval/reranker/mixed mode。
- 新法典沿用同一資料分層：raw -> intermediate -> structured -> manifest。

## Entrypoints
- `crawler/statutes/fetch_civil_code_index_with_playwright_cli.py`
- `crawler/statutes/classify_civil_code_index_lines_with_ollama.py`
- `crawler/statutes/build_civil_code_hierarchy.py`
- `crawler/statutes/fetch_civil_code_article_pages.py`
- `crawler/statutes/parse_civil_code_articles.py`
- `crawler/statutes/build_civil_code_manifest.py`
