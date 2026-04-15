# MO_cocounsel

Macau CoCounsel / Macau Legal Copilot

A Macau-focused legal research and document analysis system inspired by CoCounsel, designed for legal retrieval, document review, drafting support, and future agentic legal workflows.

---

## Overview

**MO_cocounsel** is a Macau legal AI project that aims to build a **Macau version of CoCounsel**.

Its long-term goal is not just to answer legal questions, but to provide a structured legal workbench for:

- legal research
- document review
- contract / notice analysis
- case and statute comparison
- memo and checklist generation
- workflow orchestration through legal agents

The core principle of this project is:

> **First build the legal retrieval engine, then build the agents.**

Without strong retrieval, citation grounding, and evidence binding, higher-level agents are only a thin interface over unstable outputs.

---

## Product Positioning

MO_cocounsel is positioned as a:

- **Macau Legal Copilot**
- **Macau CoCounsel**
- **Macau legal research and review assistant**

It is designed primarily for:

- legal research
- issue spotting
- document analysis
- structured legal outputs
- future multi-step legal workflows

---

## Core Design Principle

This project is built around one foundational layer:

# **Macau Legal Retrieval Engine**

This engine is the shared legal intelligence layer used by all upper-level features and agents.

It must support:

- Macau statute retrieval
- Macau public case law retrieval
- statute-case linkage
- citation and evidence binding
- structured research summaries
- multi-step retrieval for deep research
- source-aware and court-aware search modes

---

# Core Capabilities

## A. Legal Research

### 1. Natural-language legal search
Users can input ordinary legal questions in natural language, and the system will retrieve:

- Macau statutes
- Macau case law
- explanatory materials where available

Example queries:
- “僱主拖糧，員工可否即時解除合同？”
- “澳門解僱通知未寫明理由，法律上有何風險？”
- “買賣合同中的違約金條款是否可能過高？”
- “交通事故後可否同時主張哪些損害賠償？”

### 2. Deep Research / multi-step legal research
The system does not stop at one retrieval step. It can:

- decompose a complex legal question
- perform multi-step search
- refine sub-issues
- aggregate legal findings into a structured result

### 3. Issue decomposition
A complex legal question can be broken into:

- main issue
- sub-issues
- procedural questions
- remedies / compensation
- limitation / burden of proof / evidence gaps

### 4. Case-oriented research summary
The output is not just a paragraph answer. It should include:

- conclusion summary
- core cases
- supporting cases
- relevant reasoning snippets
- adverse / limiting cases where relevant

### 5. Statute-oriented research summary
The system can produce a statute-first analysis, including:

- applicable provisions
- statutory elements
- how statutes and cases support each other

### 6. Research mode control
Users can choose the research mode:

- statute-only
- case-only
- hybrid analysis

### 7. Court / source-specific search
Users can control search scope, such as:

- only Court of Final Appeal
- only Intermediate Court
- only certain subject areas
- only specific sources

### 8. Timeline / legal evolution search
The system can track how a legal issue evolves across years and cases.

### 9. Adverse case retrieval
The system should not only find favorable authorities, but also:

- adverse cases
- restrictive cases
- contrary positions
- exceptions and limitations

---

## B. Document Review / Analysis

### 1. Upload-and-analyze legal documents
Supported formats may include:

- PDF
- DOCX
- images
- scanned documents

The system analyzes the content and links it to Macau law and cases.

### 2. Contract review
The system can:

- identify clauses
- highlight legal risks
- detect missing terms
- mark sections requiring human review

### 3. Clause summarization
Long legal clauses can be rewritten into plain language.

### 4. Contract data extraction
The system can extract structured information such as:

- parties
- term
- termination
- breach
- confidentiality
- indemnity
- governing law / jurisdiction

### 5. Document comparison
Compare two versions of a document and identify:

- clause changes
- added / removed terms
- changed risk profile

### 6. Benchmark against standard
Compare a document against a standard template to identify:

- missing clauses
- extra clauses
- deviations from standard practice

### 7. Batch review
Support reviewing multiple documents together, such as:

- contracts
- notices
- case materials
- legal correspondence

### 8. Case material organization
From a bundle of case materials, the system can extract:

- parties
- timeline
- facts
- issues
- evidence
- likely legal questions

### 9. Legal sufficiency checks
For example:

- whether a dismissal notice states sufficient reasons
- whether required elements are missing
- whether procedural defects may exist

---

## C. Drafting / Work Product Generation

### 1. Research memo generation
Generate a structured memo including:

- issue
- rule
- authorities
- analysis
- risks
- conclusion

### 2. Case brief generation
Produce a case brief with:

- case number
- facts
- issue
- reasoning
- holding
- usable citations

### 3. Plain-language rewrite
Translate legal analysis into plain language for non-lawyers.

### 4. Client-style explanation draft
Generate a non-formal explanation draft with clear caution that it is not formal legal advice.

### 5. Pre-litigation issue checklist
Based on facts and materials, generate a checklist of:

- missing facts
- missing evidence
- unresolved legal questions
- issues requiring confirmation

### 6. Risk checklist
Output risk checklists for:

- contracts
- labor notices
- procedural actions
- legal arrangements

### 7. Comparison tables
Generate structured tables such as:

- contract A vs contract B
- statute vs case comparison
- favorable vs adverse authority comparison

### 8. Draft-first legal work product
Potential outputs include:

- legal research draft
- complaint draft
- internal legal analysis draft
- notice draft

---

## D. Workflow / Agent Capabilities

The project also plans future agentic workflows.

### 1. Research Agent
Responsible for:

- multi-step research
- sub-issue search
- result consolidation

### 2. Citation Agent
Responsible for:

- linking conclusions to source chunks
- generating citation cards
- preserving grounding

### 3. Document Analysis Agent
Responsible for:

- extracting facts / clauses / issues from uploaded documents
- turning them into legal research queries

### 4. Comparison Agent
Responsible for:

- comparing versions
- identifying legal significance of changes
- surfacing risk delta

### 5. Memo Drafting Agent
Responsible for transforming research outputs into work products.

### 6. Issue Spotting Agent
Responsible for identifying legal issues from long factual narratives.

### 7. Evidence Gap Agent
Responsible for identifying:

- missing facts
- missing evidence
- unsupported conclusions

### 8. Task Planner / Workflow Orchestrator
Responsible for:

- classifying task type
- deciding which tools / agents to call
- determining retrieval order
- stopping or continuing the research loop

---

# System Architecture

## Global Architecture

```text
Frontend UI
    |
Backend API (FastAPI)
    |
Task Planner / Workflow Orchestrator
    |
+-----------------------------+
|  Legal Retrieval Layer      |
|  - Query Normalizer         |
|  - Issue Decomposer         |
|  - Search Router            |
|  - Hybrid Retriever         |
|  - Re-ranker                |
|  - Citation Binder          |
+-----------------------------+
    |
+-----------------------------+
|  Knowledge Layer            |
|  - Macau statutes DB        |
|  - Macau cases DB           |
|  - Metadata DB              |
|  - Vector index             |
|  - Keyword/full-text index  |
+-----------------------------+
    |
+-----------------------------+
|  Agent Layer                |
|  - Research Agent           |
|  - Citation Agent           |
|  - Document Analysis Agent  |
|  - Comparison Agent         |
|  - Memo Drafting Agent      |
|  - Issue Spotting Agent     |
|  - Evidence Gap Agent       |
+-----------------------------+
    |
Output Layer
- Answer
- Cases
- Statutes
- Citations
- Memo
- Checklist
- Compare Table
```

---

## Retrieval Layer Responsibilities

The retrieval layer is the foundation of the entire system.

It is responsible for:

- query normalization
- issue decomposition
- statute retrieval
- case retrieval
- statute-case linkage
- ranking core / supporting / adverse authorities
- citation binding
- structured evidence for upper-layer agents

---

## Core Retrieval Modules

### 1. Query Normalizer
Converts ordinary user language into legal retrieval language.

Important note:
The README examples under this section are **illustrative only**. They are not hardcoded constraints and do not imply that the system is limited to labor-law issues such as wage disputes. The same normalization layer should support many legal domains and many issue families.

Example:
- 拖糧 / 欠薪 / 不出糧 / 延遲支付工資
- can be normalized into one issue representation in a labor-law context

Responsibilities:
- legal synonym normalization
- issue code mapping
- jurisdiction-specific term mapping
- domain-aware query rewriting

### 2. Issue Decomposer
Breaks one complex legal problem into sub-issues.

Example:
- main issue
- procedural issue
- remedy issue
- evidence issue
- limitation issue

### 3. Search Router
Chooses search strategy dynamically:

- statute-only
- case-only
- hybrid
- specific court
- timeline
- adverse-case search

### 4. Hybrid Retriever
Combines:

- keyword / full-text retrieval
- vector retrieval
- metadata filtering
- issue-aware retrieval

### 5. Re-ranker
Re-ranks candidate authorities using factors such as:

- relevance to main issue
- relevance to sub-issues
- court level
- recency
- procedural importance
- compensation / remedy relevance
- burden-of-proof relevance

### 6. Citation Binder
Binds each conclusion to:

- case number
- article number
- source chunk
- snippet
- source URL

This is one of the most important components in the project.

---

## Issue Taxonomy and Legal Term Map

MO_cocounsel should not depend on a single fixed list of hardcoded legal phrases. Instead, it should use an extensible **issue taxonomy** and **alias map**.

This means the system should support:

- issue taxonomy
- issue aliases
- Macau legal term map
- procedural vs substantive issue map
- remedy taxonomy

Example taxonomy entry:

```json
{
  "issue_code": "late_wage_payment",
  "aliases": [
    "拖糧",
    "欠薪",
    "不出糧",
    "延遲支付工資",
    "未按時支付工資"
  ],
  "related_issues": [
    "employee_termination_with_just_cause",
    "compensation_claim",
    "burden_of_proof",
    "interest_claim"
  ]
}
```

This is only one example issue family. The same structure should later cover many other categories, such as:

- dismissal validity
- contract breach
- damages
- prescription / limitation
- procedural defects
- tenancy disputes
- tort liability
- criminal procedure issues

The point of writing this in the README is to document an **extensible architecture**, not a closed rule list.

---

## Authority Roles

Retrieved authorities should not be treated as one flat list. MO_cocounsel should distinguish between different legal roles, such as:

- core authority
- supporting authority
- adverse authority
- limiting authority
- procedural authority
- remedy authority

This helps the system produce better research summaries, compare tables, and memo outputs.

---

## Retrieval System Design Notes

The retrieval engine is not designed in a vacuum. Its design should be informed by benchmark testing, reverse engineering of working legal retrieval tools, and repeated query evaluation.

A production-like Macau legal retrieval system likely behaves as:

```text
User legal question
-> query normalization
-> issue tagging / issue decomposition
-> retrieve large candidate set of cases
-> hybrid ranking (keyword + semantic + metadata)
-> select representative authorities
-> generate structured legal summary
-> bind summary points to cited authorities
-> return expandable case cards / snippets
```

This suggests that the retrieval system is not just a search box, but a layered legal intelligence pipeline.

### Observed strengths to preserve

- not pure keyword search
- likely hybrid retrieval behavior
- recurring representative precedent anchors
- structured, template-guided research summaries

### Observed weaknesses to improve

- synonym stability can drift
- mixed issues can blur together
- citation grounding may not be granular enough
- recall may be high while precision is uneven

MO_cocounsel should explicitly improve these areas through stronger normalization, finer issue decomposition, stricter evidence binding, and better re-ranking.

---

## Recommended Retrieval Output Schema

The retrieval engine should not return only raw search hits. It should return a structured legal retrieval package:

```json
{
  "raw_query": "...",
  "normalized_query": "...",
  "research_mode": "hybrid",
  "main_issue": "...",
  "sub_issues": ["...", "..."],
  "core_cases": [
    {
      "case_number": "...",
      "court_level": "...",
      "decision_date": "...",
      "reasoning_snippet": "...",
      "source_url": "...",
      "score": 0.92
    }
  ],
  "supporting_cases": [],
  "adverse_cases": [],
  "applicable_statutes": [],
  "structured_summary": [
    {
      "point_title": "...",
      "point_text": "...",
      "citations": ["..."]
    }
  ],
  "evidence_gaps": [],
  "caution_notes": []
}
```

---

# Knowledge Layer

## Initial Data Sources

Priority order:

1. **Macau public judgments / case law**
2. **Macau statutes / regulations**
3. **Official explanatory materials and public legal documents**
4. **Internal benchmark notes / manually curated issue maps**

---

## Suggested Data Pipeline

```text
Source discovery
-> crawler / downloader
-> raw html/pdf storage
-> parser
-> metadata extraction
-> structured database
-> chunking
-> embeddings
-> search indexes
```

---

## Suggested Core Tables

### cases
- id
- case_number
- court_name
- court_level
- decision_date
- case_type
- title
- source_url
- language
- full_text
- summary_text
- reasoning_text
- holding_text
- issue_tags
- cited_statutes
- raw_html_path
- raw_pdf_path
- created_at
- updated_at

### case_chunks
- id
- case_id
- chunk_index
- section_type
- chunk_text
- token_count
- embedding_vector
- bm25_text
- citation_anchor

### statutes
- id
- law_name
- law_code
- article_number
- title
- article_text
- language
- effective_date
- repealed_date
- source_url
- created_at
- updated_at

### statute_chunks
- id
- statute_id
- chunk_index
- chunk_text
- embedding_vector
- bm25_text

---

# Recommended Development Order

## Phase 1 — Legal Retrieval Engine MVP
Build the minimum viable retrieval system first.

Must-have:
- case and statute ingestion
- keyword search
- vector search
- hybrid retrieval
- citation-ready result schema
- structured research summary

Output target:
- issue breakdown
- core cases
- supporting cases
- applicable statutes
- grounded legal summary

## Phase 2 — Document Analysis Layer
Build upload and analysis capability.

Must-have:
- PDF / DOCX / image parsing
- clause extraction
- issue spotting
- document-to-query generation
- retrieval linkage

## Phase 3 — Work Product Layer
Turn research into usable outputs.

Must-have:
- research memo
- case brief
- plain-language rewrite
- risk checklist
- comparison table

## Phase 4 — Workflow / Agent Orchestration
Add multi-step automation.

Must-have:
- task planner
- agent routing
- multi-step retrieval loops
- evidence gap detection
- batch review flow

---

# Suggested Tech Stack

## Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- httpx

## Database / Search
- PostgreSQL
- pgvector
- PostgreSQL full-text search

## Parsing / Ingestion
- Playwright
- BeautifulSoup / lxml
- PyMuPDF / pdfplumber
- python-docx
- OCR fallback when necessary

## Frontend
- Vue 3 or Next.js
- Tailwind CSS
- Pinia / TanStack Query
- PDF viewer
- diff viewer
- citation viewer

## Infra
- Docker Compose
- local-first development
- local object storage / MinIO for raw files

---

# Proposed API Design

## Research
- `POST /research/query`
- `POST /research/deep-query`
- `POST /research/similar-cases`
- `POST /research/timeline`
- `POST /research/adverse-cases`

## Documents
- `POST /documents/upload`
- `POST /documents/analyze`
- `POST /documents/compare`
- `POST /documents/batch-review`

## Drafting / Work Products
- `POST /drafts/memo`
- `POST /drafts/case-brief`
- `POST /drafts/plain-language`
- `POST /drafts/checklist`

## Internal Tools
- `POST /internal/normalize-query`
- `POST /internal/decompose-issues`
- `POST /internal/retrieve`
- `POST /internal/rerank`
- `POST /internal/bind-citations`

---

# MVP Scope

The first real MVP should stay narrow while remaining product-accurate.

## Recommended MVP
Focus on:

- Macau public judgments
- Macau statutes (laws and regulations)
- hybrid retrieval
- statute-case linkage
- citation cards
- structured research summary

Clarifications:

- MVP first focuses on Macau public judgments and Macau statutes.
- The architecture is cross-domain and not labor-law-limited.
- Early iterations may use a small subset of cases for faster retrieval testing, but that subset does not define product scope.
- Day 1 delivery is retrieval foundation only; it does **not** include agent orchestration implementation.
- Direction remains: **Macau Legal Retrieval Engine first, agents second.**

## MVP Input
- natural language legal question
- long factual narrative

## MVP Output
- issue decomposition
- 3–5 core cases
- 3–5 supporting cases
- applicable statutes
- structured summary
- citation-backed findings

---

# Evaluation Plan

To avoid building an impressive but unreliable demo, evaluation is required.

Recommended evaluation setup:

- 50 benchmark legal queries
- expected core cases
- expected statutes
- issue coverage rubric
- citation grounding rubric
- hallucination checks
- regression evaluation after each major update

## Search Evaluation Dimensions

The retrieval engine should be evaluated across dimensions such as:

- query normalization stability
- issue decomposition quality
- core authority precision
- adverse authority recall
- citation grounding quality
- evidence-role labeling accuracy
- source-mode compliance
- long-fact narrative issue extraction quality

---

# Common Failure Modes

This project should avoid:

- building multi-agent orchestration too early
- building chat UI too early
- failing to preserve raw source documents
- relying only on vector search
- skipping metadata filtering
- skipping benchmark evaluation
- skipping citation binding
- trying to cover all legal domains too early
- not building issue taxonomy

## Retrieval-specific observed failure patterns

- paraphrase drift
- remedy-dominant drift
- procedure/substance blending
- over-broad retrieval
- insufficient adverse-case surfacing
- citation not granular enough
- anchor case over-dependence
- weak exact-passage grounding

---

# Suggested Repo Structure

```text
MO_cocounsel/
├─ README.md
├─ .env.example
├─ docker-compose.yml
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core/
│  │  ├─ api/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  │  ├─ retrieval/
│  │  │  ├─ research/
│  │  │  ├─ documents/
│  │  │  ├─ drafting/
│  │  │  └─ agents/
│  │  ├─ db/
│  │  └─ utils/
│  ├─ alembic/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  ├─ public/
│  └─ package.json
├─ crawler/
│  ├─ source_discovery/
│  ├─ downloaders/
│  ├─ parsers/
│  └─ logs/
├─ data/
│  ├─ raw/
│  ├─ parsed/
│  ├─ cleaned/
│  └─ indexed/
├─ scripts/
├─ tests/
└─ docs/
```

---

# Current Project Status

At the moment, this repository is at the project-definition stage. The immediate next step is to establish the **Macau Legal Retrieval Engine** as the foundation before implementing higher-level agents or advanced workflows.

---

# Roadmap

## Near-term
- initialize backend and database
- design schema for cases and statutes
- build small-scale ingestion pipeline
- test on 100–300 Macau judgments
- implement hybrid retrieval
- implement citation-ready output schema

## Mid-term
- add document upload and analysis
- add memo generation
- add comparison workflows
- add risk checklists

## Long-term
- add orchestration layer
- add multi-agent workflows
- add batch review
- add legal research workspace UI

---

# Vision

MO_cocounsel is not intended to be only a chatbot.

The long-term goal is to build a **Macau legal workbench** with:

- grounded legal retrieval
- evidence-linked outputs
- structured legal reasoning support
- document intelligence
- reusable legal workflows

The foundation of everything is:

> **Macau Legal Retrieval Engine first. Agents second.**
