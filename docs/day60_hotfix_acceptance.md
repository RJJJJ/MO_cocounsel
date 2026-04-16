# Day 60 Hotfix Acceptance: Round-Local Page Signature Dedupe

## Today Objective
Fix one focused Day 60 convergence-crawl bug: page-signature duplicate detection must be scoped **within a single round**, not shared across rounds.

## Exact Bug Being Fixed
In the child crawler (`crawler/pipeline/add_all_court_crawling_mode.py`), page signatures were previously tracked in a run-global set across convergence rounds.

That caused this failure mode:
1. Round 1 sees page signatures for early pages.
2. Round 2 revisits page 1 (expected behavior in Day 60).
3. The same signature is incorrectly treated as a duplicate loop.
4. Round 2 stops too early (often on page 1 or near the front).

## Why This Causes False Convergence / Page Undercount
Day 60 convergence relies on rescans because source-site page drift can move records between pages over time.

If round 2+ is prematurely stopped by cross-round page-signature reuse, crawler coverage shrinks artificially:
- fewer valid pages parsed per round
- fewer opportunities to discover drifted sentence IDs
- zero-new rounds happen too soon
- court appears to converge early even when tail pages still exist

## State Scope Rules (Hotfix Contract)
### Round-local state
- `seen_page_signatures_this_round`
- Purpose: detect loops/repeated result pages **inside the same round only**.

### Cross-round state
- `seen_sentence_ids`
- Purpose: authoritative sentence_id-first dedupe across the whole court run.
- This remains unchanged and must stay enabled.

## Deliverables
- [x] Child crawler hotfix to move page-signature dedupe into per-round scope.
- [x] Explicit code comments clarifying round-local vs cross-round state.
- [x] Keep existing stop reason/audit shape compatible (`duplicate result page signature ...`).
- [x] No orchestration redesign in parent script.
- [x] This acceptance doc added.

## Acceptance Checklist
- [ ] Round 2 revisiting page 1 no longer triggers duplicate-page stop due to round 1 history.
- [ ] Duplicate-page stop still works for repeated pages within the same round.
- [ ] sentence_id already seen in prior rounds is still skipped.
- [ ] Convergence logic/formula remains unchanged.
- [ ] No retrieval/agent/frontend policy changes.

## Evidence Developer Must Provide
1. Diff showing `seen_page_signatures` removed from run-global scope and replaced by a round-local structure.
2. Code comment that explicitly states:
   - cross-round rescans are expected because page drift exists
   - cross-round page repetition is normal
   - sentence_id dedupe remains cross-round.
3. A run command example for convergence mode.
4. Brief explanation of why TSI/TJB should no longer be artificially truncated by cross-round page-signature reuse.

## Explicit Examples
### Example A (must be allowed)
- Round 1 crawls page 1 and records signature S.
- Round 2 starts and revisits page 1, also sees S.
- **Expected:** continue normally; no duplicate-result-page stop, because S from round 1 is out-of-scope.

### Example B (must still be skipped)
- Round 1 discovered `sentence_id=ABC123` and added it to seen sentence IDs.
- Round 2 sees `sentence_id=ABC123` again.
- **Expected:** skip as duplicate sentence_id (cross-round dedupe still correct).

## Example CLI Command
```bash
python crawler/pipeline/add_all_court_crawling_mode.py \
  --court tsi \
  --until-converged \
  --max-rounds 6 \
  --zero-new-round-stop 2 \
  --start-page 1 \
  --end-page 200
```
