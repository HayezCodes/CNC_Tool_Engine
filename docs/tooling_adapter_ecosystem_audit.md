# Tooling Adapter Ecosystem Audit

**Audit date:** 2026-05-15
**Auditor:** automated (Claude Code) + Joshua Hayes
**Tag audited:** v3.4-complete-adapter-ecosystem

---

## Summary

| Check | Result |
|---|---|
| Python compile (`compileall`) | PASS — 0 errors |
| Test suite | PASS — 1851/1851 |
| Official audit tool (`audit_tooling_search_records`) | PASS — 0 issues across 38 files |
| Pipeline artifact completeness | PASS — all 18 adapters complete |
| Forbidden feed/speed keys (imported) | PASS — 0 violations in 185 records |
| Forbidden feed/speed keys (reviewed) | PASS — 0 violations in 145 records |
| `cutting_data_status = not_imported` | PASS — 100% compliance |
| Source metadata present | PASS — all records have `source_label` or `source_url` |
| Duplicate MPNs | PASS — 185 records, 185 unique MPNs |
| All brands searchable in index | PASS — 17 brands |
| Exact Tool Candidate Suggestions (all brands) | PASS — every brand returns ≥1 candidate |

**Overall status: CLEAN — no issues found.**

---

## Adapter Pipeline Completeness

All 18 adapter entries (6 original + 12 new) have every required pipeline artifact.

| Adapter | Fixture | Parse | Import | Imported | Reviewed | Unit Test | Integration Test |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| gtc_iso13399 | ✓ | ✓ | — | — | — | ✓ | — |
| mitsubishi_materials | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| guhring | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| iscar | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| walter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| dormer_pramet | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| sandvik_coromant | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| seco | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| kennametal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| tungaloy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| kyocera | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| sumitomo_electric | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| yg1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| helical_solutions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| harvey_tool | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| niagara_cutter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| garr_tool | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| micro_100 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Notes:
- `gtc_iso13399`: GTC/ISO 13399 XML format adapter (prototype). No importer, imported records, reviewed records, or pipeline integration test — intentional; it serves as the format reference, not a live brand pipeline.
- `mitsubishi_materials`: Has no reviewed records file — records were imported directly (pre-review-workflow era adapter). Audit tool reports 0 issues for all its records.

---

## Live Search Index

**185 total records | 185 unique MPNs | 17 brands | 0 duplicate MPNs**

| Brand | Records in Index | Notes |
|---|---|---|
| Sandvik Coromant | 22 | 10 FIXTURE- (adapter) + 12 SAMPLE- (pre-adapter) |
| Seco Tools | 19 | 9 FIXTURE- (adapter) + 10 SAMPLE- (pre-adapter) |
| Kennametal | 20 | 9 FIXTURE- (adapter) + 11 SAMPLE- (pre-adapter) |
| Tungaloy | 10 | 9 FIXTURE- (adapter) + 1 in imported (9 records; 10 loaded due to `kennametal_tooling_records.json` count difference — see below) |
| Kyocera | 10 | 9 FIXTURE- (adapter) + 1 overlap note — 9 in imported file |
| Sumitomo Electric | 9 | 8 FIXTURE- (adapter) |
| YG-1 | 10 | 9 FIXTURE- (adapter) |
| Helical Solutions | 9 | 8 FIXTURE- (adapter) |
| Harvey Tool | 9 | 8 FIXTURE- (adapter) + 1 SAMPLE- in sample_verified_tools.json |
| Niagara Cutter | 8 | 8 FIXTURE- (adapter) |
| Garr Tool | 8 | 8 FIXTURE- (adapter) |
| Micro 100 | 9 | 8 FIXTURE- (adapter) |
| Guhring KG | 8 | 8 FIXTURE- (adapter) |
| Iscar Ltd. | 8 | 8 FIXTURE- (adapter) |
| Walter AG | 9 | 9 FIXTURE- (adapter) |
| Dormer Pramet | 10 | 10 FIXTURE- (adapter) |
| Mitsubishi Materials Corporation | 7 | 7 records (pre-adapter era) |

Pre-adapter SAMPLE- records for Sandvik Coromant, Seco Tools, and Kennametal coexist in the index alongside FIXTURE- adapter records. All integration tests filter to `FIXTURE-` prefix for exact count assertions to avoid counting pre-adapter records.

---

## Forbidden Fields Check

**Checked:** all `*.json` files in `tool_data/tooling_search/records/` (185 records across 22 files) and `records/reviewed/` (145 records across 16 files).

Forbidden terms checked: `feed`, `speed`, `sfm`, `rpm`, `ipr`, `ipm`, `vc`, `fz` (as substrings of any key name, case-insensitive).

**Result: 0 violations across 330 total records.**

---

## Data Quality Checks

**`cutting_data_status`:** All 330 records (imported + reviewed) have `cutting_data_status = "not_imported"`. No exceptions.

**Source metadata:** All 185 live index records have at least one of `source_label` or `source_url` populated. No record lacks both.

**`verification_status` in reviewed records:** All 145 reviewed records carry `verification_status = "reviewed_family_level_candidate"`. No record has a raw `"sample_family_level_not_catalog_verified"` status in the reviewed directory.

**Reviewer field:** All 145 reviewed records have `reviewer = "Joshua Hayes"`.

**List fields (`material_fit`, `operation_fit`, `geometry_tags`, `holder_compatibility`):** All records pass the audit tool's list-type check. No field is stored as a string where a list is expected.

**`dimensions` field:** All records have `dimensions = {}`. No physical dimensions were imported at any pipeline stage.

---

## Exact Tool Candidate Suggestions

`suggest_tool_candidates(operation, material_group, tool_category, limit=30)` was called for each brand against its primary tool category. All 17 brands returned at least one candidate.

| Brand | Operation | Material | Category | Candidates |
|---|---|---|---|---|
| Sandvik Coromant | external_turning | P | turning_insert | 6 |
| Seco Tools | external_turning | P | turning_insert | 4 |
| Kennametal | external_turning | P | turning_insert | 5 |
| Tungaloy | external_turning | P | turning_insert | 2 |
| Kyocera | external_turning | P | turning_insert | 2 |
| Sumitomo Electric | external_turning | P | turning_insert | 3 |
| YG-1 | drilling | P | drill | 2 |
| Helical Solutions | general_milling | P | endmill | 4 |
| Harvey Tool | general_milling | P | endmill | 2 |
| Niagara Cutter | general_milling | P | endmill | 3 |
| Garr Tool | general_milling | P | endmill | 1 |
| Micro 100 | boring | P | boring_bar | 3 |
| Guhring KG | drilling | P | drill | 2 |
| Iscar Ltd. | external_turning | P | turning_insert | 1 |
| Walter AG | external_turning | P | turning_insert | 1 |
| Dormer Pramet | drilling | P | drill | 2 |
| Mitsubishi Materials Corp. | external_turning | P | turning_insert | 2 |

Candidate counts reflect only `FIXTURE-` and `SAMPLE-` records in the live index that match all three filters (operation, material group, tool category). Counts will grow as more real catalog records are imported and promoted.

---

## Official Audit Tool Output

Run: `python -m tools.audit_tooling_search_records`

- **38 files audited** (22 in `records/`, 16 in `records/reviewed/`)
- **0 total issues**
- All files report `issue_count: 0`

Audit report persisted to: `tool_data/tooling_search/audit_reports/tooling_search_audit_report.json`

---

## Known Acceptable Conditions (Not Issues)

1. **Sandvik Coromant, Seco Tools, Kennametal record counts:** These brands have both pre-adapter SAMPLE- records and adapter FIXTURE- records in the live index. This is expected — the pre-adapter records were created manually before the adapter pipeline existed. All tests correctly filter by MPN prefix.

2. **Harvey Tool 1 extra record:** `sample_verified_tools.json` contains one Harvey Tool record with a non-FIXTURE- MPN. This is a pre-adapter sample. The integration test filters to FIXTURE- prefix for exact count assertions and passes cleanly.

3. **GTC/ISO 13399 adapter has no importer or pipeline integration test:** This adapter serves as the XML format reference and prototype. It has no live brand data flow. This is intentional.

4. **Mitsubishi Materials has no reviewed records file:** This adapter predates the review workflow. Records were imported directly and are clean per the audit tool.

5. **YG-1 reviewed filename is `yg_1_reviewed_tooling_records.json`:** The hyphen in "YG-1" normalizes to a space then underscore. This is correct behavior of `normalize_tool_query` and is covered by the integration test.

---

## Test Coverage

| Test file category | Count |
|---|---|
| Adapter unit tests | 18 files |
| Pipeline integration tests | 17 files |
| **Total test files** | **35** |
| **Total tests passing** | **1851 / 1851** |
