# CNC Tool Engine

`CNC Tool Engine` is a Streamlit-based shop-support recommendation app for common CNC tooling decisions. It gives operators and programmers a quick starting point for material-group-driven guidance, tool family selection, and grade behavior without rewriting catalog data or replacing supplier documentation.

## What This App Does

The app helps generate practical starting-point recommendations across these current modules:

- Turning
- Drilling
- Endmill
- Face Mill
- Grooving
- Threading
- Burnishing
- Workholding
- Catalog Explorer

Under the hood, the app uses the modular `grade_engine/` package for grade behavior resolution and `tool_data/` JSON files for catalog-style reference data.

## Brand Intelligence Layer

The brand intelligence layer provides family-level tooling guidance for practical brand and tool-family selection by operation, ISO material group, and shop priority. It is designed to help programmers choose likely tooling families to investigate.

- Brand Intelligence: broad brand strengths, shop-use notes, source status, and recommended engine use.
- Endmill Families: endmill-only family guidance for general milling, dynamic/adaptive milling, value tooling, and specialty cutters.
- Insert/Grade Families: broad insert brand behavior tags for production turning, toughness, wear-resistance, chipbreaker direction, and general insert use.
- Problem Solver: converts common shop problems like chatter, poor finish, short tool life, small-bore access, value sourcing, dynamic milling, specialty features, and production turning into practical recommendation directions.
- Tool Lookup Integration: search terms that match known brands, operations, or tooling families can show a supplemental family-level Brand Intelligence panel below the normal lookup results.

This layer does not replace manufacturer catalogs, does not provide certified speeds/feeds, and does not claim exact catalog numbers, dimensions, grade equivalency, or manufacturer-approved cutting data.

## Catalog Ingestion Pipeline

The catalog ingestion pipeline is a staged foundation for future manufacturer tooling data work. It uses official manufacturer catalog/resource pages first, keeps staged records untrusted until reviewed, and does not import exact feeds/speeds into staged data yet.

First staged manufacturer data: Helical Solutions endmill family records.

Staged records live separately from production recommendation data. Reviewed records can later feed the Brand Intelligence layer only after source citation and shop-safe validation.

Reviewed catalog records are still family-level unless cutting data is separately validated.

Reviewed Catalog Families are display/reference only and are not yet used in recommendation scoring.

## Enterprise Tooling Search Foundation

The enterprise tooling search foundation is a new, separate backend layer for future exact-tooling search and indexing work.

- It is separate from the current recommendation logic and does not replace recommendation scoring.
- It stores exact-tool-style records under `tool_data/tooling_search/` while reviewed family guidance remains separate.
- It currently uses only a small, conservative sample record set to establish schema, search behavior, filtering, and match explanations.
- A bulk CSV/JSON importer foundation now exists for dry-run validation and normalization before records are written.
- Speeds and feeds are not imported in this phase.
- Records must stay source-linked and explicitly verification-marked.

## Manufacturer Adapter Pipeline

A structured adapter pipeline now exists for ingesting machine-readable manufacturer tooling data (ISO 13399, GTC XML, structured JSON, and similar formats) into the Enterprise Tooling Search system.

### Mitsubishi Materials Adapter Pilot

A Mitsubishi Materials JSON adapter has been built and run through the complete import/audit/review/search pipeline end-to-end. This pilot proves the pipeline works — it is **not real catalog data**:

- **Adapter:** `tools/tooling_adapters/mitsubishi_materials_adapter.py` — parses Mitsubishi-format JSON into normalized tooling search records
- **Fixture:** `tools/tooling_adapters/samples/sample_mitsubishi_materials_structured.json` — 7 synthetic records, clearly marked as test fixtures (not manufacturer data)
- **Imported records:** `tool_data/tooling_search/records/mitsubishi_materials_imported_tools.json` — passes import validation and audit (0 issues), searchable via the Enterprise Tooling Search UI
- **Reviewed records:** `tool_data/tooling_search/records/reviewed/mitsubishi_materials_reviewed_tools.json` — reviewed by Joshua Hayes, status `reviewed_family_level_candidate`

All records at every pipeline stage: no feeds/speeds, no dimensions, `cutting_data_status = not_imported`, `verification_status = sample_family_level_not_catalog_verified` (imported) or `reviewed_family_level_candidate` (reviewed). The Mitsubishi Materials adapter pilot is a pipeline proof-of-concept only. Adding real manufacturer catalog data requires separate sourcing, authorization, and re-running the full pipeline with actual catalog records.

### Guhring Adapter Pilot

A second adapter pilot for Guhring KG has been built and run through the same complete pipeline. Guhring covers tool types not addressed by insert-focused brands: drills (solid carbide and HSS-E cobalt), taps, thread mills, reamers, countersinks, endmills, and step drills — introducing seven new `tool_category` values to the search index.

- **Adapter:** `tools/tooling_adapters/guhring_adapter.py`
- **Fixture:** `tools/tooling_adapters/samples/sample_guhring_structured.json` — 8 synthetic records
- **Imported records:** `tool_data/tooling_search/records/guhring_imported_tools.json` — 0 audit issues, searchable via Enterprise Tooling Search UI
- **Reviewed records:** `tool_data/tooling_search/records/reviewed/guhring_reviewed_tools.json` — reviewed by Joshua Hayes, `reviewed_family_level_candidate`

As with Mitsubishi, this is a pipeline proof-of-concept with synthetic fixtures only — not real catalog data.

### Iscar Adapter Pilot

A third adapter pilot for Iscar Ltd. focuses on indexable tooling normalization — turning inserts, milling inserts, high-feed milling inserts (mapped to a distinct `high_feed_insert` category), indexable drills (SUMOCHAM-style replaceable tips), grooving inserts, threading inserts, and boring bars.

- **Adapter:** `tools/tooling_adapters/iscar_adapter.py` — maps Iscar's `chip_former` field to the schema `chipbreaker` field; distinguishes `high_feed_insert` from general `milling_insert`
- **Fixture:** `tools/tooling_adapters/samples/sample_iscar_structured.json` — 8 synthetic records
- **Imported records:** `tool_data/tooling_search/records/iscar_imported_tools.json` — 0 audit issues, searchable
- **Reviewed records:** `tool_data/tooling_search/records/reviewed/iscar_reviewed_tools.json` — reviewed by Joshua Hayes, `reviewed_family_level_candidate`

As with all pilots, this is a pipeline proof-of-concept with synthetic fixtures only — not real catalog data.

### Walter AG Adapter Pilot

A fourth adapter pilot for Walter AG covers the full Walter tooling portfolio — turning inserts (Tiger·tec Silver family), shoulder and face milling inserts (Blaxx M3255 style), solid carbide drills (Walter Titex), indexable drills (D4140-style two-insert systems), thread mills (TC410 solid carbide), grooving inserts (Cut 3), solid carbide endmills (Walter Prototyp), and boring bars (CBo). This pilot introduces the `thread_mill` category (shared with Guhring) and demonstrates the shoulder vs. face milling insert normalization pattern (`ShoulderMillingInsert` and `FaceMillingInsert` both map to `milling_insert`; geometry_tags carry the subtype).

- **Adapter:** `tools/tooling_adapters/walter_adapter.py`
- **Fixture:** `tools/tooling_adapters/samples/sample_walter_structured.json` — 9 synthetic records, clearly marked as test fixtures (not manufacturer data)
- **Imported records:** `tool_data/tooling_search/records/walter_imported_tools.json` — 0 audit issues, searchable
- **Reviewed records:** `tool_data/tooling_search/records/reviewed/walter_reviewed_tooling_records.json` — reviewed by Joshua Hayes, `reviewed_family_level_candidate`

As with all pilots, this is a pipeline proof-of-concept with synthetic fixtures only — not real catalog data.

### Dormer Pramet Adapter Pilot

A fifth adapter pilot for Dormer Pramet covers both the Dormer round-tool segment (solid carbide drills, HSS-cobalt drills, taps, thread mills, reamers, countersinks, endmills) and the Pramet indexable-tooling segment (turning inserts, milling inserts, grooving/parting inserts). This pilot proves that a single adapter can normalize across two distinct tooling segments under one brand, with `tool_category` distinguishing round tools from indexable tooling.

- **Adapter:** `tools/tooling_adapters/dormer_pramet_adapter.py`
- **Fixture:** `tools/tooling_adapters/samples/sample_dormer_pramet_structured.json` — 10 synthetic records, clearly marked as test fixtures (not manufacturer data)
- **Imported records:** `tool_data/tooling_search/records/dormer_pramet_imported_tools.json` — 0 audit issues, searchable
- **Reviewed records:** `tool_data/tooling_search/records/reviewed/dormer_pramet_reviewed_tooling_records.json` — reviewed by Joshua Hayes, `reviewed_family_level_candidate`

As with all pilots, this is a pipeline proof-of-concept with synthetic fixtures only — not real catalog data.

## Install

1. Create and activate a virtual environment.
2. Install the runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. If you want to run tests, install the development dependencies too:

```powershell
python -m pip install -r requirements-dev.txt
```

## Run

Start the Streamlit app from the repo root:

```powershell
streamlit run app.py
```

## Validation Commands

Use these commands from the repo root to verify the app and grade engine baseline:

```powershell
python -m compileall .
pytest
python tools/engine_health_report.py
```

## Project Structure

- `app.py`: Streamlit UI and module navigation
- `grade_engine/`: Recommendation and grade-behavior logic
- `tool_data/`: JSON catalog, lookup, and validation data
- `tests/`: Smoke and validation coverage for the grade engine

## Important Use Note

This app provides shop-support recommendation guidance only. It is not final manufacturer-certified cutting data, and it should not replace supplier catalogs, tooling application engineering, machine limitations, or your shop's approved process standards.
