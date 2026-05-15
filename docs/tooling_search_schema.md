# Tooling Search Schema

`tool_data/tooling_search/` is the foundation for a future enterprise tooling search layer.

This layer is intentionally separate from:

- reviewed catalog-family guidance in `tool_data/catalog_ingestion/reviewed/`
- recommendation and boosting logic in `grade_engine/`

The exact-tooling search layer is for source-linked tooling records only. In this foundation phase, records may still be sample scaffolds as long as they are clearly marked with verification state and cutting-data state.

## Normalized Exact Tool Record

Each tooling search record should include these normalized fields:

- `brand`
- `tool_category`
- `manufacturer_part_number`
- `series`
- `family_name`
- `designation`
- `grade`
- `chipbreaker`
- `coating`
- `material_fit`
- `operation_fit`
- `geometry_tags`
- `dimensions`
- `holder_compatibility`
- `coolant_capability`
- `source_label`
- `source_url`
- `source_page_reference`
- `verification_status`
- `cutting_data_status`
- `notes`

## Field Guidance

### Identity fields

- `brand`: manufacturer brand name
- `tool_category`: normalized category such as `turning_insert`, `endmill`, `boring_bar`, `indexable_drill`
- `manufacturer_part_number`: exact manufacturer reference when verified; sample placeholder values must be clearly marked in `notes` and `verification_status`
- `series`: manufacturer series/platform when known
- `family_name`: family grouping that connects the exact record to broader shop guidance
- `designation`: ISO or catalog designation when known

### Technical descriptor fields

- `grade`: exact grade only when source-verified; otherwise leave blank or use a clearly marked sample placeholder
- `chipbreaker`: exact chipbreaker only when source-verified; otherwise leave blank or use a clearly marked sample placeholder
- `coating`: exact coating only when source-verified; otherwise leave blank or use a clearly marked sample placeholder
- `material_fit`: normalized ISO material groups like `P`, `M`, `K`, `N`, `S`, `H`
- `operation_fit`: normalized operation tags such as `general_milling`, `profiling`, `external_turning`, `threading`
- `geometry_tags`: normalized geometry and application tags
- `dimensions`: structured dimension object; leave empty when exact catalog dimensions are not verified
- `holder_compatibility`: list of holder or platform notes when known
- `coolant_capability`: conservative normalized value such as `unknown`, `through_coolant_capable`, `external_only`, `verify_by_catalog`

### Source and trust fields

- `source_label`: human-readable source name
- `source_url`: source link
- `source_page_reference`: page, section, or figure reference when available
- `verification_status`: explicit trust state such as `verified_source_page_record` or `sample_family_level_not_catalog_verified`
- `cutting_data_status`: use `not_imported` unless cutting data has been separately and intentionally imported
- `notes`: context, limitations, and verification reminders

## Foundation Rules

- Do not merge these exact-tooling records into reviewed family records.
- Do not import speeds/feeds in this phase.
- Do not invent dimensions, certified grades, or exact catalog numbers.
- Unverified foundation records should use:
  - `verification_status: sample_family_level_not_catalog_verified`
  - `cutting_data_status: not_imported`

## Folder Roles

- `tool_data/tooling_search/records/`: normalized exact-tool record files
- `tool_data/tooling_search/indexes/`: reserved for future persisted indexes
- `grade_engine/tooling_search.py`: load, normalize, filter, search, and explain match behavior
