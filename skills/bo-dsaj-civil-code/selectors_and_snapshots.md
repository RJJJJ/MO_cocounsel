# Selectors and snapshots

## Snapshot artifacts
- `data/raw/statutes/civil_code/index/index_raw.html`
- `data/raw/statutes/civil_code/index/index_raw.txt`
- `data/raw/statutes/civil_code/index/index_raw.png` (Playwright CLI screenshot)

## Link extraction target
- HTML `<a href="...">` anchors from index page.
- Anchor text 與 line text 做 normalized exact-match 對位。

## Article fetch artifacts
- `data/raw/statutes/civil_code/articles/*.html`
- `data/parsed/statutes/civil_code/articles/article_fetch_log.jsonl`

## Notes
- 本 prototype 以 robust text parsing 為主，不綁死 fragile CSS selector。
- 若後續法典站頁面結構不同，再於此檔新增 selector 變體。
