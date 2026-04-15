# MVP Contract (Day 1 Baseline)

## Product Goal

Build a reliable **Macau Legal Retrieval Engine** that can retrieve, rank, and cite Macau public judgments and Macau statutes as the foundation for all later product layers.

This MVP contract explicitly prioritizes retrieval quality and evidence binding over conversational polish or multi-agent automation.

---

## Day 1–7 Implementation Contract

### Day 1: Foundation Contract and System Definition
- Lock MVP scope and acceptance criteria.
- Define source inventory for official Macau legal sources.
- Define initial domain entities and retrieval-oriented relations.
- Confirm non-goals: no agent orchestration implementation.

### Day 2: Source Connectivity and Fetching Skeleton
- Validate fetch strategies for at least two official legal sources.
- Document access constraints (pagination, PDF/HTML mix, anti-bot behavior).
- Produce first raw-source capture samples for parser design.

### Day 3: Parsing and Metadata Extraction Prototype
- Build parsing specs for judgments and statutes.
- Extract minimum metadata set (title, source URL, decision/effective date, language).
- Define parser failure categories and logging format.

### Day 4: Storage and Canonicalization Layer
- Define canonical schema mappings from raw sources to domain entities.
- Establish raw-to-structured transformation rules.
- Confirm document identity strategy (dedupe keys and source fingerprints).

### Day 5: Retrieval Indexing Baseline
- Define chunking policy and citation-anchor format.
- Produce baseline keyword index and vector index plan.
- Define retrieval response contract for case/statute mixed results.

### Day 6: Retrieval Evaluation Harness (Minimal)
- Create benchmark query list (small but representative).
- Define pass/fail criteria for relevance, citation availability, and source traceability.
- Run first dry evaluation and record known gaps.

### Day 7: Demo Readiness Review
- Verify end-to-end retrieval path from query -> authorities -> citation evidence.
- Publish implementation notes, open issues, and next-week priorities.
- Confirm readiness to move into execution phase with stable scope.

---

## In Scope

- Retrieval foundation for **Macau public judgments** and **Macau statutes**.
- Source inventory and ingestion strategy planning.
- Domain model and entity relationships for retrieval and citation.
- Day 1 acceptance criteria and evidence package.
- Architecture decisions that keep future domain expansion open.

---

## Out of Scope

- Agent orchestration implementation.
- Production UI and chat experience.
- Automated memo drafting quality optimization.
- Full-domain legal coverage in week 1.
- Any claim that the product scope is limited to labor law.

---

## First Demo Definition

A successful first demo shows a retrieval-centric flow:

1. Input one Macau legal question (natural language).
2. Return statutes and cases from official or documented sources.
3. Show ranked core/supporting authorities.
4. Show citation chunks linked back to source document and URL.
5. Output a short, structured summary with traceable evidence links.

No multi-agent routing is required for this first demo.

---

## Must-have Acceptance Criteria

- Scope statement is explicit: retrieval engine first, agents second.
- MVP scope explicitly includes Macau judgments + Macau statutes.
- Documentation clarifies cross-domain architecture (not labor-law-only).
- Source inventory includes risk and operational feasibility fields.
- Domain model covers case/statute/citation/source/ingestion tracking.
- Day 1 deliverables are reviewable without writing runtime feature code.

---

## Risks and Assumptions

### Risks
- Official sources may have unstable structure or anti-automation behavior.
- PDF-heavy sources may increase extraction complexity and OCR cost.
- Metadata inconsistency across sources may reduce matching quality.
- Early small datasets can bias retrieval tuning if treated as full scope.

### Assumptions
- Official Macau legal sources remain accessible for lawful public retrieval.
- Initial bilingual/parsing complexity is manageable with staged iteration.
- Retrieval quality can be improved incrementally through benchmark loops.
- Agent workflows can be added later without redesigning core retrieval entities.
