# Day 59A Hotfix Acceptance (Run-Completion Semantics)

## Today objective

Apply a minimal Day 59A hotfix so per-court crawl child and full-corpus parent can distinguish:

1. acceptable non-fatal stop conditions (practical page exhaustion / late-page instability after useful earlier extraction), and
2. true fatal failures.

The goal is to prevent a single court's late-page timeout from incorrectly failing the whole full-corpus assembly.

## Exact bug being fixed

Current behavior treated late-page `wait_for_selector` timeout in per-court child as fatal and returned non-zero.
Parent is fail-fast on non-zero child exits, so full-corpus assembly aborted even when earlier pages were already parsed successfully and many records were already added.

Example observed bug shape:
- court TA pages 1..8 parsed with useful records
- page 9 timeout occurs
- child exits 1
- parent aborts full-corpus build

## Acceptable non-fatal termination

For this round, the following is acceptable and should exit code 0:

- result pages exhausted / no practical further stable pages
- invalid/no-result later page after useful earlier pages
- late-page timeout/error **after** useful progress already happened

Useful progress for this hotfix is explicitly scoped to:
- at least one valid result page parsed, **and**
- at least one corpus record successfully produced.

When this happens, child marks run status as `partial_success` (or `success` for normal exhaustion-like stop) and logs an explicit stop reason.

## Fatal failure definition

True fatal failure means crawl could not meaningfully establish/use court result pages and extraction flow, such as:

- environment/runtime dependency missing (e.g., Playwright unavailable)
- failure before useful extraction starts
- unrecoverable navigation/parsing failure before meaningful page parsing + record production

Fatal failures return non-zero, and parent keeps fail-fast behavior.

## Deliverables

- Update child crawler status semantics and exit behavior:
  - `success`
  - `partial_success`
  - `fatal_failure`
- Ensure late-page timeout after useful progress is treated as non-fatal stop with explicit report/log reason.
- Preserve existing stats/report shape as much as possible.
- Keep parent fail-fast on non-zero, and compatible with child exit-0 acceptable partial completion.

## Acceptance checklist

- [ ] Child report/summary includes explicit `run status` and `stop reason`.
- [ ] Child returns exit code 0 for late-page timeout when useful progress already exists.
- [ ] Child keeps non-zero exit for pre-extraction / true fatal failures.
- [ ] Parent continues normal full-corpus assembly when child exit code is 0.
- [ ] Parent still fail-fast when child exit code is non-zero.
- [ ] No Day 59A strategy redesign; only minimal run-semantics hotfix.

## Evidence developer must provide

- Changed file list.
- Concise semantics explanation.
- Example CLI command.
- Sample child summary/report shape (showing run status + stop reason).
- Clarification why TA late-page timeout no longer kills full-corpus parent run.

## Explicit example

If TA crawl successfully parses earlier pages and writes records, then later page timeout (e.g., page 9) is classified as practical end-of-range for this round:

- child run status: `partial_success`
- child exit code: `0`
- stop reason includes late-page timeout treated non-fatal
- parent sees exit 0 and continues merging all courts normally

This hotfix addresses run-completion semantics only; it does **not** claim complete harvest coverage for every configured page.
