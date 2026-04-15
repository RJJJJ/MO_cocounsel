# Day 15 Spec: Refine Paginated Result-Card Link Preservation

## Why Day 14 pagination is considered successful

Day 14 fixed the navigation model by making pagination stateful:

1. Playwright opens the real search UI.
2. It selects court and submits a real search.
3. Page 1 is parsed from submitted result state.
4. Page 2/3 are derived from that submitted result URL.

This solved the previous false-pagination issue (URL looked paginated but rendered search shell). Day 14 evidence showed pages 1/2/3 parsed with stable card counts and sensible dedupe behavior.

## Why text/fulltext link preservation is the current bottleneck

Despite pagination stability, Day 14 reported `total resolved sentence URLs: 0`. This indicates link extraction inside paginated cards is weaker than the earlier validated single-page behavior.

Likely causes:

- link detection over-relied on visible anchor text labels,
- some text/fulltext entries are represented by icons/spans/buttons,
- some entries are action-based (`onclick`/`javascript:`) instead of plain `href`,
- paginated DOM variants expose document entry data through non-anchor attributes.

## Refined link extraction strategy

The Day 15 refined parser keeps Day 14 stateful pagination unchanged, but upgrades in-card document extraction:

1. Parse pages 1, 2, 3 from state-compatible paginated URLs.
2. For each candidate result card, inspect **all document-related nodes** inside card context:
   - `a`
   - `button`
   - `[role="button"]`
   - `span`
   - icon-like nodes (`i`)
3. Read both text and attributes:
   - `href`
   - `onclick`
   - `data-href`
   - `data-url`
   - `data-target`
   - `title`
   - `aria-label`
   - `class`
4. Build normalized candidates and classify:
   - PDF candidate
   - text/fulltext candidate
   - zh sentence candidate
   - pt sentence candidate
5. Preserve text entry even without normal URL:
   - if actionable but no plain href, store `action:<descriptor>` in `text_url_or_action`.

## zh / pt sentence link detection rules

- zh sentence: URL/action payload contains `/sentence/zh/<id>`.
- pt sentence: URL/action payload contains `/sentence/pt/<id>`.
- Resolution priority for `text_url_or_action`:
  1. zh sentence
  2. pt sentence
  3. generic text/fulltext candidate
  4. action descriptor fallback

## Success criteria

A Day 15 run is successful when:

- Day 14 stateful pagination behavior remains intact (pages 1/2/3 parsed from submitted state).
- Output cards preserve both PDF and text/fulltext entry info where available.
- Report includes:
  - pages parsed
  - total cards before dedupe
  - total cards after dedupe
  - cards with `pdf_url`
  - cards with `text_url_or_action`
  - cards with both
  - zh text links count
  - pt text links count
  - whether paginated text-link resolution appears successful
- Artifacts are produced:
  - `data/parsed/court_probe/playwright_result_cards_paginated_refined.json`
  - `data/parsed/court_probe/playwright_pagination_refined_report.txt`

## Recommended next step

Choose one next phase (outside Day 15 scope):

1. Batch text-detail extraction from refined paginated cards.
2. Build raw corpus storage layout for immutable text snapshots + metadata index.
