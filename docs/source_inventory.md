# Source Inventory (Day 1)

The inventory below captures target sources for Day 2 ingestion validation.

## 1) Macau Courts – Judgment Search

- **source_name:** Macau Courts – Judgment Search
- **base_url:** https://www.court.gov.mo/zh/subpage/researchjudgments
- **source_type:** Judicial portal / judgment search
- **official_or_unofficial:** Official
- **expected_content:** Public judgments, case identifiers, decision dates, court-level metadata, subject tags, search result metadata, and linked judgment files (PDF/HTML where available)
- **access_pattern:** Search/list results pages with filters and detail views; pagination and court/category filtering expected
- **parsing_difficulty:** Medium-High
- **need_playwright:** Yes (likely)
- **need_ocr_fallback:** Yes (for scanned PDFs)
- **legal_or_operational_risks:** Potential anti-bot controls, dynamic UI changes, partial metadata consistency across result pages, and result/detail structure drift over time
- **day2_priority:** P0

## 2) Macau Official Gazette / Boletim Oficial

- **source_name:** Macau Official Gazette / Boletim Oficial
- **base_url:** https://bo.io.gov.mo
- **source_type:** Government gazette / legislation publication
- **official_or_unofficial:** Official
- **expected_content:** Statutes, regulations, promulgation notices, and legal updates
- **access_pattern:** Archive browsing by issue/date; primarily document-centric retrieval
- **parsing_difficulty:** Medium
- **need_playwright:** No (initially)
- **need_ocr_fallback:** Yes (for older scanned content)
- **legal_or_operational_risks:** Historical format variance, bilingual alignment complexity, citation normalization effort
- **day2_priority:** P0

## Notes

- For case-law retrieval, Day 2 uses **only** the Macau Courts Judgment Search page as the initial judicial source.
- “Latest Judgments” is **not** treated as a separate ingestion source in the MVP unless later testing shows a material coverage gap.
- Day 2 should confirm whether Playwright is strictly required for each source by running minimal fetch probes.
- OCR fallback should be opt-in by source and by file-level detection, not globally enabled.
- Only public, legally accessible materials should be ingested.
