# Source Inventory (Day 1)

The inventory below captures target sources for Day 2 ingestion validation.

| source_name | base_url | source_type | official_or_unofficial | expected_content | access_pattern | parsing_difficulty | need_playwright | need_ocr_fallback | legal_or_operational_risks | day2_priority |
|---|---|---|---|---|---|---|---|---|---|---|
| Macau Courts official site | https://www.court.gov.mo | Judicial portal / judgments | Official | Cases (public judgments), court metadata, decision files | Mixed navigation with list pages and detail pages; likely PDF and/or HTML judgments | Medium-High | Yes (likely) | Yes (for scanned PDFs) | Potential anti-bot controls, changing page templates, partial metadata availability | P0 |
| Macau Official Gazette / Boletim Oficial | https://bo.io.gov.mo | Government gazette / legislation publication | Official | Statutes, regulations, promulgation notices, legal updates | Archive browsing by issue/date, often document-centric retrieval | Medium | No (initially) | Yes (for older scanned content) | Format variance across historical records, bilingual text alignment complexity, citation normalization effort | P0 |

## Notes

- Day 2 should confirm whether Playwright is strictly required for each source by running minimal fetch probes.
- OCR fallback should be opt-in by source and by file-level detection, not globally enabled.
- Only public, legally accessible materials should be ingested.
