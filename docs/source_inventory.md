# Source Inventory (Day 1)

The inventory below captures target sources for Day 2 ingestion validation.

## 1) Macau Courts – Judgment Search

- **source_name:** Macau Courts – Judgment Search
- **base_url:** https://www.court.gov.mo/zh/subpage/researchjudgments
- **source_type:** Judicial portal / judgment search
- **official_or_unofficial:** Official
- **expected_content:** Public judgments, case identifiers, decision dates, court-level metadata, linked judgment files (PDF/HTML where available)
- **access_pattern:** Search/list results pages with detail views; pagination and filtering expected
- **parsing_difficulty:** Medium-High
- **need_playwright:** Yes (likely)
- **need_ocr_fallback:** Yes (for scanned PDFs)
- **legal_or_operational_risks:** Potential anti-bot controls, dynamic UI changes, partial metadata consistency across result pages
- **day2_priority:** P0

## 2) Macau Courts – Latest Judgments

- **source_name:** Macau Courts – Latest Judgments
- **base_url:** https://www.court.gov.mo
- **source_type:** Judicial portal / latest releases
- **official_or_unofficial:** Official
- **expected_content:** Recently published judgments and update-oriented listing pages
- **access_pattern:** Bulletin/list-style navigation from court portal sections; likely shallow-to-detail traversal
- **parsing_difficulty:** Medium
- **need_playwright:** Yes (likely)
- **need_ocr_fallback:** Yes (when linked files are scanned)
- **legal_or_operational_risks:** Section path changes, inconsistent labeling of “latest” views, potential duplication with search endpoint
- **day2_priority:** P1

## 3) Macau Official Gazette / Boletim Oficial

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

- Day 2 should confirm whether Playwright is strictly required for each source by running minimal fetch probes.
- OCR fallback should be opt-in by source and by file-level detection, not globally enabled.
- Only public, legally accessible materials should be ingested.
