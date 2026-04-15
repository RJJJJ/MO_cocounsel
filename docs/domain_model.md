# Domain Model (MVP Retrieval Foundation)

This document defines retrieval-first entities for Day 1 planning.

---

## 1) case

### Purpose
Represent one Macau public judgment as a canonical retrieval unit with stable identity and legal metadata.

### Key Fields
- `case_id` (UUID, internal primary key)
- `source_doc_id` (FK -> source_document)
- `case_number` (string, normalized)
- `court_name` (string)
- `court_level` (enum: final/intermediate/first-instance/other)
- `decision_date` (date)
- `case_type` (string)
- `title` (string)
- `language` (enum: zh/pt/other)
- `summary_text` (text, optional)
- `full_text` (text)
- `status` (enum: active/superseded/unknown)

### Relations
- One `case` belongs to one `source_document`.
- One `case` has many `citation_chunk` rows.
- One `case` can link to many `issue_taxonomy` tags.

### Why It Exists in MVP
Retrieval cannot rank case authorities or expose traceable evidence without a normalized case entity.

---

## 2) statute

### Purpose
Represent Macau legal provisions (law/regulation/article) as retrieval-ready and citation-ready units.

### Key Fields
- `statute_id` (UUID)
- `source_doc_id` (FK -> source_document)
- `law_name` (string)
- `law_code` (string, optional)
- `article_number` (string)
- `title` (string, optional)
- `article_text` (text)
- `effective_date` (date, optional)
- `repealed_date` (date, optional)
- `language` (enum: zh/pt/other)

### Relations
- One `statute` belongs to one `source_document`.
- One `statute` has many `citation_chunk` rows.
- One `statute` can be linked from many `case` records via citation extraction.

### Why It Exists in MVP
The MVP requires statute-case linkage and statute-first retrieval views, which depend on a canonical statute entity.

---

## 3) citation_chunk

### Purpose
Store granular passages used for ranking and evidence binding in retrieval responses.

### Key Fields
- `chunk_id` (UUID)
- `entity_type` (enum: case/statute)
- `entity_id` (UUID; FK to case or statute depending on `entity_type`)
- `chunk_index` (integer)
- `section_type` (string; e.g., facts/reasoning/holding/article)
- `chunk_text` (text)
- `token_count` (integer)
- `bm25_text` (text/searchable)
- `embedding_vector` (vector, optional at Day 1)
- `citation_anchor` (string; stable pointer for UI/API)

### Relations
- Many `citation_chunk` rows map to one `case` or one `statute`.
- Retrieval output references `citation_chunk` for evidence links.

### Why It Exists in MVP
Without chunk-level evidence, outputs cannot provide trustworthy citation grounding.

---

## 4) issue_taxonomy

### Purpose
Define extensible legal issue labels, aliases, and hierarchy for query normalization and decomposition.

### Key Fields
- `issue_code` (string, unique)
- `display_name` (string)
- `domain` (string; e.g., contract, labor, tort, procedure)
- `aliases` (json array)
- `parent_issue_code` (string, optional)
- `description` (text)
- `status` (enum: active/deprecated/draft)

### Relations
- Many-to-many between `issue_taxonomy` and `case`.
- Many-to-many between `issue_taxonomy` and `statute`.
- Query normalizer consumes `issue_taxonomy` as controlled vocabulary.

### Why It Exists in MVP
Prevents brittle hardcoded term handling and keeps architecture cross-domain from Day 1.

---

## 5) source_document

### Purpose
Track raw legal artifacts exactly as fetched so every parsed entity remains source-traceable.

### Key Fields
- `source_doc_id` (UUID)
- `source_name` (string)
- `source_url` (string)
- `base_url` (string)
- `document_type` (enum: case_pdf/case_html/statute_pdf/statute_html/other)
- `raw_storage_path` (string)
- `content_hash` (string)
- `fetched_at` (timestamp)
- `http_status` (integer)
- `language_hint` (string, optional)

### Relations
- One `source_document` can produce one or more `case` or `statute` records.
- One `source_document` belongs to one `ingestion_job` execution context.

### Why It Exists in MVP
Evidence binding requires auditability back to raw source files and URLs.

---

## 6) ingestion_job

### Purpose
Record each ingestion run for observability, retry control, and data quality accountability.

### Key Fields
- `job_id` (UUID)
- `job_type` (enum: discovery/fetch/parse/normalize/chunk/index)
- `source_name` (string)
- `started_at` (timestamp)
- `finished_at` (timestamp, optional)
- `status` (enum: running/success/partial_failed/failed)
- `input_count` (integer)
- `success_count` (integer)
- `failure_count` (integer)
- `error_summary` (text/json)

### Relations
- One `ingestion_job` can create many `source_document` records.
- Downstream entities (`case`, `statute`, `citation_chunk`) are traceable to originating job ID via lineage metadata.

### Why It Exists in MVP
MVP reliability depends on repeatable ingestion and fast diagnosis of parser/source failures.
