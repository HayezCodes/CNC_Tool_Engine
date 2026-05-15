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
    guhring_adapter.py                            # Guhring KG JSON adapter
    iscar_adapter.py                              # Iscar Ltd. JSON adapter
    samples/
      sample_gtc_iso13399.xml                     # synthetic test fixture (NOT manufacturer data)
      sample_mitsubishi_materials_structured.json # synthetic test fixture (NOT manufacturer data)
      sample_guhring_structured.json              # synthetic test fixture (NOT manufacturer data)
      sample_iscar_structured.json                # synthetic test fixture (NOT manufacturer data)
    output/
      .gitkeep                                    # output directory stub
      <name>_records.json                         # adapter output (staged, not yet in records/)

  parse_gtc_iso13399_sample.py          # runner: parse sample, validate, write output
  parse_mitsubishi_materials_sample.py  # runner: parse Mitsubishi sample, validate, write output
  parse_guhring_sample.py               # runner: parse Guhring sample, validate, write output
  parse_iscar_sample.py                 # runner: parse Iscar sample, validate, write output
  import_mitsubishi_adapter_output.py   # importer: adapter output → records/
  import_guhring_adapter_output.py      # importer: adapter output → records/
  import_iscar_adapter_output.py        # importer: adapter output → records/
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

## Guhring Adapter (`guhring_adapter.py`)

Parses Guhring-style structured JSON tooling records into normalized tooling search records. Guhring manufactures drills, taps, thread mills, reamers, countersinks, endmills, and step drills — tool categories not covered by insert-focused brands. The adapter uses the same JSON format as the Mitsubishi adapter (`catalog_header` + `tool_records` array) and the same field mapping conventions.

**New tool categories introduced:**

| tool_type value | schema tool_category |
|---|---|
| `SolidCarbideDrill`, `HSSCobaltDrill`, `HSSEDrill` | `drill` |
| `MachineTap`, `SpiralTap`, `FormTap` | `tap` |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` |
| `Reamer`, `SolidCarbideReamer` | `reamer` |
| `Countersink`, `ChamferTool` | `countersink` |
| `StepDrill`, `CombinationDrill` | `step_drill` |

**New operations introduced:**

| Input string | schema operation |
|---|---|
| `Tapping`, `ThroughHoleTapping`, `BlindHoleTapping` | `tapping`, `through_hole_tapping`, `blind_hole_tapping` |
| `ThreadMilling`, `ExternalThreadMilling`, `InternalThreadMilling` | `thread_milling`, `external_thread_milling`, `internal_thread_milling` |
| `Reaming`, `FinishReaming`, `PrecisionReaming` | `reaming`, `finish_reaming`, `precision_reaming` |
| `Countersinking`, `Chamfering`, `Deburring` | `countersinking`, `chamfering`, `deburring` |
| `StepDrilling`, `PilotDrilling` | `step_drilling`, `pilot_drilling` |

**Field mapping:** identical to the Mitsubishi Materials adapter — `part_number → manufacturer_part_number`, `tool_type → tool_category`, `material_groups → material_fit`, `operations → operation_fit`, `geometry_tags → geometry_tags`, `holder_compatibility → holder_compatibility`, `coolant → coolant_capability`. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_guhring_sample.py
python tools/parse_guhring_sample.py --dry-run
python tools/import_guhring_adapter_output.py
python tools/import_guhring_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/guhring_sample_records.json` (8 synthetic fixture records). Imported records go to `tool_data/tooling_search/records/guhring_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/guhring_reviewed_tools.json`.

## Iscar Adapter (`iscar_adapter.py`)

Parses Iscar-style structured JSON tooling records into normalized tooling search records. Iscar specializes in indexable tooling across the full range of turning, milling, drilling, grooving, and threading operations.

**Indexable tooling normalization notes:**

Iscar uses `chip_former` as the field name for the insert's chipbreaker geometry code (e.g., F3P, NF, GF). The adapter maps `chip_former → chipbreaker` transparently. If both `chip_former` and `chipbreaker` keys appear in the source record, `chip_former` takes precedence.

Boring bars in Iscar's system are toolholders that accept indexable inserts. They are recorded as `tool_category = "boring_bar"` to preserve that distinction from the insert itself — the toolholder and insert are separate records in a real catalog.

SUMOCHAM indexable drills use a replaceable tip system. The record represents the tip/platform, not the assembled body-plus-tip combination. Physical dimensions (body diameter, flute length, etc.) are excluded — `dimensions = {}` as always.

**High-feed milling insert normalization:**

Iscar high-feed milling inserts (HELI-FEED, Hi-QuadF, and similar) have their own `tool_type = "HighFeedMillingInsert"` which maps to `tool_category = "high_feed_insert"`. This distinguishes them from general milling inserts in search and filter workflows — operators can filter specifically for high-feed tooling without being mixed with general face milling inserts.

High-feed inserts typically operate at small depths of cut (ap ≤ 2mm) and high table feed rates by design. No feed or speed data is imported; the `high_feed_insert` category is purely a geometry/application classification.

**Tool category mapping (Iscar-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | |
| `MillingInsert`, `FaceMillingInsert`, `HelimillInsert` | `milling_insert` | |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | Distinct from milling_insert |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | SUMOCHAM tips |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | |
| `ThreadingInsert` | `threading_insert` | |
| `BoringBar`, `BoringToolholder` | `boring_bar` | Toolholder, not insert |

**New operations introduced:**

| Input string | schema operation |
|---|---|
| `HighFeedMilling` | `high_feed_milling` |
| `CircularGrooving` | `circular_grooving` |
| `LightTurning`, `HeavyTurning` | `light_turning`, `heavy_turning` |
| `Plunging` | `plunge_milling` |

Running the sample:

```bash
python tools/parse_iscar_sample.py
python tools/parse_iscar_sample.py --dry-run
python tools/import_iscar_adapter_output.py
python tools/import_iscar_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/iscar_sample_records.json` (8 synthetic fixture records: 2 turning inserts, 1 milling insert, 1 high-feed insert, 1 indexable drill, 1 grooving insert, 1 threading insert, 1 boring bar). Imported records go to `tool_data/tooling_search/records/iscar_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/iscar_reviewed_tools.json`.

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
