# Tooling Adapter Architecture

## Purpose

The tooling adapter layer provides a safe, structured pipeline for ingesting machine-readable manufacturer tooling data (ISO 13399, GTC XML, and similar formats) into the Enterprise Tooling Search system.

Adapters normalize raw vendor data into the standard tooling search schema **without** importing cutting data, feeds, speeds, or unverified dimensions. All adapter output must pass through the existing audit and review workflow before records enter the live search index.

## Ingestion Path

```
Manufacturer Data Source
  (ISO 13399 XML, GTC ZIP, DIN 4000, CSV, ...)
        │
        ▼
  Adapter (tools/tooling_adapters/<format>_adapter.py)
    - Reads source file
    - Rejects records with forbidden feed/speed elements
    - Normalizes fields to SCHEMA_FIELDS
    - Forces dimensions = {}
    - Forces cutting_data_status = "not_imported"
    - Returns list[dict]
        │
        ▼
  Runner Script (tools/parse_<source>_sample.py)
    - Calls adapter.parse()
    - Runs adapter.validate_output() — checks schema compliance
    - Runs validate_import_rows() — existing importer validation
    - Checks for forbidden keys in output
    - Writes to tools/tooling_adapters/output/<name>.json
        │
        ▼
  Audit Workflow (tools/audit_tooling_search_records.py)
    - Checks all JSON files under tool_data/tooling_search/records/
    - Reports schema issues, missing required fields, invalid statuses,
      forbidden feed/speed fields, duplicates, invalid list types
    - Writes JSON audit report to tool_data/tooling_search/audit_reports/
        │
        ▼
  Review Workflow (tools/review_tooling_records.py)
    - Reviewer promotes adapter output records
    - Sets verification_status to reviewed_exact_tool_candidate or
      reviewed_family_level_candidate
    - Adds reviewer, review_date, review_notes
    - Writes to tool_data/tooling_search/records/reviewed/
        │
        ▼
  Live Search Index
    - grade_engine/tooling_search.py loads records/ (non-recursive)
    - Reviewed records under records/reviewed/ not in live index until
      promoted to records/ root by a human operator
```

## Directory Layout

```
tools/
  tooling_adapters/
    __init__.py                                   # namespace package marker
    base_adapter.py                               # shared contract, helpers, validation bridge
    gtc_iso13399_adapter.py                       # GTC / ISO 13399 XML adapter
    mitsubishi_materials_adapter.py               # Mitsubishi Materials JSON adapter
    samples/
      sample_gtc_iso13399.xml                     # synthetic test fixture (NOT manufacturer data)
      sample_mitsubishi_materials_structured.json # synthetic test fixture (NOT manufacturer data)
    output/
      .gitkeep                                    # output directory stub
      <name>_records.json                         # adapter output (staged, not yet in records/)

  parse_gtc_iso13399_sample.py          # runner: parse sample, validate, write output
  parse_mitsubishi_materials_sample.py  # runner: parse Mitsubishi sample, validate, write output
```

## Base Adapter (`base_adapter.py`)

Provides the shared contract all adapters must implement:

- **`field_contains_forbidden_term(field_name)`** — returns True if the field name contains any of `("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")` after normalization. Used to reject records containing feed/speed data at the element level.
- **`normalize_material_fit(values)`** — filters values to ISO material group codes (P, M, K, N, S, H) only.
- **`normalize_operation_fit(values)`** — lowercases and snake_cases operation strings.
- **`normalize_geometry_tags(values)`** — lowercases and snake_cases tag strings.
- **`normalize_holder_compatibility(values)`** — strips whitespace from holder strings.
- **`make_empty_record()`** — returns a dict with all 20 SCHEMA_FIELDS set to safe defaults (`""`, `[]`, `{}` as appropriate).
- **`validate_adapter_output(records)`** — checks all records for: complete SCHEMA_FIELDS, no forbidden keys, `cutting_data_status == "not_imported"`, valid `verification_status`, list fields are lists, dimensions is a dict.
- **`BaseToolingAdapter`** — abstract base class. Subclasses must implement `parse(source)` and call `validate_output(records)` before returning. Exposes `parse_errors` and `rejected_count`.

## GTC / ISO 13399 Adapter (`gtc_iso13399_adapter.py`)

Parses simplified GTC-style XML files into normalized tooling search records.

**GTC (Generic Tool Catalog)** is an XML+ZIP format co-developed by Sandvik Coromant, Kennametal, Iscar, and Siemens, built on top of ISO 13399. It is supported by Sandvik CoroPlus Tool Library and Siemens NX/Teamcenter.

Field mapping:

| XML Element | Schema Field | Notes |
|---|---|---|
| `ManufacturerName` (header) | `brand` | From `<CatalogHeader>` |
| `MPN` | `manufacturer_part_number` | |
| `ToolCategory` | `tool_category` | Mapped via `_TOOL_CATEGORY_MAP` |
| `Series` | `series` | |
| `FamilyName` | `family_name` | |
| `Designation` | `designation` | |
| `Grade` | `grade` | |
| `Chipbreaker` | `chipbreaker` | |
| `Coating` | `coating` | |
| `MaterialGroup` (repeated) | `material_fit` | Filtered to ISO codes |
| `Operation` (repeated) | `operation_fit` | Mapped via `_OPERATION_MAP` |
| `GeometryTag` (repeated) | `geometry_tags` | Normalized snake_case |
| `HolderCompatibility` | `holder_compatibility` | Comma-split to list |
| `CoolantCapability` | `coolant_capability` | Mapped via `_COOLANT_MAP` |
| `CatalogURL` (header) | `source_url` | |
| `CatalogLabel` (header) | `source_label` | |
| `SourcePageReference` | `source_page_reference` | |
| `Notes` | `notes` | |
| *(forced)* | `dimensions` | Always `{}` — never imported |
| *(forced)* | `cutting_data_status` | Always `"not_imported"` |
| *(forced)* | `verification_status` | Always `"sample_family_level_not_catalog_verified"` |

**Rejection policy:** If any `<ToolItem>` child element tag contains a forbidden feed/speed term (after normalization), the entire record is rejected before any field is read. Rejection notices appear in `parse_errors`; `rejected_count` is incremented.

## Mitsubishi Materials Adapter (`mitsubishi_materials_adapter.py`)

Parses Mitsubishi-style structured JSON tooling records into normalized tooling search records.

**Input format:** A JSON object with two top-level keys:
- `catalog_header` — `manufacturer`, `catalog_label`, `catalog_url`, optional `issue_date`
- `tool_records` — array of flat dicts with Mitsubishi-convention field names

Field mapping:

| JSON Key | Schema Field | Notes |
|---|---|---|
| `catalog_header.manufacturer` | `brand` | Defaults to `"Mitsubishi Materials Corporation"` |
| `part_number` | `manufacturer_part_number` | |
| `tool_type` | `tool_category` | Mapped via `_TOOL_CATEGORY_MAP` |
| `series` | `series` | |
| `family_name` | `family_name` | |
| `designation` | `designation` | |
| `grade` | `grade` | |
| `chipbreaker` | `chipbreaker` | |
| `coating` | `coating` | |
| `material_groups` (array) | `material_fit` | Filtered to ISO codes via `normalize_material_fit()` |
| `operations` (array) | `operation_fit` | Mapped via `_OPERATION_MAP` |
| `geometry_tags` (array) | `geometry_tags` | Normalized snake_case |
| `holder_compatibility` | `holder_compatibility` | Comma-split to list |
| `coolant` | `coolant_capability` | Mapped via `_COOLANT_MAP` |
| `catalog_header.catalog_label` | `source_label` | |
| `catalog_header.catalog_url` | `source_url` | |
| `source_page` | `source_page_reference` | |
| `notes` | `notes` | |
| *(forced)* | `dimensions` | Always `{}` — never imported |
| *(forced)* | `cutting_data_status` | Always `"not_imported"` |
| *(forced)* | `verification_status` | Always `"sample_family_level_not_catalog_verified"` |

**Rejection policy:** If any JSON key in a `tool_records` entry contains a forbidden feed/speed term (after normalization), the entire record is rejected. Rejection notices appear in `parse_errors`; `rejected_count` is incremented.

**`parse_mitsubishi_file(source)`** is the module-level convenience function. It instantiates the adapter, calls `parse()` and `validate_output()`, and returns a summary dict with `record_count`, `rejected_count`, `parse_errors`, `validation_errors`, and `records`.

Running the sample:

```bash
# Parse and write output JSON
python tools/parse_mitsubishi_materials_sample.py

# Dry run (validate only, no file written)
python tools/parse_mitsubishi_materials_sample.py --dry-run

# Custom output path
python tools/parse_mitsubishi_materials_sample.py --output path/to/custom.json
```

Output is written to `tools/tooling_adapters/output/mitsubishi_materials_sample_records.json`. Seven synthetic fixture records covering turning inserts, milling inserts, endmills, indexable drills, grooving inserts, and threading inserts. All marked as not manufacturer catalog data.

## What Is Never Imported

The adapter layer enforces these constraints unconditionally:

- **No feeds or speeds** — element tags containing `feed`, `speed`, `sfm`, `rpm`, `ipr`, `ipm`, `vc`, or `fz` cause record rejection.
- **No dimensions** — `dimensions` field is always `{}`. Physical catalog dimensions (diameter, length, IC, etc.) are not ingested.
- **No cutting data** — `cutting_data_status` is always `"not_imported"`.
- **No verification promotion** — `verification_status` defaults to `"sample_family_level_not_catalog_verified"`. Promotion to `reviewed_*` status is done only by a human reviewer via the review workflow.

## Adding a New Adapter

1. Create `tools/tooling_adapters/<format>_adapter.py`
2. Subclass `BaseToolingAdapter`
3. Implement `parse(source)`:
   - Read and parse the source file
   - For each record, call `field_contains_forbidden_term()` on all raw field names before mapping
   - Use `make_empty_record()` to start every record
   - Use the normalize helpers for list fields
   - Always leave `dimensions = {}` and `cutting_data_status = "not_imported"`
4. Create a runner script in `tools/parse_<format>_sample.py`
5. Add a synthetic fixture file in `tools/tooling_adapters/samples/`
6. Add tests in `tests/test_<format>_adapter.py`
7. Run `python -m compileall . && pytest` before committing
8. Output goes to `tools/tooling_adapters/output/` — not to `records/` directly

## Sample Fixtures

`tools/tooling_adapters/samples/sample_gtc_iso13399.xml` contains 5 synthetic GTC records clearly marked as test fixture data.

`tools/tooling_adapters/samples/sample_mitsubishi_materials_structured.json` contains 7 synthetic Mitsubishi-format records clearly marked as test fixture data.

All fixture records use fictional MPNs, grades, and catalog references. They must not be used for purchasing, machining, or catalog reference.

Running the sample:

```bash
# Parse and write output JSON
python tools/parse_gtc_iso13399_sample.py

# Dry run (validate only, no file written)
python tools/parse_gtc_iso13399_sample.py --dry-run

# Custom output path
python tools/parse_gtc_iso13399_sample.py --output path/to/custom.json
```

Output is written to `tools/tooling_adapters/output/sample_gtc_iso13399_records.json`. This file is staged output — it must go through `tools/audit_tooling_search_records.py` and `tools/review_tooling_records.py` before any records are promoted to `tool_data/tooling_search/records/`.
