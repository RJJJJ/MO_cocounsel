# Day 21 Acceptance - Chunking Prep Layer

## Today objective
Build a chunking preparation layer that transforms raw Macau court corpus records into normalized, chunk-ready JSONL records for downstream retrieval work, without embedding, indexing, or database integration.

## Deliverables
- `crawler/prep/build_chunking_prep_layer.py`
- `crawler/prep/chunking_prep_layer_spec.md`
- `data/corpus/prepared/macau_court_cases/chunks.jsonl`
- `data/corpus/prepared/macau_court_cases/chunking_prep_report.txt`

## Acceptance checklist
- [ ] Script reads `data/corpus/raw/macau_court_cases/manifest.jsonl`.
- [ ] For each manifest row, script loads corresponding `metadata.json` and `full_text.txt`.
- [ ] Text cleaning is lightweight and preserves legal content.
- [ ] Chunking uses paragraph-aware splitting with fixed-size fallback.
- [ ] Each chunk has stable `chunk_id` and `chunk_index`.
- [ ] Output `chunks.jsonl` contains required schema fields.
- [ ] Output report includes required aggregate stats.
- [ ] Terminal output prints required summary stats.
- [ ] No embedding/indexing/database logic exists in this day.

## Evidence developer must provide
1. Command used to run chunking prep script.
2. Terminal summary output showing:
   - total corpus records read,
   - total chunk records written,
   - average chunks per case,
   - zh chunks count,
   - pt chunks count,
   - success flag.
3. File paths and existence proof for generated artifacts:
   - `chunks.jsonl`
   - `chunking_prep_report.txt`
4. Short note confirming no embedding/indexing/database integration was added.
