# Recovery playbook

## A. Playwright CLI 失敗
1. 確認 `playwright --version`。
2. 執行 `playwright install chromium`。
3. 降低 timeout 並重試 snapshot。
4. 若仍失敗，保留錯誤狀態到 report（不要 silent fail）。

## B. Ollama 不可用
1. 確認 `ollama serve` 是否啟動。
2. 檢查 `http://127.0.0.1:11434/api/tags`。
3. 尚未拉模型時先 `ollama pull qwen3:4b-instruct`。
4. 緊急 fallback：`--no-ollama` 走 heuristic（並標記 needs_review）。

## C. Hierarchy 異常
1. 檢查分類是否超出允許 node_type（應全部收斂到 6 類）。
2. 檢查 stack pop/push 規則是否遵守 part>chapter>section。
3. heading 不入層級 stack，只附著當前 path。

## D. Article 解析缺欄位
1. 先用 index 對齊補 `article_number` / `hierarchy_path`。
2. 對缺 number 或空 text 標記 `needs_review=true`。
3. 不以 LLM 自由補全文，避免 hallucination。
