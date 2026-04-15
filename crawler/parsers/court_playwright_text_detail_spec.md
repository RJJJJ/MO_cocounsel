# Day 11 Playwright text-detail refinement spec

## What was wrong in Day 10 extraction

1. `case_number` 被日期字首誤抓成 `26/03`，因為 regex 在整段文字中先匹配到日期片段。
2. `case_type` 被誤切成 `/2026`，因為是用錯誤 `case_number` 後方字串做切割。
3. `text_url` 長期為 null，原因是 Day 10 只靠 `a` 文字或 href 關鍵字；但 TXT icon link 常是圖片節點（innerText 幾乎空白），需同時解析父層 anchor / class / src。
4. `decision_result`、`reporting_judge` 會被摘要大段文字污染，需以欄位標籤 + stop-key 截斷策略解析。

## Corrected case_number / case_type strategy

- 先從結構化欄位取值：
  - `span.num` 作為 case number 主來源（`\d+/\d{4}`）
  - `span.type` 作為 case type 主來源（避免由 raw text 切片）
- 若欄位缺失，再 fallback 到整卡 raw text。
- `decision_date` 優先取 `span.date`，再 fallback raw text。

## TXT/fulltext entry implementation on site

在結果卡的 `span.download` 中，TXT/fulltext 常以下列形式出現：

- `<a class="openNewWindow" href="/sentence/zh/42353" target="_blank"><img src="/images/icon_txtc.png"></a>`
- 或葡文版 `<img src="/images/icon_txtp.png">`

實作重點：

- 不只看 `href` 文字；也檢查 clickable node 與其 ancestor anchor 的：
  - `href`
  - `onclick`
  - `class`
  - `img src`
  - 以及是否符合 `/sentence/(zh|pt)/<id>` pattern
- 支援 target 新頁籤（popup）與可能 overlay/modal 容器（fancybox/mfp/modal）。

## TXT type conclusion (URL / modal / popup / JS)

以目前 Day 11 probe 實測：

- 主要是 **plain URL + popup/new tab**（`target="_blank"`）型態。
- 程式同時保留對 `onclick/javascript/modal/popup trigger` 的檢測與 fallback。
- 尚未觀察到必須依賴 JS-only 才能取得內文的卡片，但已加上保護邏輯。

## Extraction strategy for text-detail pages

1. 用 Playwright 先走搜尋流程取得結果卡。
2. 對前 1–3 張有 text entry 的卡，直接點擊 TXT/fulltext 入口。
3. 捕捉 popup（`expect_popup`），若無 popup 則檢查 same-tab / overlay。
4. 以多 selector 擷取正文（`#content`, `.maincontent`, `.case_summary`, `article`, `body`）。
5. 輸出 sample JSON，欄位包含：
   - `case_number`
   - `decision_date`
   - `title_or_issue`
   - `full_text`
   - `source_type="txt/fulltext"`
   - `extracted_from`

## Remaining uncertainties

- 某些歷史判決頁可能使用舊版模板，正文 selector 需再擴充。
- overlay/modal 情境目前有支持但需更大量樣本驗證。
- 目前只做單頁結果，不含 pagination，因此 coverage 仍受首頁回傳筆數限制。

## Recommended next step

建議下一輪優先：

1. **batch text-detail extraction**：先在單頁範圍內對所有卡穩定抽取 TXT 內容並加上 retry。
2. 再做 **pagination**：擴展結果頁遍歷，串接批次抽取流程。
