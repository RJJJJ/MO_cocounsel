# Site patterns (BO/DSAJ Civil Code prototype)

## Index page
- 常見路徑：`.../codciv/indice_art.asp`
- 目錄多為「結構行 + 文章連結行」混排。
- 同頁會含導覽噪音（例如返回、首頁、語言切換字樣）。

## Article page URL pattern
- 從 index 的 `<a href="...">` 抽出 article 連結。
- 連結通常為相對路徑，需用 `urljoin(index_url, href)` 正規化。

## Hierarchy signals
- `Livro/Parte` -> part
- `Título/Capítulo` -> chapter
- `Secção` -> section
- `Art.` / `Artigo` + number -> article
- 其餘可作 heading 或 noise

## Repeatable extraction strategy
1. 先完整保留 raw html + raw text。
2. link-text 對位後再做分類。
3. hierarchy 一律程式重建，不交給 LLM 直接生成樹。
