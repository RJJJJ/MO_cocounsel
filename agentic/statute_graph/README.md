# Statute LangGraph Self-Healing Workflow Skeleton

## 這個 graph 解決什麼問題
現有澳門民法典 ingestion prototype 已有 deterministic 腳本可跑，但無統一 orchestrator 來處理「驗收失敗 -> 診斷 -> 重試 / 停止 / 人審」循環。此模組提供 LangGraph workflow skeleton，在保留原腳本前提下，建立可循環、可檢查點、可診斷的控制層。

## deterministic pipeline 與 LangGraph 的分工
- **Deterministic pipeline（source of truth）**
  - `crawler/statutes/classify_civil_code_index_lines_with_ollama.py`
  - `crawler/statutes/build_civil_code_hierarchy.py`
  - `crawler/statutes/fetch_civil_code_article_pages.py`
  - `crawler/statutes/parse_civil_code_articles.py`
  - `crawler/statutes/build_civil_code_manifest.py`
- **LangGraph orchestration**
  - 控制 stage 順序
  - 保存 artifacts 路徑與每步摘要
  - 執行 deterministic validators
  - 收斂 failures，交給 LLM（目前 mock）做 structured diagnosis / patch proposal
  - 根據 retry budget 決定 retry / stop / human review

## 為什麼 validators 才是 source of truth
- validator 為 deterministic、可重現規則，不依賴 LLM 抽樣行為。
- LLM 僅輸出 diagnosis / patch 建議，不直接決定 correctness。
- 任何 stop/retry/human-review 決策都以 validator issue 為第一信號。

## 未來接入 Playwright / Playwright MCP browser checks
- 在 graph state 內已預留 `browser_checks` 欄位。
- 可新增節點（例如 `run_browser_truth_checks`）在 `run_validators` 後執行：
  - 使用 Playwright 自動開頁
  - 抽樣比對 article heading/text
  - 以結構化結果回填 `browser_checks`
- 細節接口見 `agentic/statute_graph/browser/README.md`。

## 未來接入 patch apply node
- `graph.py` 已預留 `patch_candidate` 節點與 routing 分支。
- v1 只輸出 `patch_proposal`，不自動改 production code。
- 後續可新增：
  1. `generate_patch_diff`
  2. `run_targeted_regression`
  3. `human_approve_patch`
  4. `apply_patch_and_retry`

## 依賴
- Python 3.10+
- `langgraph`（workflow runtime）

## 本地運行
```bash
python scripts/run_statute_graph.py --target-code-id mo-civil-code --max-retries 1 --mock-llm
```

常用參數：
- `--target-code-id`: statute code id
- `--max-retries`: validator fail 時最大重試次數
- `--mock-llm`: 啟用 mock diagnosis（建議先開）
- `--summary-output`: workflow final state 匯出路徑
