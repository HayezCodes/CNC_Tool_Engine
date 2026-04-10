import unittest
from urllib.parse import parse_qs, urlparse

from grade_engine.engine import resolve_grade_behavior
from grade_engine.insert_identity import build_insert_identity
from grade_engine.resolver import build_supplier_query, map_behavior_to_supplier_grades
from grade_engine.router import get_tool_family_message
from grade_engine.tooling_advisor import resolve_tooling_recommendation

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None


def decode_search_query(url: str) -> str:
    params = parse_qs(urlparse(url).query)
    for key in ("q", "text", "searchterm"):
        if key in params and params[key]:
            return params[key][0]
    return ""


class BehaviorResolutionTests(unittest.TestCase):
    def test_steel_roughing_bias_stays_tough(self):
        result = resolve_grade_behavior(
            {
                "material_group": "P",
                "application_zone": "TOUGH",
                "interrupted_cut": "LIGHT",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "HEAVY",
                "finish_priority": "LOW",
            }
        )

        self.assertEqual(result["required_toughness"], "HIGH")
        self.assertEqual(result["preferred_coating"], "PVD")
        self.assertEqual(result["insert_identity"]["shape"], "CNMG")

    def test_stainless_finishing_stays_finish_oriented(self):
        result = resolve_grade_behavior(
            {
                "material_group": "M",
                "application_zone": "WEAR",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "LIGHT",
                "finish_priority": "HIGH",
            }
        )

        self.assertEqual(result["required_wear_resistance"], "HIGH")
        self.assertEqual(result["preferred_coating"], "CVD")
        self.assertEqual(result["insert_identity"]["shape"], "VNMG")


class InsertIdentityTests(unittest.TestCase):
    def test_insert_identity_changes_with_roughing_vs_finishing(self):
        roughing = build_insert_identity(
            {
                "application_zone": "TOUGH",
                "finish_priority": "LOW",
                "doc_band": "HEAVY",
                "interrupted_cut": "HEAVY",
                "workholding": "GOOD",
            },
            {"geometry": "DNMG / CNMG type direction"},
            {"family": "MR / MRR style"},
        )
        finishing = build_insert_identity(
            {
                "application_zone": "WEAR",
                "finish_priority": "HIGH",
                "doc_band": "LIGHT",
                "interrupted_cut": "NONE",
                "workholding": "GOOD",
            },
            {"geometry": "VNMG / sharper finishing direction"},
            {"family": "MF finishing style"},
        )

        self.assertEqual(roughing["shape"], "CNMG")
        self.assertEqual(roughing["ansi_size"], "433")
        self.assertEqual(roughing["nose_radius"], "large")
        self.assertEqual(finishing["shape"], "VNMG")
        self.assertEqual(finishing["ansi_size"], "431")
        self.assertEqual(finishing["nose_radius"], "small")

    def test_insert_identity_uses_dnmg_for_balanced_unstable_work(self):
        balanced_unstable = build_insert_identity(
            {
                "application_zone": "BALANCED",
                "finish_priority": "NORMAL",
                "doc_band": "MEDIUM",
                "interrupted_cut": "LIGHT",
                "workholding": "AVERAGE",
            },
            {"geometry": "DNMG as a broad starting point"},
            {"family": "MR / MF style"},
        )

        self.assertEqual(balanced_unstable["shape"], "DNMG")
        self.assertEqual(balanced_unstable["ansi_size"], "432")
        self.assertEqual(balanced_unstable["nose_radius"], "medium")


class SupplierQueryTests(unittest.TestCase):
    def test_supplier_queries_keep_grade_context_and_drop_generic_breakers(self):
        query = build_supplier_query(
            "KENNAMETAL",
            "P",
            "KCP25C",
            "VNMG / sharper finishing direction",
            "MF finishing style",
            {"shape": "VNMG", "ansi_size": "431"},
        )

        self.assertIn("KCP25C", query)
        self.assertIn("steel", query.lower())
        self.assertNotIn("GENERAL-PURPOSE", query)

    def test_msc_queries_use_iso_bucket_aliases_not_internal_keys(self):
        query = build_supplier_query(
            "MSC",
            "N",
            "MSC_ISO_N05",
            "VNMG / sharper finishing direction",
            "General-purpose family",
            {"shape": "VNMG", "ansi_size": "431"},
        )

        self.assertIn("ISO N05", query)
        self.assertNotIn("MSC_ISO_", query)
        self.assertNotIn("GENERAL-PURPOSE", query)

    def test_mapping_exposes_search_query_and_link_match(self):
        result = resolve_grade_behavior(
            {
                "material_group": "K",
                "application_zone": "TOUGH",
                "interrupted_cut": "NONE",
                "stickout": "SHORT",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "HEAVY",
                "finish_priority": "LOW",
            }
        )
        matches = map_behavior_to_supplier_grades(
            result["material_group"],
            result["application_zone"],
            result["preferred_coating"],
            result["geometry_hint"],
            result["chipbreaker_hint"],
            result["insert_identity"],
        )

        self.assertIn("SANDVIK", matches)
        sandvik = matches["SANDVIK"]
        self.assertIn("search_query", sandvik)
        self.assertEqual(list(sandvik["links"].keys()), ["Search"])
        decoded_query = decode_search_query(sandvik["links"]["Search"])
        self.assertEqual(decoded_query, sandvik["search_query"])
        self.assertNotIn("GENERAL-PURPOSE", decoded_query)

    def test_kennametal_links_use_live_search_path(self):
        result = resolve_grade_behavior(
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            }
        )
        matches = map_behavior_to_supplier_grades(
            result["material_group"],
            result["application_zone"],
            result["preferred_coating"],
            result["geometry_hint"],
            result["chipbreaker_hint"],
            result["insert_identity"],
        )

        kennametal_link = matches["KENNAMETAL"]["links"]["Search"]
        self.assertIn("bing.com/search", kennametal_link)
        self.assertIn("site%3Awww.kennametal.com%2Fus%2Fen%2Fproducts", kennametal_link)

    def test_msc_and_iscar_links_use_live_search_paths(self):
        result = resolve_grade_behavior(
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            }
        )
        matches = map_behavior_to_supplier_grades(
            result["material_group"],
            result["application_zone"],
            result["preferred_coating"],
            result["geometry_hint"],
            result["chipbreaker_hint"],
            result["insert_identity"],
        )

        msc_link = matches["MSC"]["links"]["Search"]
        iscar_link = matches["ISCAR"]["links"]["Search"]
        self.assertIn("bing.com/search", msc_link)
        self.assertIn("site%3Awww.mscdirect.com", msc_link)
        self.assertIn("bing.com/search", iscar_link)
        self.assertIn("site%3Awww.iscar.com%2FeCatalog", iscar_link)

    def test_pvd_sandvik_mappings_keep_non_empty_description(self):
        result = resolve_grade_behavior(
            {
                "material_group": "M",
                "application_zone": "BALANCED",
                "interrupted_cut": "HEAVY",
                "stickout": "LONG",
                "workholding": "POOR",
                "cutting_speed_band": "LOW",
                "doc_band": "HEAVY",
                "finish_priority": "LOW",
            }
        )
        self.assertEqual(result["preferred_coating"], "PVD")
        matches = map_behavior_to_supplier_grades(
            result["material_group"],
            result["application_zone"],
            result["preferred_coating"],
            result["geometry_hint"],
            result["chipbreaker_hint"],
            result["insert_identity"],
        )

        self.assertEqual(matches["SANDVIK"]["recommended_grade"], "GC1115")
        self.assertTrue(matches["SANDVIK"]["description"])


class ToolFamilyCoverageTests(unittest.TestCase):
    def test_every_family_resolves_to_live_message(self):
        for tool_family in (
            "TURNING_INSERT",
            "GROOVING_INSERT",
            "THREADING_INSERT",
            "DRILL",
            "ENDMILL",
            "FACE_MILL",
            "TAP",
            "REAMER",
        ):
            message = get_tool_family_message(tool_family)
            self.assertEqual(message["status"], "LIVE")

    def test_every_family_returns_supplier_search(self):
        input_data = {
            "material_group": "P",
            "application_zone": "BALANCED",
            "interrupted_cut": "NONE",
            "stickout": "NORMAL",
            "workholding": "GOOD",
            "cutting_speed_band": "NORMAL",
            "doc_band": "MEDIUM",
            "finish_priority": "NORMAL",
        }
        for tool_family in (
            "TURNING_INSERT",
            "GROOVING_INSERT",
            "THREADING_INSERT",
            "DRILL",
            "ENDMILL",
            "FACE_MILL",
            "TAP",
            "REAMER",
        ):
            recommendation = resolve_tooling_recommendation(tool_family, input_data)
            self.assertTrue(recommendation["starter_platform"])
            self.assertTrue(recommendation["geometry_focus"])
            self.assertTrue(recommendation["holder_focus"])
            self.assertGreater(len(recommendation["supplier_matches"]), 0)
            for supplier_data in recommendation["supplier_matches"].values():
                self.assertTrue(supplier_data["description"])
                self.assertIn("Search", supplier_data["links"])
                self.assertTrue(decode_search_query(supplier_data["links"]["Search"]))
                self.assertNotIn("coming next", supplier_data["description"].lower())
                self.assertNotIn("placeholder", supplier_data["description"].lower())

    def test_cast_iron_drill_does_not_use_polished_aluminum_point(self):
        recommendation = resolve_tooling_recommendation(
            "DRILL",
            {
                "material_group": "K",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        self.assertIn("strong-margin", recommendation["geometry_focus"].lower())
        self.assertNotIn("polished", recommendation["geometry_focus"].lower())

    def test_stable_unified_threading_can_promote_full_profile_insert(self):
        recommendation = resolve_tooling_recommendation(
            "THREADING_INSERT",
            {
                "material_group": "P",
                "application_zone": "WEAR",
                "interrupted_cut": "NONE",
                "stickout": "SHORT",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "LIGHT",
                "finish_priority": "HIGH",
                "thread_profile": "UNIFIED_60",
                "thread_side": "EXTERNAL",
            },
        )

        starter_text = recommendation["starter_platform"].lower()
        search_text = " ".join(
            supplier_data["search_query"].lower()
            for supplier_data in recommendation["supplier_matches"].values()
        )
        self.assertIn("full-profile", starter_text)
        self.assertIn("full profile", search_text)

    def test_non_ferrous_tap_watchouts_stay_material_relevant(self):
        recommendation = resolve_tooling_recommendation(
            "TAP",
            {
                "material_group": "N",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        watch_text = " ".join(recommendation["watch_items"]).lower()
        notes_text = " ".join(recommendation["process_notes"]).lower()
        self.assertIn("form tap", recommendation["starter_platform"].lower())
        self.assertIn("ductile aluminum", notes_text)
        self.assertNotIn("super alloy", watch_text)

    def test_through_hole_steel_tap_uses_spiral_point_path(self):
        recommendation = resolve_tooling_recommendation(
            "TAP",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
                "hole_type": "THROUGH",
            },
        )

        starter_text = recommendation["starter_platform"].lower()
        search_text = " ".join(
            supplier_data["search_query"].lower()
            for supplier_data in recommendation["supplier_matches"].values()
        )
        self.assertIn("spiral-point gun tap", starter_text)
        self.assertIn("through hole", search_text)
        self.assertNotIn("blind hole", search_text)

    def test_non_turning_supplier_queries_drop_turning_grade_jargon(self):
        recommendation = resolve_tooling_recommendation(
            "DRILL",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("drill", search_query)
            self.assertNotIn("cvd", search_query)
            self.assertNotIn("pvd", search_query)

    def test_non_turning_supplier_queries_collapse_overlapping_family_terms(self):
        drill = resolve_tooling_recommendation(
            "DRILL",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )
        grooving = resolve_tooling_recommendation(
            "GROOVING_INSERT",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        self.assertEqual(drill["supplier_matches"]["SANDVIK"]["search_query"].lower().count("carbide drill"), 1)
        self.assertEqual(grooving["supplier_matches"]["SANDVIK"]["search_query"].lower().count("grooving insert"), 1)

    def test_tap_supplier_queries_include_hole_style_not_coating(self):
        recommendation = resolve_tooling_recommendation(
            "TAP",
            {
                "material_group": "M",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
                "hole_type": "BLIND",
            },
        )

        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("spiral-flute tap", search_query)
            self.assertIn("blind hole", search_query)
            self.assertNotIn("cvd", search_query)
            self.assertNotIn("pvd", search_query)

    def test_threading_insert_supplier_queries_stay_thread_specific(self):
        recommendation = resolve_tooling_recommendation(
            "THREADING_INSERT",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("threading insert", search_query)
            self.assertIn("laydown", search_query)
            self.assertEqual(search_query.count("threading insert"), 1)
            self.assertNotIn("cvd", search_query)
            self.assertNotIn("pvd", search_query)

    def test_threading_insert_internal_whitworth_search_stays_specific(self):
        recommendation = resolve_tooling_recommendation(
            "THREADING_INSERT",
            {
                "material_group": "M",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
                "thread_profile": "WHITWORTH_55",
                "thread_side": "INTERNAL",
            },
        )

        self.assertIn("55 degree internal threading style", recommendation["geometry_focus"].lower())
        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("55 degree", search_query)
            self.assertIn("internal", search_query)

    def test_face_mill_supplier_queries_stay_family_specific(self):
        recommendation = resolve_tooling_recommendation(
            "FACE_MILL",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("face mill", search_query)
            self.assertEqual(search_query.count("face mill"), 1)
            self.assertNotIn("turning insert", search_query)

    def test_reamer_supplier_queries_stay_family_specific(self):
        recommendation = resolve_tooling_recommendation(
            "REAMER",
            {
                "material_group": "M",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
            },
        )

        for supplier_data in recommendation["supplier_matches"].values():
            search_query = supplier_data["search_query"].lower()
            self.assertIn("reamer", search_query)
            self.assertNotIn("turning insert", search_query)
            self.assertNotIn("cvd", search_query)
            self.assertNotIn("pvd", search_query)

    def test_blind_hole_reamer_uses_spiral_geometry(self):
        recommendation = resolve_tooling_recommendation(
            "REAMER",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
                "hole_type": "BLIND",
            },
        )

        self.assertIn("right-hand spiral", recommendation["geometry_focus"].lower())

    def test_hardened_material_reamer_prefers_carbide_platform(self):
        recommendation = resolve_tooling_recommendation(
            "REAMER",
            {
                "material_group": "H",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "MEDIUM",
                "finish_priority": "NORMAL",
                "hole_type": "THROUGH",
            },
        )

        self.assertIn("solid carbide", recommendation["starter_platform"].lower())

    def test_non_ferrous_endmill_keeps_polished_aluminum_bias(self):
        recommendation = resolve_tooling_recommendation(
            "ENDMILL",
            {
                "material_group": "N",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "LIGHT",
                "finish_priority": "HIGH",
            },
        )

        starter_text = recommendation["starter_platform"].lower()
        summary_text = recommendation["behavior"]["recommendation_summary"].lower()
        self.assertIn("polished carbide endmill", starter_text)
        self.assertIn("non-ferrous", summary_text)
        self.assertTrue(
            all("blind hole" in supplier_data["search_query"].lower() for supplier_data in recommendation["supplier_matches"].values())
        )

    def test_non_turning_watch_items_keep_setup_risk_flags(self):
        recommendation = resolve_tooling_recommendation(
            "ENDMILL",
            {
                "material_group": "P",
                "application_zone": "BALANCED",
                "interrupted_cut": "HEAVY",
                "stickout": "LONG",
                "workholding": "POOR",
                "cutting_speed_band": "HIGH",
                "doc_band": "HEAVY",
                "finish_priority": "LOW",
            },
        )

        watch_text = " ".join(recommendation["watch_items"]).lower()
        notes_text = " ".join(recommendation["process_notes"]).lower()
        self.assertIn("high edge-chipping risk", watch_text)
        self.assertIn("deflection / chatter risk", watch_text)
        self.assertIn("poor workholding", notes_text)

    def test_light_doc_stainless_warning_stays_broadly_accurate(self):
        recommendation = resolve_tooling_recommendation(
            "TURNING_INSERT",
            {
                "material_group": "M",
                "application_zone": "BALANCED",
                "interrupted_cut": "NONE",
                "stickout": "NORMAL",
                "workholding": "GOOD",
                "cutting_speed_band": "NORMAL",
                "doc_band": "LIGHT",
                "finish_priority": "NORMAL",
            },
        )

        watch_text = " ".join(recommendation["watch_items"]).lower()
        self.assertIn("light-doc stainless cut", watch_text)
        self.assertNotIn("finishing cut", watch_text)


@unittest.skipIf(AppTest is None, "streamlit testing support unavailable")
class AppStartupTests(unittest.TestCase):
    def test_app_renders_and_builds_recommendation(self):
        app = AppTest.from_file("app.py")
        app.run()
        self.assertEqual(app.title[0].value, "CNC Tool Engine")
        self.assertEqual(len(app.button), 0)
        self.assertTrue(any(header.value == "Recommendation" for header in app.subheader))
        self.assertTrue(any(header.value == "Supplier Search" for header in app.subheader))

    def test_internal_logic_toggle_renders_key(self):
        app = AppTest.from_file("app.py")
        app.run()
        app.checkbox[0].check()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(caption.value == "Internal logic key" for caption in app.caption))
        self.assertTrue(any("grade_behavior_key" not in code.value and "_T_" in code.value for code in app.code))

    def test_every_family_builds_without_ui_exceptions(self):
        for tool_family in (
            "TURNING_INSERT",
            "GROOVING_INSERT",
            "THREADING_INSERT",
            "DRILL",
            "ENDMILL",
            "FACE_MILL",
            "TAP",
            "REAMER",
        ):
            app = AppTest.from_file("app.py")
            app.run()
            app.selectbox[0].set_value(tool_family)
            app.run()

            self.assertEqual(len(app.exception), 0, msg=f"{tool_family} raised a Streamlit exception")
            self.assertTrue(any(header.value == "Recommendation" for header in app.subheader))
            self.assertTrue(any(header.value == "Supplier Search" for header in app.subheader))


if __name__ == "__main__":
    unittest.main()
