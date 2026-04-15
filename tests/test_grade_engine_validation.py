import unittest
from urllib.parse import parse_qs, urlparse

from grade_engine.engine import resolve_grade_behavior
from grade_engine.insert_identity import build_insert_identity
from grade_engine.resolver import build_supplier_query, map_behavior_to_supplier_grades


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


if __name__ == "__main__":
    unittest.main()
