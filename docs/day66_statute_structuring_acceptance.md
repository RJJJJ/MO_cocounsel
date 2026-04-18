# Day 66 Acceptance - Statute Structuring Prototype

## Acceptance checklist
- [ ] 可抓取民法典 index，保留 raw html/txt/png 快照
- [ ] 可產出 `index_lines.jsonl`
- [ ] 可產出 line-level node_type classification（僅 6 類）
- [ ] 可重建 hierarchy（非 LLM 直出樹）
- [ ] 可發現 article URL pattern 並抓取一批 article pages
- [ ] 可抽 `article_number/article_heading/article_text/hierarchy_path/source_url`
- [ ] 可生成 article-level JSONL
- [ ] 可生成 manifest v1
- [ ] skills 內有 site patterns / failures / recovery / selectors
- [ ] docs 內有本地部署與運行指南

## Suggested local run commands
1. `python crawler/statutes/fetch_civil_code_index_with_playwright_cli.py`
2. `python crawler/statutes/classify_civil_code_index_lines_with_ollama.py --model qwen3:4b-instruct`
3. `python crawler/statutes/build_civil_code_hierarchy.py`
4. `python crawler/statutes/fetch_civil_code_article_pages.py --max-pages 30`
5. `python crawler/statutes/parse_civil_code_articles.py`
6. `python crawler/statutes/build_civil_code_manifest.py`

## Review focus
- `needs_review=true` 的文章條目
- article number regex 命中率
- hierarchy stack 組裝是否符合 part/chapter/section 順序
