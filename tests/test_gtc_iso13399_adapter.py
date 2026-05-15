"""Tests for the GTC/ISO 13399 adapter foundation.

Covers:
- Sample XML fixture parses without errors
- All required schema fields present in output
- Forbidden feed/speed fields are rejected at the record level
- List fields normalize correctly (material_fit, operation_fit, geometry_tags)
- cutting_data_status is always 'not_imported'
- verification_status is a valid value
- Output passes base adapter validation
- Output passes import_tooling_records importer validation
- Tool category mapping works
- Operation mapping works
- Coolant capability mapping works
- XML with missing <ToolItems> returns empty list with error
- Malformed XML returns empty list with error
- No app or recommendation modules required
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from tools.tooling_adapters.base_adapter import (
    ISO_MATERIAL_GROUPS,
    VALID_CUTTING_DATA_STATUSES,
    VALID_VERIFICATION_STATUSES,
    field_contains_forbidden_term,
    make_empty_record,
    normalize_geometry_tags,
    normalize_material_fit,
    normalize_operation_fit,
    validate_adapter_output,
)
from tools.tooling_adapters.gtc_iso13399_adapter import (
    GtcIso13399Adapter,
    parse_gtc_file,
)
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS


SAMPLE_XML_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_gtc_iso13399.xml"
)

EXPECTED_RECORD_COUNT = 5


# ── Fixtures and helpers ─────────────────────────────────────────────────────

def _minimal_xml(tool_items_xml: str, *, forbidden_element: str = "") -> str:
    """Build a minimal GTC XML document for inline testing."""
    extra = f"<{forbidden_element}>999</{forbidden_element}>" if forbidden_element else ""
    return dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <GenericToolCatalog version="2.0">
          <CatalogHeader>
            <ManufacturerName>Test Manufacturer</ManufacturerName>
            <CatalogLabel>Test Catalog 2025</CatalogLabel>
            <CatalogURL>https://example.com/test</CatalogURL>
            <IssueDate>2025-01-01</IssueDate>
          </CatalogHeader>
          <ToolItems>
            {tool_items_xml}
          </ToolItems>
        </GenericToolCatalog>
    """)


def _make_tool_item_xml(
    mpn: str = "TEST-MPN-001",
    category: str = "TurningInsert",
    materials: list[str] | None = None,
    operations: list[str] | None = None,
    extra_elements: str = "",
) -> str:
    materials = materials or ["P", "M"]
    operations = operations or ["ExternalTurning", "Facing"]
    mat_xml = "".join(f"<MaterialGroup>{m}</MaterialGroup>" for m in materials)
    ops_xml = "".join(f"<Operation>{o}</Operation>" for o in operations)
    return f"""
        <ToolItem>
          <MPN>{mpn}</MPN>
          <ToolCategory>{category}</ToolCategory>
          <Series>Test Series</Series>
          <FamilyName>Test family</FamilyName>
          <Designation>CNMG 120408</Designation>
          <Grade>TEST-GRADE</Grade>
          <Chipbreaker>TEST-CB</Chipbreaker>
          <Coating>TEST-COAT</Coating>
          <MaterialGroups>{mat_xml}</MaterialGroups>
          <Operations>{ops_xml}</Operations>
          <GeometryTags>
            <GeometryTag>NegativeRake</GeometryTag>
            <GeometryTag>GeneralPurpose</GeometryTag>
          </GeometryTags>
          <HolderCompatibility>CNMG compatible holders</HolderCompatibility>
          <CoolantCapability>VerifyByCatalog</CoolantCapability>
          <SourcePageReference>p.1</SourcePageReference>
          <Notes>Test record.</Notes>
          {extra_elements}
        </ToolItem>
    """


# ── base_adapter module tests ────────────────────────────────────────────────

class TestBaseAdapterHelpers:
    def test_make_empty_record_has_all_schema_fields(self) -> None:
        record = make_empty_record()
        for field in SCHEMA_FIELDS:
            assert field in record, f"Missing field: {field}"

    def test_make_empty_record_defaults_are_safe(self) -> None:
        record = make_empty_record()
        assert record["cutting_data_status"] == "not_imported"
        assert record["verification_status"] == "sample_family_level_not_catalog_verified"
        assert record["dimensions"] == {}
        assert isinstance(record["material_fit"], list)
        assert isinstance(record["operation_fit"], list)

    def test_field_contains_forbidden_term_detects_feed(self) -> None:
        assert field_contains_forbidden_term("FeedRate") is True
        assert field_contains_forbidden_term("feed_per_tooth") is True

    def test_field_contains_forbidden_term_detects_sfm(self) -> None:
        assert field_contains_forbidden_term("sfm") is True
        assert field_contains_forbidden_term("SFM") is True

    def test_field_contains_forbidden_term_detects_rpm(self) -> None:
        assert field_contains_forbidden_term("RPM") is True
        assert field_contains_forbidden_term("ToolRPM") is True

    def test_field_contains_forbidden_term_detects_cutting_speed(self) -> None:
        assert field_contains_forbidden_term("CuttingSpeed") is True

    def test_field_contains_forbidden_term_safe_fields(self) -> None:
        assert field_contains_forbidden_term("brand") is False
        assert field_contains_forbidden_term("tool_category") is False
        assert field_contains_forbidden_term("CoolantCapability") is False
        assert field_contains_forbidden_term("material_fit") is False
        assert field_contains_forbidden_term("notes") is False
        assert field_contains_forbidden_term("designation") is False

    def test_normalize_material_fit_valid_groups(self) -> None:
        result = normalize_material_fit(["P", "M", "K", "N", "S", "H"])
        assert result == ["P", "M", "K", "N", "S", "H"]

    def test_normalize_material_fit_filters_invalid(self) -> None:
        result = normalize_material_fit(["P", "X", "M", "Z"])
        assert result == ["P", "M"]

    def test_normalize_material_fit_uppercases(self) -> None:
        result = normalize_material_fit(["p", "m"])
        assert result == ["P", "M"]

    def test_normalize_operation_fit_snake_case(self) -> None:
        result = normalize_operation_fit(["External Turning", "Face Milling"])
        assert result == ["external_turning", "face_milling"]

    def test_normalize_geometry_tags_snake_case(self) -> None:
        result = normalize_geometry_tags(["NegativeRake", "80DegreeDiamond"])
        assert result == ["negativerake", "80degreediamond"]

    def test_validate_adapter_output_clean_records(self) -> None:
        record = make_empty_record()
        record["brand"] = "Test"
        record["manufacturer_part_number"] = "TEST-001"
        record["tool_category"] = "turning_insert"
        record["source_label"] = "Test Catalog"
        record["source_url"] = "https://example.com"
        record["verification_status"] = "sample_family_level_not_catalog_verified"
        record["cutting_data_status"] = "not_imported"
        errors = validate_adapter_output([record])
        assert errors == []

    def test_validate_adapter_output_detects_forbidden_key(self) -> None:
        record = make_empty_record()
        record["sfm"] = 400
        errors = validate_adapter_output([record])
        assert any("forbidden" in e.lower() for e in errors)

    def test_validate_adapter_output_detects_wrong_cutting_data_status(self) -> None:
        record = make_empty_record()
        record["cutting_data_status"] = "feeds_imported"
        errors = validate_adapter_output([record])
        assert any("cutting_data_status" in e for e in errors)

    def test_validate_adapter_output_detects_invalid_verification_status(self) -> None:
        record = make_empty_record()
        record["verification_status"] = "made_up_status"
        errors = validate_adapter_output([record])
        assert any("verification_status" in e for e in errors)

    def test_validate_adapter_output_detects_non_list_material_fit(self) -> None:
        record = make_empty_record()
        record["material_fit"] = "P M K"
        errors = validate_adapter_output([record])
        assert any("material_fit" in e for e in errors)


# ── GtcIso13399Adapter unit tests ────────────────────────────────────────────

class TestGtcAdapterParsesInlineXml:
    def setup_method(self) -> None:
        self.adapter = GtcIso13399Adapter()

    def test_parse_single_valid_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 1
        assert self.adapter.rejected_count == 0
        assert self.adapter.parse_errors == []

    def test_parse_sets_brand_from_header(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["brand"] == "Test Manufacturer"

    def test_parse_sets_source_label_from_header(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["source_label"] == "Test Catalog 2025"

    def test_parse_sets_source_url_from_header(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["source_url"] == "https://example.com/test"

    def test_parse_always_sets_not_imported(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert all(r["cutting_data_status"] == "not_imported" for r in records)

    def test_parse_always_sets_valid_verification_status(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        for r in records:
            assert r["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_parse_dimensions_always_empty_dict(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert all(r["dimensions"] == {} for r in records)

    def test_material_fit_normalized_to_iso_groups(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(materials=["P", "M", "K", "X"]))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["material_fit"] == ["P", "M", "K"]

    def test_operation_fit_mapped_to_snake_case(self) -> None:
        xml = _minimal_xml(
            _make_tool_item_xml(operations=["ExternalTurning", "Facing", "Roughing"])
        )
        records = self.adapter.parse_xml_string(xml)
        ops = records[0]["operation_fit"]
        assert "external_turning" in ops
        assert "facing" in ops
        assert "roughing" in ops

    def test_geometry_tags_normalized_to_snake_case(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        for tag in records[0]["geometry_tags"]:
            assert " " not in tag
            assert tag == tag.lower()

    def test_tool_category_turning_insert_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(category="TurningInsert"))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["tool_category"] == "turning_insert"

    def test_tool_category_milling_insert_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(category="MillingInsert"))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["tool_category"] == "milling_insert"

    def test_tool_category_solid_endmill_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(category="SolidEndMill"))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_indexable_drill_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(category="IndexableDrill"))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["tool_category"] == "indexable_drill"

    def test_tool_category_grooving_insert_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(category="GroovingInsert"))
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["tool_category"] == "grooving_insert"

    def test_forbidden_feed_rate_element_rejects_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(extra_elements="<FeedRate>0.15</FeedRate>"))
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 0
        assert self.adapter.rejected_count == 1
        assert any("FeedRate" in e for e in self.adapter.parse_errors)

    def test_forbidden_sfm_element_rejects_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(extra_elements="<SFM>450</SFM>"))
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 0
        assert self.adapter.rejected_count == 1

    def test_forbidden_rpm_element_rejects_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(extra_elements="<RPM>2500</RPM>"))
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 0
        assert self.adapter.rejected_count == 1

    def test_forbidden_cutting_speed_element_rejects_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml(extra_elements="<CuttingSpeed>200</CuttingSpeed>"))
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 0
        assert self.adapter.rejected_count == 1

    def test_clean_record_not_rejected_when_forbidden_record_present(self) -> None:
        clean = _make_tool_item_xml(mpn="CLEAN-001")
        bad = _make_tool_item_xml(mpn="BAD-001", extra_elements="<FeedRate>0.1</FeedRate>")
        xml = _minimal_xml(clean + bad)
        records = self.adapter.parse_xml_string(xml)
        assert len(records) == 1
        assert records[0]["manufacturer_part_number"] == "CLEAN-001"
        assert self.adapter.rejected_count == 1

    def test_missing_tool_items_container_returns_empty(self) -> None:
        xml = dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <GenericToolCatalog version="2.0">
              <CatalogHeader>
                <ManufacturerName>Test</ManufacturerName>
                <CatalogLabel>Test</CatalogLabel>
                <CatalogURL>https://example.com</CatalogURL>
                <IssueDate>2025-01-01</IssueDate>
              </CatalogHeader>
            </GenericToolCatalog>
        """)
        records = self.adapter.parse_xml_string(xml)
        assert records == []
        assert any("ToolItems" in e for e in self.adapter.parse_errors)

    def test_malformed_xml_returns_empty_with_error(self) -> None:
        records = self.adapter.parse_xml_string("<broken xml <<<")
        assert records == []
        assert any("XML parse error" in e for e in self.adapter.parse_errors)

    def test_all_schema_fields_present_in_output(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        for field in SCHEMA_FIELDS:
            assert field in records[0], f"Missing schema field: {field}"

    def test_validate_output_passes_for_clean_record(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        errors = self.adapter.validate_output(records)
        assert errors == []

    def test_no_forbidden_keys_in_output(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        for record in records:
            bad_keys = [k for k in record if field_contains_forbidden_term(str(k))]
            assert bad_keys == [], f"Forbidden keys found: {bad_keys}"

    def test_coolant_capability_verify_by_catalog_mapped(self) -> None:
        xml = _minimal_xml(_make_tool_item_xml())
        records = self.adapter.parse_xml_string(xml)
        assert records[0]["coolant_capability"] == "verify_by_catalog"


# ── Sample file integration tests ────────────────────────────────────────────

class TestSampleFileIntegration:
    def setup_method(self) -> None:
        self.adapter = GtcIso13399Adapter()

    def test_sample_file_exists(self) -> None:
        assert SAMPLE_XML_PATH.exists(), f"Sample XML not found: {SAMPLE_XML_PATH}"

    def test_sample_file_parses(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        assert records is not None

    def test_sample_file_produces_expected_record_count(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        assert len(records) == EXPECTED_RECORD_COUNT

    def test_sample_file_has_no_parse_errors(self) -> None:
        self.adapter.parse(SAMPLE_XML_PATH)
        assert self.adapter.parse_errors == []

    def test_sample_file_has_no_rejections(self) -> None:
        self.adapter.parse(SAMPLE_XML_PATH)
        assert self.adapter.rejected_count == 0

    def test_sample_records_all_have_schema_fields(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for record in records:
            for field in SCHEMA_FIELDS:
                assert field in record, f"Record {record.get('manufacturer_part_number')} missing: {field}"

    def test_sample_records_all_have_not_imported(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        assert all(r["cutting_data_status"] == "not_imported" for r in records)

    def test_sample_records_all_have_valid_verification_status(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            assert r["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_sample_records_dimensions_always_empty(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        assert all(r["dimensions"] == {} for r in records)

    def test_sample_records_brand_is_fixture_manufacturer(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        assert all(r["brand"] == "Fixture Manufacturer Co" for r in records)

    def test_sample_records_material_fit_are_valid_iso_groups(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            for group in r["material_fit"]:
                assert group in ISO_MATERIAL_GROUPS, f"Invalid material group: {group}"

    def test_sample_records_operation_fit_snake_case(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            for op in r["operation_fit"]:
                assert " " not in op, f"Space in operation: {op}"
                assert op == op.lower(), f"Uppercase in operation: {op}"

    def test_sample_records_geometry_tags_snake_case(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            for tag in r["geometry_tags"]:
                assert " " not in tag, f"Space in geometry tag: {tag}"

    def test_sample_records_cover_expected_tool_categories(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        categories = {r["tool_category"] for r in records}
        assert "turning_insert" in categories
        assert "milling_insert" in categories
        assert "endmill" in categories
        assert "indexable_drill" in categories
        assert "grooving_insert" in categories

    def test_sample_records_have_mpn_with_fixture_prefix(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            assert r["manufacturer_part_number"].startswith("FIXTURE-GTC-"), (
                f"MPN does not have FIXTURE-GTC- prefix: {r['manufacturer_part_number']}"
            )

    def test_sample_records_have_no_forbidden_output_keys(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        for r in records:
            bad = [k for k in r if field_contains_forbidden_term(str(k))]
            assert bad == [], f"Forbidden key in {r['manufacturer_part_number']}: {bad}"

    def test_sample_passes_base_adapter_validation(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        errors = self.adapter.validate_output(records)
        assert errors == [], f"Base adapter validation errors: {errors}"

    def test_sample_passes_importer_validation(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        errors = validate_import_rows(records)
        assert errors == [], f"Importer validation errors: {errors}"

    def test_parse_gtc_file_convenience_function(self) -> None:
        result = parse_gtc_file(SAMPLE_XML_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0
        assert result["parse_errors"] == []
        assert result["validation_errors"] == []
        assert len(result["records"]) == EXPECTED_RECORD_COUNT

    def test_sample_output_is_json_serializable(self) -> None:
        records = self.adapter.parse(SAMPLE_XML_PATH)
        dumped = json.dumps(records)
        reloaded = json.loads(dumped)
        assert len(reloaded) == EXPECTED_RECORD_COUNT
