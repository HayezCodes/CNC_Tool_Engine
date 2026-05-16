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
    __init__.py                                        # namespace package marker
    base_adapter.py                                    # shared contract, helpers, validation bridge
    gtc_iso13399_adapter.py                            # GTC / ISO 13399 XML adapter
    mitsubishi_materials_adapter.py                    # Mitsubishi Materials JSON adapter
    guhring_adapter.py                                 # Guhring KG JSON adapter
    iscar_adapter.py                                   # Iscar Ltd. JSON adapter
    walter_adapter.py                                  # Walter AG JSON adapter
    dormer_pramet_adapter.py                           # Dormer Pramet JSON adapter
    sandvik_coromant_adapter.py                        # Sandvik Coromant JSON adapter
    seco_adapter.py                                    # Seco Tools JSON adapter
    kennametal_adapter.py                              # Kennametal JSON adapter
    tungaloy_adapter.py                                # Tungaloy JSON adapter
    kyocera_adapter.py                                 # Kyocera JSON adapter
    sumitomo_electric_adapter.py                       # Sumitomo Electric JSON adapter
    yg1_adapter.py                                     # YG-1 JSON adapter
    helical_solutions_adapter.py                       # Helical Solutions JSON adapter
    harvey_tool_adapter.py                             # Harvey Tool JSON adapter
    niagara_cutter_adapter.py                          # Niagara Cutter JSON adapter
    garr_tool_adapter.py                               # Garr Tool JSON adapter
    micro_100_adapter.py                               # Micro 100 JSON adapter
    samples/
      sample_gtc_iso13399.xml                          # synthetic test fixture (NOT manufacturer data)
      sample_mitsubishi_materials_structured.json      # synthetic test fixture (NOT manufacturer data)
      sample_guhring_structured.json                   # synthetic test fixture (NOT manufacturer data)
      sample_iscar_structured.json                     # synthetic test fixture (NOT manufacturer data)
      sample_walter_structured.json                    # synthetic test fixture (NOT manufacturer data)
      sample_dormer_pramet_structured.json             # synthetic test fixture (NOT manufacturer data)
      sample_sandvik_coromant_structured.json          # synthetic test fixture (NOT manufacturer data)
      sample_seco_structured.json                      # synthetic test fixture (NOT manufacturer data)
      sample_kennametal_structured.json                # synthetic test fixture (NOT manufacturer data)
      sample_tungaloy_structured.json                  # synthetic test fixture (NOT manufacturer data)
      sample_kyocera_structured.json                   # synthetic test fixture (NOT manufacturer data)
      sample_sumitomo_electric_structured.json         # synthetic test fixture (NOT manufacturer data)
      sample_yg1_structured.json                       # synthetic test fixture (NOT manufacturer data)
      sample_helical_solutions_structured.json         # synthetic test fixture (NOT manufacturer data)
      sample_harvey_tool_structured.json               # synthetic test fixture (NOT manufacturer data)
      sample_niagara_cutter_structured.json            # synthetic test fixture (NOT manufacturer data)
      sample_garr_tool_structured.json                 # synthetic test fixture (NOT manufacturer data)
      sample_micro_100_structured.json                 # synthetic test fixture (NOT manufacturer data)
    output/
      .gitkeep                                         # output directory stub
      <name>_records.json                              # adapter output (staged, not yet in records/)

  parse_gtc_iso13399_sample.py               # runner: parse sample, validate, write output
  parse_mitsubishi_materials_sample.py       # runner: parse Mitsubishi sample, validate, write output
  parse_guhring_sample.py                    # runner: parse Guhring sample
  parse_iscar_sample.py                      # runner: parse Iscar sample
  parse_walter_sample.py                     # runner: parse Walter sample
  parse_dormer_pramet_sample.py              # runner: parse Dormer Pramet sample
  parse_sandvik_coromant_sample.py           # runner: parse Sandvik Coromant sample
  parse_seco_sample.py                       # runner: parse Seco Tools sample
  parse_kennametal_sample.py                 # runner: parse Kennametal sample
  parse_tungaloy_sample.py                   # runner: parse Tungaloy sample
  parse_kyocera_sample.py                    # runner: parse Kyocera sample
  parse_sumitomo_electric_sample.py          # runner: parse Sumitomo Electric sample
  parse_yg1_sample.py                        # runner: parse YG-1 sample
  parse_helical_solutions_sample.py          # runner: parse Helical Solutions sample
  parse_harvey_tool_sample.py                # runner: parse Harvey Tool sample
  parse_niagara_cutter_sample.py             # runner: parse Niagara Cutter sample
  parse_garr_tool_sample.py                  # runner: parse Garr Tool sample
  parse_micro_100_sample.py                  # runner: parse Micro 100 sample
  import_mitsubishi_adapter_output.py        # importer: adapter output → records/
  import_guhring_adapter_output.py           # importer: adapter output → records/
  import_iscar_adapter_output.py             # importer: adapter output → records/
  import_walter_adapter_output.py            # importer: adapter output → records/
  import_dormer_pramet_adapter_output.py     # importer: adapter output → records/
  import_sandvik_coromant_adapter_output.py  # importer: adapter output → records/
  import_seco_adapter_output.py              # importer: adapter output → records/
  import_kennametal_adapter_output.py        # importer: adapter output → records/
  import_tungaloy_adapter_output.py          # importer: adapter output → records/
  import_kyocera_adapter_output.py           # importer: adapter output → records/
  import_sumitomo_electric_adapter_output.py # importer: adapter output → records/
  import_yg1_adapter_output.py               # importer: adapter output → records/
  import_helical_solutions_adapter_output.py # importer: adapter output → records/
  import_harvey_tool_adapter_output.py       # importer: adapter output → records/
  import_niagara_cutter_adapter_output.py    # importer: adapter output → records/
  import_garr_tool_adapter_output.py         # importer: adapter output → records/
  import_micro_100_adapter_output.py         # importer: adapter output → records/
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

## Walter Adapter (`walter_adapter.py`)

Parses Walter-style structured JSON tooling records into normalized tooling search records. Walter AG covers a broad tooling portfolio across turning, milling, drilling, threading, grooving, and boring — combining insert-based tooling (Tiger·tec Silver turning grades, Blaxx shoulder milling) with solid carbide tooling families (Walter Titex drills, Walter Prototyp endmills, TC410 thread mills).

**Shoulder milling insert normalization:**

Walter shoulder milling inserts (`ShoulderMillingInsert`) and face milling inserts (`FaceMillingInsert`) both normalize to `tool_category = "milling_insert"`. This is consistent with how other adapters treat milling subtypes — the `tool_category` identifies the insert type; `geometry_tags` (e.g., `SquareShoulder`, `True90Degree`, `FaceMilling`) and `operation_fit` (e.g., `shoulder_milling`, `face_milling`) carry the specific subtype information for downstream filtering and display.

**Drilling family mapping — solid vs. indexable:**

Walter Titex solid carbide drills (`SolidCarbideDrill`) map to `tool_category = "drill"`, consistent with Guhring solid carbide drills. Walter D4140-style two-insert indexable drills (`IndexableDrill`) map to `tool_category = "indexable_drill"`. This split allows operators to filter specifically for solid-shank vs. insert-based drilling systems.

**Thread mill normalization:**

Walter TC410-style solid carbide thread mills (`ThreadMill`, `SolidCarbideThreadMill`) map to `tool_category = "thread_mill"`. Thread mill operations (`ThreadMilling`, `ExternalThreadMilling`, `InternalThreadMilling`) are mapped to snake_case operation values. No tap category is introduced by this adapter — threading inserts remain a distinct category if added in the future.

**Solid carbide endmill normalization:**

Walter Prototyp solid carbide endmills (`SolidCarbideEndmill`) map to `tool_category = "endmill"`, consistent with all other adapters. No Walter-specific subtype is introduced.

**Tool category mapping (Walter-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | Tiger·tec Silver family |
| `MillingInsert`, `ShoulderMillingInsert`, `FaceMillingInsert` | `milling_insert` | geometry_tags distinguish subtype |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | |
| `SolidCarbideDrill`, `HSSEDrill` | `drill` | Titex family |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | D4140-style two-insert systems |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | TC410 family |
| `ThreadingInsert` | `threading_insert` | |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | Cut 3 family |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | Prototyp family |
| `BoringBar`, `BoringToolholder` | `boring_bar` | CBo family |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |

**New operations introduced:**

| Input string | schema operation |
|---|---|
| `ThreadMilling` | `thread_milling` |
| `ExternalThreadMilling` | `external_thread_milling` |
| `InternalThreadMilling` | `internal_thread_milling` |

**Field mapping:** identical to the Mitsubishi Materials adapter — `part_number → manufacturer_part_number`, `tool_type → tool_category`, `material_groups → material_fit`, `operations → operation_fit`, `geometry_tags → geometry_tags`, `holder_compatibility → holder_compatibility`, `coolant → coolant_capability`. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_walter_sample.py
python tools/parse_walter_sample.py --dry-run
python tools/import_walter_adapter_output.py
python tools/import_walter_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/walter_sample_records.json` (9 synthetic fixture records: 1 turning insert, 2 milling inserts (shoulder + face), 1 solid carbide drill, 1 indexable drill, 1 thread mill, 1 grooving insert, 1 endmill, 1 boring bar). Imported records go to `tool_data/tooling_search/records/walter_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/walter_reviewed_tooling_records.json`.

## Dormer Pramet Adapter (`dormer_pramet_adapter.py`)

Parses Dormer Pramet-style structured JSON tooling records into normalized tooling search records. Dormer Pramet was formed in 2014 from the merger of Dormer Tools (round tools: drills, taps, reamers, countersinks, endmills, thread mills) and Pramet Tools (Czech indexable tooling brand: turning inserts, milling inserts, grooving inserts). The adapter handles both sub-brands through a single normalized schema path — `tool_category` distinguishes round tools from indexable tooling.

**Dormer round-tool normalization:**

Dormer round tools cover the full range of hole-making and finishing operations. Solid carbide (`SolidCarbideDrill`) and HSS-cobalt (`HSSCobaltDrill`, `HSSEDrill`) drills both map to `tool_category = "drill"`. Tap variants (`SpiralTap`, `MachineTap`, `FormTap`) all map to `tap`. Thread mills map to `thread_mill`. Reamers map to `reamer`. Countersinks and chamfer tools map to `countersink`. Endmills map to `endmill`.

**Pramet indexable-tool normalization:**

Pramet indexable tooling (turning inserts, milling inserts, grooving/parting inserts) normalizes identically to other indexable brands — `TurningInsert → turning_insert`, `MillingInsert → milling_insert`, `GroovingInsert / PartingInsert → grooving_insert`. Chipbreaker codes from Pramet's insert designation system are preserved in the `chipbreaker` field without translation.

**Tapping/threading/reaming operation mapping:**

| Input string | schema operation |
|---|---|
| `Tapping` | `tapping` |
| `ThroughHoleTapping` | `through_hole_tapping` |
| `BlindHoleTapping` | `blind_hole_tapping` |
| `ThreadMilling`, `ExternalThreadMilling`, `InternalThreadMilling` | `thread_milling`, `external_thread_milling`, `internal_thread_milling` |
| `Reaming`, `FinishReaming`, `PrecisionReaming` | `reaming`, `finish_reaming`, `precision_reaming` |
| `Countersinking`, `Chamfering`, `Deburring` | `countersinking`, `chamfering`, `deburring` |

**Tool category mapping (Dormer Pramet-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `SolidCarbideDrill`, `HSSCobaltDrill`, `HSSEDrill`, `HSSDrill` | `drill` | Dormer round tools |
| `SpiralTap`, `MachineTap`, `FormTap`, `ExtrusionTap` | `tap` | Dormer taps |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | Dormer thread mills |
| `Reamer`, `SolidCarbideReamer` | `reamer` | Dormer reamers |
| `Countersink`, `ChamferTool` | `countersink` | Dormer countersinks |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | Dormer endmills |
| `StepDrill`, `CombinationDrill` | `step_drill` | Dormer step drills |
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | Pramet indexable |
| `MillingInsert`, `ShoulderMillingInsert`, `FaceMillingInsert` | `milling_insert` | Pramet indexable |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | Pramet indexable |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | Pramet indexable |
| `ThreadingInsert` | `threading_insert` | Pramet indexable |
| `BoringBar`, `BoringToolholder` | `boring_bar` | Pramet indexable |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | Pramet indexable |

**Field mapping:** identical to all other JSON adapters — `part_number → manufacturer_part_number`, `tool_type → tool_category`, `material_groups → material_fit`, `operations → operation_fit`, `geometry_tags → geometry_tags`, `holder_compatibility → holder_compatibility`, `coolant → coolant_capability`. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_dormer_pramet_sample.py
python tools/parse_dormer_pramet_sample.py --dry-run
python tools/import_dormer_pramet_adapter_output.py
python tools/import_dormer_pramet_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/dormer_pramet_sample_records.json` (10 synthetic fixture records: 2 drills (solid carbide + HSS-cobalt), 1 tap, 1 thread mill, 1 reamer, 1 countersink, 1 endmill, 1 Pramet turning insert, 1 Pramet milling insert, 1 Pramet grooving insert). Imported records go to `tool_data/tooling_search/records/dormer_pramet_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/dormer_pramet_reviewed_tooling_records.json`.

## Sandvik Coromant Adapter (`sandvik_coromant_adapter.py`)

Parses Sandvik Coromant-style structured JSON tooling records into normalized tooling search records. Sandvik Coromant (part of Sandvik AB) is a Swedish precision tooling manufacturer and one of the world's largest cutting tool suppliers. Key product families: CoroTurn turning inserts and toolholders, CoroMill milling inserts and cutters, CoroDrill solid carbide and indexable drilling, CoroThread threading inserts, CoroCut grooving and parting, Silent Tools vibration-damped boring bars (SilentToolsBar), and CoroMill Plura solid carbide endmills. Grades use the Tiger·tec Silver PVD/CVD coating families (GC4000 series).

**Silent Tools boring bar normalization:**

Sandvik's vibration-damped boring bars use the `SilentToolsBar` type in addition to the standard `BoringBar`. Both map to `tool_category = "boring_bar"`, preserving the application classification while allowing `geometry_tags` (e.g., `vibration_damped`) to carry the sub-type distinction.

**Tool category mapping (Sandvik Coromant-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | CoroTurn family |
| `MillingInsert`, `ShoulderMillingInsert`, `FaceMillingInsert`, `IndexableMillingInsert` | `milling_insert` | CoroMill family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | |
| `SolidCarbideDrill`, `HSSDrill` | `drill` | CoroDrill solid family |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | CoroDrill indexable family |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | CoroMill Plura |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | CoroCut family |
| `ThreadingInsert` | `threading_insert` | CoroThread family |
| `BoringBar`, `SilentToolsBar` | `boring_bar` | Silent Tools vibration-damped |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter — same JSON format (`catalog_header` + `tool_records`), same field conventions. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_sandvik_coromant_sample.py
python tools/parse_sandvik_coromant_sample.py --dry-run
python tools/import_sandvik_coromant_adapter_output.py
python tools/import_sandvik_coromant_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/sandvik_coromant_sample_records.json` (10 synthetic fixture records: 2 turning inserts, 2 milling inserts, 1 high-feed insert, 1 solid carbide drill, 1 endmill, 1 grooving insert, 1 threading insert, 1 boring bar). Imported records go to `tool_data/tooling_search/records/sandvik_coromant_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/sandvik_coromant_reviewed_tooling_records.json`.

## Seco Tools Adapter (`seco_adapter.py`)

Parses Seco Tools-style structured JSON tooling records into normalized tooling search records. Seco Tools (part of Seco Tools AB, owned by Sandvik AB) is a Swedish cutting tool manufacturer. Key product families: Duratomic turning inserts (TC/TP coating series), Turbo milling inserts, Feedmax solid carbide drills, Jabro solid carbide endmills, MDT grooving and parting inserts, and Snap Tap threading inserts.

**Tool category mapping (Seco-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | Duratomic family |
| `MillingInsert`, `ShoulderMillingInsert`, `FaceMillingInsert`, `IndexableMillingInsert` | `milling_insert` | Turbo family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | |
| `SolidCarbideDrill`, `HSSDrill`, `HSSCobaltDrill` | `drill` | Feedmax family |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | Jabro family |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | MDT family |
| `ThreadingInsert` | `threading_insert` | Snap Tap family |
| `BoringBar` | `boring_bar` | |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_seco_sample.py
python tools/parse_seco_sample.py --dry-run
python tools/import_seco_adapter_output.py
python tools/import_seco_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/seco_sample_records.json` (9 synthetic fixture records). Imported records go to `tool_data/tooling_search/records/seco_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/seco_reviewed_tooling_records.json`.

## Kennametal Adapter (`kennametal_adapter.py`)

Parses Kennametal-style structured JSON tooling records into normalized tooling search records. Kennametal Inc. is a US-based cutting tool and tooling systems manufacturer. Key product families: Beyond coating turning inserts (KC5010/KC5025 grades), HARVI solid carbide endmills, GO Drill solid carbide drills, KGOP grooving inserts, KM quick-change toolholding, Mill 4-12 milling inserts, and threading inserts.

**Tool category mapping (Kennametal-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | Beyond coating grades |
| `MillingInsert`, `ShoulderMillingInsert`, `FaceMillingInsert`, `IndexableMillingInsert` | `milling_insert` | Mill 4-12 family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | |
| `SolidCarbideDrill`, `HSSDrill`, `HSSCobaltDrill` | `drill` | GO Drill family |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | HARVI family |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | KGOP family |
| `ThreadingInsert` | `threading_insert` | |
| `BoringBar`, `BoringToolholder` | `boring_bar` | |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_kennametal_sample.py
python tools/parse_kennametal_sample.py --dry-run
python tools/import_kennametal_adapter_output.py
python tools/import_kennametal_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/kennametal_sample_records.json` (9 synthetic fixture records). Imported records go to `tool_data/tooling_search/records/kennametal_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/kennametal_reviewed_tooling_records.json`.

## Tungaloy Adapter (`tungaloy_adapter.py`)

Parses Tungaloy-style structured JSON tooling records into normalized tooling search records. Tungaloy Corporation (part of IMC Group) is a Japanese cutting tool manufacturer. Key product families: TungTurn turning inserts (AH/T9000-series grades), TungMeister milling inserts, DoFeedMill high-feed milling inserts, TungDrill Quattro indexable drills, TungEnd solid carbide endmills, TungCut grooving and parting inserts, TungThread threading inserts, and EZBore boring bars.

**DoFeedMill high-feed insert normalization:**

Tungaloy's DoFeedMill inserts use `HighFeedMillingInsert` as the `tool_type`. These map to `tool_category = "high_feed_insert"`, consistent with how other adapters classify high-feed geometry. The DoFeedMill's distinctive large corner radius and shallow depth-of-cut design is preserved in `geometry_tags` rather than the category name.

**Tool category mapping (Tungaloy-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | TungTurn family |
| `MillingInsert`, `IndexableMillingInsert`, `FaceMillingInsert`, `ShoulderMillingInsert` | `milling_insert` | TungMeister family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | DoFeedMill |
| `SolidCarbideDrill`, `HSSDrill` | `drill` | |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | TungDrill Quattro |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | TungEnd family |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | TungCut family |
| `ThreadingInsert` | `threading_insert` | TungThread family |
| `BoringBar` | `boring_bar` | EZBore family |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill` | `thread_mill` | |
| `Reamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_tungaloy_sample.py
python tools/parse_tungaloy_sample.py --dry-run
python tools/import_tungaloy_adapter_output.py
python tools/import_tungaloy_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/tungaloy_sample_records.json` (9 synthetic fixture records: 2 turning inserts, 1 milling insert, 1 high-feed insert, 1 solid carbide drill, 1 indexable drill, 1 endmill, 1 grooving insert, 1 threading insert). Imported records go to `tool_data/tooling_search/records/tungaloy_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/tungaloy_reviewed_tooling_records.json`.

## Kyocera Adapter (`kyocera_adapter.py`)

Parses Kyocera-style structured JSON tooling records into normalized tooling search records. Kyocera Corporation (Kyocera Precision Tools) is a Japanese cutting tool manufacturer. Key product families: PR/CA/PV-series Megacoat Nano turning inserts, MFH Miracle milling inserts, MFH Raptor high-feed inserts, MAS/MDS solid carbide drills, solid carbide endmills, GBA/GBR grooving inserts, threading inserts, and S-STLCR-series boring bars.

**Megacoat Nano grade normalization:**

Kyocera's Megacoat Nano grades (PR1535, CA6535, etc.) are recorded in the `grade` field without translation. The `geometry_tags` and `material_fit` carry the application information (ISO group codes P, M, K, N, S, H).

**Tool category mapping (Kyocera-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | PR/CA/PV grades |
| `MillingInsert`, `IndexableMillingInsert`, `FaceMillingInsert`, `ShoulderMillingInsert` | `milling_insert` | MFH Miracle family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | MFH Raptor family |
| `SolidCarbideDrill`, `HSSDrill` | `drill` | MAS/MDS family |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | GBA/GBR family |
| `ThreadingInsert` | `threading_insert` | |
| `BoringBar` | `boring_bar` | S-STLCR family |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill` | `thread_mill` | |
| `Reamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_kyocera_sample.py
python tools/parse_kyocera_sample.py --dry-run
python tools/import_kyocera_adapter_output.py
python tools/import_kyocera_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/kyocera_sample_records.json` (9 synthetic fixture records: 2 turning inserts, 1 milling insert, 1 high-feed insert, 1 solid carbide drill, 1 endmill, 1 grooving insert, 1 threading insert, 1 boring bar). Imported records go to `tool_data/tooling_search/records/kyocera_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/kyocera_reviewed_tooling_records.json`.

## Sumitomo Electric Adapter (`sumitomo_electric_adapter.py`)

Parses Sumitomo Electric-style structured JSON tooling records into normalized tooling search records. Sumitomo Electric Hardmetal Corporation is a Japanese cutting tool manufacturer. Key product families: AC/WBN/EH-series turning inserts, SEXL/SNEX milling inserts, LNMX high-feed inserts, MDW modular drills (indexable), solid carbide endmills (WEX-H series), GY grooving inserts, and threading inserts.

**MDW modular drill normalization:**

Sumitomo's MDW modular drill system is an indexable drill where the cutting tip is replaceable. This maps to `tool_category = "indexable_drill"`, consistent with how other adapters classify body-plus-replaceable-tip systems.

**Tool category mapping (Sumitomo Electric-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert`, `IndexableTurningInsert` | `turning_insert` | AC/WBN/EH grades |
| `MillingInsert`, `IndexableMillingInsert`, `FaceMillingInsert`, `ShoulderMillingInsert` | `milling_insert` | SEXL/SNEX family |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | LNMX family |
| `SolidCarbideDrill`, `HSSDrill` | `drill` | |
| `IndexableDrill`, `DrillInsert` | `indexable_drill` | MDW modular drills |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | WEX-H family |
| `GroovingInsert`, `PartingInsert` | `grooving_insert` | GY family |
| `ThreadingInsert` | `threading_insert` | |
| `BoringBar` | `boring_bar` | |
| `SpiralTap`, `MachineTap` | `tap` | |
| `ThreadMill` | `thread_mill` | |
| `Reamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_sumitomo_electric_sample.py
python tools/parse_sumitomo_electric_sample.py --dry-run
python tools/import_sumitomo_electric_adapter_output.py
python tools/import_sumitomo_electric_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/sumitomo_electric_sample_records.json` (8 synthetic fixture records: 2 turning inserts, 1 milling insert, 1 high-feed insert, 1 indexable drill, 1 endmill, 1 grooving insert, 1 threading insert). Imported records go to `tool_data/tooling_search/records/sumitomo_electric_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/sumitomo_electric_reviewed_tooling_records.json`.

## YG-1 Adapter (`yg1_adapter.py`)

Parses YG-1-style structured JSON tooling records into normalized tooling search records. YG-1 Tool Company is a Korean cutting tool manufacturer known for round tooling across drills, endmills, taps, thread mills, and reamers. Key product families: Dream Drill solid carbide drills, Dream EMS solid carbide endmills (4-flute general, 3-flute aluminum), Hi-Pro Syn spiral taps and carbide taps, solid carbide thread mills, solid carbide reamers, and indexable inserts.

**Tap variant normalization:**

YG-1 offers multiple tap geometries — spiral-flute (`SpiralTap`), machine tap (`MachineTap`), form tap (`FormTap`), and carbide spiral tap (`CarbideSpiralTap`) — all mapping to `tool_category = "tap"`. The specific tap type is preserved in `geometry_tags` and `designation` for downstream selection without creating distinct categories for each variant.

**Slug → filename mapping note:**

The brand name "YG-1" contains a hyphen. `normalize_tool_query("yg-1")` returns `"yg 1"`, and the reviewed record filename is `yg_1_reviewed_tooling_records.json` (spaces replaced by underscores). The filter `{"brand": "yg-1"}` normalizes to `"yg 1"`, which matches the stored brand `"YG-1"` correctly.

**Tool category mapping (YG-1-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `TurningInsert` | `turning_insert` | |
| `MillingInsert` | `milling_insert` | |
| `HighFeedMillingInsert`, `HighFeedInsert` | `high_feed_insert` | |
| `SolidCarbideDrill`, `HSSDrill`, `HSSCobaltDrill` | `drill` | Dream Drill family |
| `IndexableDrill` | `indexable_drill` | |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | Dream EMS family |
| `GroovingInsert` | `grooving_insert` | |
| `ThreadingInsert` | `threading_insert` | |
| `BoringBar` | `boring_bar` | |
| `SpiralTap`, `MachineTap`, `FormTap`, `CarbideSpiralTap` | `tap` | Hi-Pro Syn family |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_yg1_sample.py
python tools/parse_yg1_sample.py --dry-run
python tools/import_yg1_adapter_output.py
python tools/import_yg1_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/yg1_sample_records.json` (9 synthetic fixture records: 1 drill, 2 endmills, 1 tap, 1 thread mill, 1 reamer, 1 countersink, 1 turning insert, 1 grooving insert). Imported records go to `tool_data/tooling_search/records/yg1_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/yg_1_reviewed_tooling_records.json`.

## Helical Solutions Adapter (`helical_solutions_adapter.py`)

Parses Helical Solutions-style structured JSON tooling records into normalized tooling search records. Helical Solutions (part of Harvey Performance Company) is a US solid carbide endmill specialist. Key product families: HEV-5 5-flute general-purpose endmills, HVNI 3-flute aluminum endmills, 5-flute finishing endmills, 7-flute roughers (NF series), 4-flute corner radius endmills, dynamic milling variable-helix endmills, solid carbide drills, and thread mills.

**Endmill-focused portfolio normalization:**

Helical Solutions is primarily an endmill brand. All endmill variants (variable-helix, corner-radius, long-reach, stub-length) map to `tool_category = "endmill"`. Sub-type distinctions (flute count, geometry, application) are preserved in `geometry_tags` (e.g., `five_flute`, `variable_helix`, `corner_radius`) and `operation_fit` (e.g., `dynamic_milling`, `trochoidal_milling`).

**Tool category mapping (Helical Solutions-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `SolidCarbideEndmill`, `Endmill` | `endmill` | All HEV/HVNI/NF variants |
| `SolidCarbideDrill`, `SpotDrill` | `drill` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |
| `TurningInsert` | `turning_insert` | |
| `MillingInsert` | `milling_insert` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_helical_solutions_sample.py
python tools/parse_helical_solutions_sample.py --dry-run
python tools/import_helical_solutions_adapter_output.py
python tools/import_helical_solutions_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/helical_solutions_sample_records.json` (8 synthetic fixture records: 6 endmills, 1 drill, 1 thread mill). Imported records go to `tool_data/tooling_search/records/helical_solutions_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/helical_solutions_reviewed_tooling_records.json`.

## Harvey Tool Adapter (`harvey_tool_adapter.py`)

Parses Harvey Tool-style structured JSON tooling records into normalized tooling search records. Harvey Tool Company is a US specialty tooling manufacturer. Key product families: miniature ball nose endmills, long-reach endmills, internal and external thread mills, solid carbide reamers, single-flute countersinks, solid carbide drills, and step drills.

**Internal vs. external thread mill normalization:**

Harvey Tool offers both internal thread mills (`InternalThreadMill`) and external thread mills (`ExternalThreadMill`) as distinct product lines. Both map to `tool_category = "thread_mill"`. The internal/external distinction is preserved in `geometry_tags` (e.g., `internal_thread_form`, `external_thread_form`) and `operation_fit` (`internal_thread_milling`, `external_thread_milling`).

**Step drill normalization:**

Harvey Tool step drills (`StepDrill`) produce two diameters in a single pass and map to `tool_category = "step_drill"`. This category is distinct from standard solid carbide drills (`SolidCarbideDrill → drill`) and allows operators to filter specifically for combination hole-making tools.

**Tool category mapping (Harvey Tool-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `SolidCarbideEndmill`, `Endmill`, `BallNoseEndmill` | `endmill` | Ball nose and long-reach variants |
| `SolidCarbideDrill`, `SpotDrill` | `drill` | |
| `ThreadMill`, `SolidCarbideThreadMill`, `InternalThreadMill`, `ExternalThreadMill` | `thread_mill` | All thread mill geometries |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | Single-flute countersinks |
| `StepDrill` | `step_drill` | Combination hole tools |
| `TurningInsert` | `turning_insert` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_harvey_tool_sample.py
python tools/parse_harvey_tool_sample.py --dry-run
python tools/import_harvey_tool_adapter_output.py
python tools/import_harvey_tool_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/harvey_tool_sample_records.json` (8 synthetic fixture records: 2 endmills, 1 internal thread mill, 1 external thread mill, 1 reamer, 1 countersink, 1 drill, 1 step drill). Imported records go to `tool_data/tooling_search/records/harvey_tool_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/harvey_tool_reviewed_tooling_records.json`.

## Niagara Cutter Adapter (`niagara_cutter_adapter.py`)

Parses Niagara Cutter-style structured JSON tooling records into normalized tooling search records. Niagara Cutter (part of Greenfield Industries) is a US cutting tool manufacturer. Key product families: 4-flute square endmills, aluminum-specific endmills, high-performance 5-flute endmills, roughing endmills, solid carbide drills, reamers, thread mills, and spiral taps.

**Tool category mapping (Niagara Cutter-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `SolidCarbideEndmill`, `Endmill` | `endmill` | Square and high-performance variants |
| `SolidCarbideDrill`, `HSSDrill`, `SpotDrill` | `drill` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `SpiralTap`, `MachineTap`, `FormTap`, `CarbideSpiralTap` | `tap` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |
| `TurningInsert` | `turning_insert` | |
| `MillingInsert` | `milling_insert` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_niagara_cutter_sample.py
python tools/parse_niagara_cutter_sample.py --dry-run
python tools/import_niagara_cutter_adapter_output.py
python tools/import_niagara_cutter_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/niagara_cutter_sample_records.json` (8 synthetic fixture records: 4 endmills, 1 drill, 1 reamer, 1 thread mill, 1 tap). Imported records go to `tool_data/tooling_search/records/niagara_cutter_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/niagara_cutter_reviewed_tooling_records.json`.

## Garr Tool Adapter (`garr_tool_adapter.py`)

Parses Garr Tool-style structured JSON tooling records into normalized tooling search records. Garr Tool is a US solid carbide cutting tool manufacturer. Key product families: 4-flute square endmills, 2-flute aluminum endmills, ball nose endmills, roughing endmills (corncob style), solid carbide drills, reamers, thread mills, and countersinks.

**Ball nose endmill normalization:**

Garr Tool's `BallNoseEndmill` type maps to `tool_category = "endmill"`, consistent with other adapters. The ball nose geometry is preserved in `geometry_tags` (e.g., `ball_nose`) and `operation_fit` (e.g., `profiling`, `finishing`) for downstream filtering without introducing a separate category.

**Tool category mapping (Garr Tool-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `SolidCarbideEndmill`, `Endmill`, `BallNoseEndmill` | `endmill` | All endmill geometries |
| `SolidCarbideDrill`, `SpotDrill` | `drill` | |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `Countersink` | `countersink` | |
| `StepDrill` | `step_drill` | |
| `TurningInsert` | `turning_insert` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_garr_tool_sample.py
python tools/parse_garr_tool_sample.py --dry-run
python tools/import_garr_tool_adapter_output.py
python tools/import_garr_tool_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/garr_tool_sample_records.json` (8 synthetic fixture records: 4 endmills, 1 drill, 1 reamer, 1 thread mill, 1 countersink). Imported records go to `tool_data/tooling_search/records/garr_tool_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/garr_tool_reviewed_tooling_records.json`.

## Micro 100 Adapter (`micro_100_adapter.py`)

Parses Micro 100-style structured JSON tooling records into normalized tooling search records. Micro 100 Tool Corporation is a US manufacturer specializing in solid carbide boring bars, grooving tools, and threading tools. Key product families: solid carbide boring bars (QB, QSSR series), external grooving inserts (QGE), face grooving tools (QFG), external threading inserts (QXT), thread mills (TMFC), solid carbide endmills (SE series), and countersinks (CSC series).

**Boring bar specialization:**

Unlike most adapter brands that treat boring bars as incidental, Micro 100's portfolio centers on solid carbide boring bars. Both `SolidCarbideBoringBar` and the generic `BoringBar` type map to `tool_category = "boring_bar"`. The QB general-purpose boring bars and QSSR small-diameter (sub-millimeter bore) variants are distinguished by `series` and `geometry_tags`.

**Grooving tool normalization:**

Micro 100 produces both external grooving inserts (`ExternalGroovingInsert`) and face grooving tools (`FaceGroovingTool`). Both map to `tool_category = "grooving_insert"`, with `operation_fit` (`grooving`, `face_grooving`) and `geometry_tags` carrying the application distinction.

**Tool category mapping (Micro 100-specific):**

| tool_type value | schema tool_category | Notes |
|---|---|---|
| `BoringBar`, `SolidCarbideBoringBar` | `boring_bar` | QB and QSSR series |
| `GroovingInsert`, `ExternalGroovingInsert`, `FaceGroovingTool` | `grooving_insert` | QGE and QFG series |
| `ThreadingInsert`, `ExternalThreadingInsert` | `threading_insert` | QXT series |
| `ThreadMill`, `SolidCarbideThreadMill` | `thread_mill` | TMFC series |
| `SolidCarbideEndmill`, `Endmill` | `endmill` | SE series |
| `Countersink` | `countersink` | CSC series |
| `SolidCarbideDrill`, `SpotDrill` | `drill` | |
| `Reamer`, `SolidCarbideReamer` | `reamer` | |
| `TurningInsert` | `turning_insert` | |

**Field mapping:** identical to the Mitsubishi Materials adapter. Rejection policy and safe defaults are the same.

Running the sample:

```bash
python tools/parse_micro_100_sample.py
python tools/parse_micro_100_sample.py --dry-run
python tools/import_micro_100_adapter_output.py
python tools/import_micro_100_adapter_output.py --dry-run
```

Output is written to `tools/tooling_adapters/output/micro_100_sample_records.json` (8 synthetic fixture records: 2 boring bars, 2 grooving inserts, 1 threading insert, 1 thread mill, 1 endmill, 1 countersink). Imported records go to `tool_data/tooling_search/records/micro_100_imported_tools.json`. Reviewed staging records are in `tool_data/tooling_search/records/reviewed/micro_100_reviewed_tooling_records.json`.

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
