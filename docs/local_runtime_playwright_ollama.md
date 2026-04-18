# Local Runtime: Playwright CLI + Playwright Python + Ollama

> 本文件對應 Day 66 statute structuring prototype 的本地部署與執行。

## 1) 安裝 Playwright CLI

### Node.js
```bash
node --version
npm --version
```
若未安裝，先安裝 Node.js 18+。

### 安裝 Playwright CLI
```bash
npm install -g playwright
playwright --version
```

## 2) 安裝 Playwright skills（專案內）
本輪在 repo 內提供可複用 skill docs：
- `skills/bo-dsaj-civil-code/README.md`
- `skills/bo-dsaj-civil-code/site_patterns.md`
- `skills/bo-dsaj-civil-code/failure_modes.md`
- `skills/bo-dsaj-civil-code/recovery_playbook.md`
- `skills/bo-dsaj-civil-code/selectors_and_snapshots.md`

## 3) 若需 Playwright Python
```bash
python -m pip install playwright
python -m playwright install chromium
```

## 4) 安裝與啟動 Ollama
參考官方安裝方式後，啟動服務：
```bash
ollama serve
```
預設 API：`http://127.0.0.1:11434`

## 5) 拉取 qwen3:4b-instruct
```bash
ollama pull qwen3:4b-instruct
ollama list
```

## 6) 執行順序（statute prototype）
```bash
python crawler/statutes/fetch_civil_code_index_with_playwright_cli.py
python crawler/statutes/classify_civil_code_index_lines_with_ollama.py --model qwen3:4b-instruct
python crawler/statutes/build_civil_code_hierarchy.py
python crawler/statutes/fetch_civil_code_article_pages.py --max-pages 30
python crawler/statutes/parse_civil_code_articles.py
python crawler/statutes/build_civil_code_manifest.py
```

## 7) 產出位置
- Raw snapshots:
  - `data/raw/statutes/civil_code/index/index_raw.html`
  - `data/raw/statutes/civil_code/index/index_raw.txt`
  - `data/raw/statutes/civil_code/index/index_raw.png`
  - `data/raw/statutes/civil_code/articles/*.html`
- Intermediate:
  - `data/parsed/statutes/civil_code/index/index_lines.jsonl`
  - `data/parsed/statutes/civil_code/index/index_lines_classified.jsonl`
  - `data/parsed/statutes/civil_code/index/hierarchy_nodes.jsonl`
  - `data/parsed/statutes/civil_code/index/article_index.jsonl`
- Structured:
  - `data/parsed/statutes/civil_code/articles/articles_structured.jsonl`
- Manifest:
  - `data/parsed/statutes/civil_code/manifest/civil_code_manifest_v1.json`

## 8) 常見失敗與排查
- Playwright CLI 找不到：
  - `playwright --version` 檢查 PATH。
- screenshot 失敗：
  - `playwright install chromium` 後重試。
- Ollama 連不上：
  - 確認 `ollama serve`；測 `curl http://127.0.0.1:11434/api/tags`。
- LLM 非 JSON 輸出：
  - 目前分類腳本有 JSON 擷取與 heuristic fallback。
- article number 抽不到：
  - 會以 index 對齊補值並標 `needs_review=true`。
