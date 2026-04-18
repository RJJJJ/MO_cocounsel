# Failure modes

## 1) 站點封鎖或 403
- 現象：直接 `curl` 403，但瀏覽器路徑有機會可用。
- 影響：raw html 抓取失敗或內容不完整。

## 2) Index 文本噪音高
- 現象：行文本含大量 UI 字樣、重複空白、裝飾符。
- 影響：LLM 誤判 part/chapter/section。

## 3) LLM output 非 JSON
- 現象：模型附帶說明文字或 markdown。
- 影響：分類管線中斷。

## 4) Article 內文無明確標頭
- 現象：頁面正文未出現 `Artigo N` 的標準格式。
- 影響：article_number 抽取缺失。

## 5) URL 去重不足
- 現象：同一 article 多次抓取。
- 影響：重複資料污染 manifest 統計。
