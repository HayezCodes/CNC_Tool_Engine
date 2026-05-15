# CNC Tool Engine Dataset Baseline

This folder contains a curated, normalized, catalog-backed dataset baseline for the CNC Tool Engine app.

## What is included
- Grade map with cross-brand baseline records
- Turning insert and holder families
- Grooving and threading families
- Solid and indexable drill families
- Solid endmill and indexable milling families
- Burnishing and workholding starter datasets

## What this is for
- Demoing the app to tool reps and internal stakeholders
- Powering recommendation filtering and future scoring logic
- Serving as a structured foundation for deeper SKU-level extraction later

## What this is not
- A full one-to-one digital clone of every supplier catalog
- A purchasing database with every order number populated

---

## Tooling Search Layer

`tool_data/tooling_search/` is a separate, source-linked exact-tool record layer.
It is intentionally kept apart from reviewed catalog-family guidance in
`tool_data/catalog_ingestion/reviewed/`.

### Folder roles

| Path | Role |
|------|------|
| `tooling_search/records/*.json` | Normalized exact-tool records (imported, not yet reviewed) |
| `tooling_search/records/reviewed/` | Batch-reviewed tooling records with reviewer metadata |
| `tooling_search/audit_reports/` | JSON audit reports from the audit workflow |
| `tooling_search/indexes/` | Reserved for future persisted search indexes |

### Current starter datasets

| Brand | Records | Categories |
|-------|---------|------------|
| Sandvik Coromant | 12 | Turning inserts, milling inserts, endmills, indexable drills, grooving, threading |
| Kennametal | 11 | Turning inserts, milling inserts, endmills, indexable drills, grooving, threading |
| Seco Tools | 10 | Turning inserts, milling inserts, endmills, indexable drills, grooving, threading |

All starter records carry:
- `verification_status: sample_family_level_not_catalog_verified`
- `cutting_data_status: not_imported`
- No feeds, speeds, or exact catalog dimensions

---

## Tooling Search Audit Workflow

Run the audit to check all records under `tooling_search/records/` for schema
compliance, source traceability, duplicate part numbers, and forbidden fields:

```
python tools/audit_tooling_search_records.py
```

The audit checks:
- Missing required schema fields
- Missing or empty `source_label` / `source_url`
- Invalid `verification_status` or `cutting_data_status`
- Duplicate `manufacturer_part_number` within the same brand
- Forbidden feed/speed fields (`sfm`, `rpm`, `feed`, `speed`, `ipr`, `ipm`, `fz`, `vc`)
- Invalid list-field types (`material_fit`, `operation_fit`, `geometry_tags`, `holder_compatibility`)
- Empty `material_fit` or `operation_fit` mappings

The audit report is written to:
`tool_data/tooling_search/audit_reports/tooling_search_audit_report.json`

---

## Tooling Search Review Workflow

Once records have been imported and the audit passes, promote them to reviewed
status with `tools/review_tooling_records.py`:

```
python tools/review_tooling_records.py \
    tool_data/tooling_search/records/sandvik_coromant_tooling_records.json \
    --brand-slug "sandvik_coromant" \
    --reviewer "Your Name" \
    --review-status reviewed_exact_tool_candidate \
    --review-notes "Cross-checked against 2025 catalog, family-level only."
```

Allowed review statuses:
- `reviewed_exact_tool_candidate` — record is ready for promotion to exact-tool search
- `reviewed_family_level_candidate` — record is family-level guidance only

The review tool:
- Rejects any records containing forbidden feed/speed fields
- Preserves all source references (`source_label`, `source_url`, `source_page_reference`)
- Forces `cutting_data_status = not_imported`
- Adds `reviewer`, `review_date`, and `review_notes` to every record
- Writes reviewed output to `tool_data/tooling_search/records/reviewed/`

Use `--dry-run` to validate without writing output.

---

## Scaling and Import Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| Foundation | Schema, search engine, sample records | Done |
| Audit workflow | `audit_tooling_search_records.py` | Done |
| Review workflow | `review_tooling_records.py` | Done |
| Starter imports | Sandvik Coromant, Kennametal, Seco Tools | Done |
| Bulk imports | Large brand datasets via `import_tooling_records.py` | Future |
| Catalog verification | Promote sample records to `verified_source_page_record` | Future |
| Indexing | Persist and serve search index from `indexes/` | Future |
| UI integration | Expose search and filters in the app interface | Future |

### Rules that must never change

- Do NOT import feeds, speeds, or cutting data into tooling search records.
- Do NOT invent dimensions, certified grades, or exact catalog numbers.
- Exact-tooling records must stay separate from reviewed family-level catalog records.
- Every record must carry `source_label`, `source_url`, and `verification_status`.
- Unverified records must use `verification_status: sample_family_level_not_catalog_verified`.
