# Browser Truth Check Hooks (Planned)

此資料夾保留給未來 Playwright / Playwright MCP truth-check hooks。

## 預計功能
- 抽樣開啟法典條文頁面
- 比對網頁標題、條號、內文與 parsed artifacts
- 產生 deterministic browser check records，回填 workflow state 的 `browser_checks`

## 建議輸入
- `articles_structured.jsonl`
- `article_fetch_log.jsonl`
- 抽樣策略（fixed seed）

## 建議輸出
```json
{
  "check_id": "browser-check-001",
  "article_number": "5",
  "source_url": "...",
  "result": "pass|fail",
  "evidence": {"dom_heading": "...", "parsed_heading": "..."}
}
```

## 接入位置
建議在 `run_validators` 後、`diagnose_failures` 前插入 browser check node。
