import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_head(path: str):
    text = subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True, cwd=ROOT)
    return json.loads(text)


def dump(path: str, data) -> None:
    (ROOT / path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def unique(items):
    out = []
    seen = set()
    for item in items:
        if item in (None, ""):
            continue
        key = item if not isinstance(item, list) else tuple(item)
        if isinstance(key, str):
            key = key.upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def norm_groups(groups):
    ordered = []
    for group in groups:
        if group not in ordered:
            ordered.append(group)
    return [group for group in ["P", "M", "K", "N", "S", "H"] if group in ordered]


def ensure_common(row: dict) -> dict:
    row.setdefault("geometry", {})
    row.setdefault("application", {})
    row["application"].setdefault("operations", [])
    row["application"].setdefault("strategy", "")
    row.setdefault("materials", {})
    row["materials"]["iso_groups"] = norm_groups(row["materials"].get("iso_groups", []))
    row.setdefault("recommended_grades", [])
    row["recommended_grades"] = unique(row.get("recommended_grades", []))
    for key in ["source_catalog_id", "source_file"]:
        row.pop(key, None)
    return row


def merge_rows(rows: list[dict], additions: list[dict], key_fields: list[str]) -> list[dict]:
    index = {}
    for i, row in enumerate(rows):
        key = tuple(row.get(field, "") for field in key_fields)
        index[key] = i
    for add in additions:
        ensure_common(add)
        key = tuple(add.get(field, "") for field in key_fields)
        if key in index:
            row = rows[index[key]]
            ensure_common(row)
            row["materials"]["iso_groups"] = norm_groups(row["materials"]["iso_groups"] + add["materials"]["iso_groups"])
            row["recommended_grades"] = unique(row.get("recommended_grades", []) + add.get("recommended_grades", []))
            row["application"]["operations"] = unique(row["application"].get("operations", []) + add["application"].get("operations", []))
            if not row["application"].get("strategy") and add["application"].get("strategy"):
                row["application"]["strategy"] = add["application"]["strategy"]
            for field in ["designation_family", "subcategory", "notes"]:
                if add.get(field) and not row.get(field):
                    row[field] = add[field]
            row["geometry"] = {**add.get("geometry", {}), **row.get("geometry", {})}
        else:
            rows.append(add)
            index[key] = len(rows) - 1
    return rows


turning_additions = [
    {
        "id": "sandvik_coroturn_tr",
        "brand": "Sandvik Coromant",
        "series": "CoroTurn TR",
        "tool_category": "turning_insert",
        "subcategory": "positive_turning_insert",
        "designation_family": "TR",
        "geometry": {"shape_name": "t_rail_copy_turning", "clearance_angle_deg": 7, "chipbreaker": "copy_profile"},
        "application": {"operations": ["profiling", "longitudinal_turning"], "strategy": "copy_turning"},
        "materials": {"iso_groups": ["P", "M", "K", "S"]},
        "recommended_grades": [],
    },
    {
        "id": "sandvik_coroturn_xs",
        "brand": "Sandvik Coromant",
        "series": "CoroTurn XS",
        "tool_category": "turning_insert",
        "subcategory": "small_part_turning_system",
        "designation_family": "XS",
        "geometry": {"shape_name": "small_bore_precision", "chipbreaker": "micro_internal"},
        "application": {"operations": ["profiling", "longitudinal_turning"], "strategy": "small_part_internal"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S"]},
        "recommended_grades": [],
    },
    {
        "id": "sandvik_spectrum_turn",
        "brand": "Sandvik Coromant",
        "series": "Spectrum Turn",
        "tool_category": "turning_insert",
        "subcategory": "general_turning_insert",
        "designation_family": "spectrum_turn",
        "geometry": {"shape_name": "mixed_positive_negative_range"},
        "application": {"operations": ["longitudinal_turning", "facing"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_cn_diamond",
        "brand": "Kyocera",
        "series": "CN 80° Diamond",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "CN□□",
        "geometry": {"shape_name": "80_degree_diamond", "clearance_angle_deg": 0},
        "application": {"operations": ["longitudinal_turning", "facing"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_dn_diamond",
        "brand": "Kyocera",
        "series": "DN 55° Diamond",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "DN□□",
        "geometry": {"shape_name": "55_degree_diamond", "clearance_angle_deg": 0},
        "application": {"operations": ["profiling", "longitudinal_turning"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_kn_parallelogram",
        "brand": "Kyocera",
        "series": "KN 55° Parallelogram",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "KN□□",
        "geometry": {"shape_name": "55_degree_parallelogram", "clearance_angle_deg": 0},
        "application": {"operations": ["profiling", "facing"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_rn_round",
        "brand": "Kyocera",
        "series": "RN Round",
        "tool_category": "turning_insert",
        "subcategory": "round_turning_insert",
        "designation_family": "RN□□",
        "geometry": {"shape_name": "round", "clearance_angle_deg": 0},
        "application": {"operations": ["profiling", "longitudinal_turning"], "strategy": "heavy_roughing"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_sn_square",
        "brand": "Kyocera",
        "series": "SN 90° Square",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "SN□□",
        "geometry": {"shape_name": "90_degree_square", "clearance_angle_deg": 0},
        "application": {"operations": ["facing", "longitudinal_turning"], "strategy": "heavy_roughing"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_tn_triangle",
        "brand": "Kyocera",
        "series": "TN 60° Triangle",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "TN□□",
        "geometry": {"shape_name": "60_degree_triangle", "clearance_angle_deg": 0},
        "application": {"operations": ["profiling", "facing"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_vn_diamond",
        "brand": "Kyocera",
        "series": "VN 35° Diamond",
        "tool_category": "turning_insert",
        "subcategory": "positive_turning_insert",
        "designation_family": "VN□□",
        "geometry": {"shape_name": "35_degree_diamond", "clearance_angle_deg": 7},
        "application": {"operations": ["profiling", "facing"], "strategy": "finishing"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
    {
        "id": "kyocera_wn_trigon",
        "brand": "Kyocera",
        "series": "WN Trigon",
        "tool_category": "turning_insert",
        "subcategory": "negative_turning_insert",
        "designation_family": "WN□□",
        "geometry": {"shape_name": "80_degree_trigon", "clearance_angle_deg": 0},
        "application": {"operations": ["longitudinal_turning", "facing"], "strategy": "general"},
        "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]},
        "recommended_grades": [],
    },
]


solid_additions = [
    {"id": "sandvik_corodrill_860", "brand": "Sandvik Coromant", "series": "CoroDrill 860", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "steel_drilling"}, "materials": {"iso_groups": ["P"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_861", "brand": "Sandvik Coromant", "series": "CoroDrill 861", "tool_category": "solid_drill", "subcategory": "solid_carbide_deep_hole_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "deep_hole"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_862", "brand": "Sandvik Coromant", "series": "CoroDrill 862", "tool_category": "solid_drill", "subcategory": "solid_carbide_micro_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "micro_hole"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_delta_c_840", "brand": "Sandvik Coromant", "series": "CoroDrill Delta-C 840", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "general"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S", "H"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_delta_c_841", "brand": "Sandvik Coromant", "series": "CoroDrill Delta-C 841", "tool_category": "solid_drill", "subcategory": "solid_carbide_thread_prep_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "threaded_holes"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_delta_c_842", "brand": "Sandvik Coromant", "series": "CoroDrill Delta-C 842", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "cast_iron_drilling"}, "materials": {"iso_groups": ["K"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_delta_c_846", "brand": "Sandvik Coromant", "series": "CoroDrill Delta-C 846", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "heat_resistant_alloys"}, "materials": {"iso_groups": ["S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_delta_c_850", "brand": "Sandvik Coromant", "series": "CoroDrill Delta-C 850", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "aluminum_drilling"}, "materials": {"iso_groups": ["N"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_854_856", "brand": "Sandvik Coromant", "series": "CoroDrill 854/856", "tool_category": "solid_drill", "subcategory": "composite_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "composite_drilling"}, "materials": {"iso_groups": ["N"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_452", "brand": "Sandvik Coromant", "series": "CoroDrill 452", "tool_category": "solid_drill", "subcategory": "composite_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "composite_drilling"}, "materials": {"iso_groups": ["N"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_460", "brand": "Sandvik Coromant", "series": "CoroDrill 460", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "general"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_r846", "brand": "Sandvik Coromant", "series": "CoroDrill R846", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "hard_or_hrsa"}, "materials": {"iso_groups": ["S", "H"]}, "recommended_grades": []},
    {"id": "melin_cdr", "brand": "Melin Tool", "series": "CDR", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"point_angle_deg": 140, "coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "general"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "melin_mdr", "brand": "Melin Tool", "series": "MDR", "tool_category": "solid_drill", "subcategory": "solid_carbide_drill", "geometry": {"coolant": "internal"}, "application": {"operations": ["drilling"], "strategy": "micro_hole"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
]


indexable_additions = [
    {"id": "kyocera_drs", "brand": "Kyocera", "series": "DRS", "tool_category": "indexable_drill", "geometry": {"diameter_range_mm": [10.0, 12.5], "l_d": 2, "sleeve": "adjustable"}, "application": {"operations": ["drilling"], "strategy": "indexable_general"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_shem", "brand": "Kyocera", "series": "SHEM", "tool_category": "indexable_drill", "geometry": {"diameter_range_mm": [13.0, 59.0], "l_d": 3}, "application": {"operations": ["drilling"], "strategy": "indexable_general"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_drz", "brand": "Kyocera", "series": "DRZ", "tool_category": "indexable_drill", "geometry": {"diameter_range_mm": [13.0, 59.0], "l_d": 4}, "application": {"operations": ["drilling"], "strategy": "indexable_general"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_she", "brand": "Kyocera", "series": "SHE", "tool_category": "indexable_drill", "geometry": {"diameter_range_mm": [60.0, 999.0], "mount": "cartridge"}, "application": {"operations": ["drilling"], "strategy": "large_diameter"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_870", "brand": "Sandvik Coromant", "series": "CoroDrill 870", "tool_category": "indexable_drill", "geometry": {"tip_style": "exchangeable_tip"}, "application": {"operations": ["drilling"], "strategy": "exchangeable_tip"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_880", "brand": "Sandvik Coromant", "series": "CoroDrill 880", "tool_category": "indexable_drill", "geometry": {"tip_style": "indexable_insert"}, "application": {"operations": ["drilling"], "strategy": "large_diameter"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_800", "brand": "Sandvik Coromant", "series": "CoroDrill 800", "tool_category": "indexable_drill", "geometry": {"tip_style": "indexable_insert_head"}, "application": {"operations": ["drilling"], "strategy": "indexable_general"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_corodrill_801", "brand": "Sandvik Coromant", "series": "CoroDrill 801", "tool_category": "indexable_drill", "geometry": {"tip_style": "asymmetrical_indexable"}, "application": {"operations": ["drilling"], "strategy": "indexable_general"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
]


endmill_additions = [
    {"id": "melin_vbmg2", "brand": "Melin Tool", "series": "VBMG2", "tool_category": "endmill", "geometry": {"flute_count": 2, "tip_style": "spherical_ball"}, "application": {"operations": ["finishing", "profiling"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "N"]}, "recommended_grades": []},
    {"id": "melin_vbmg4", "brand": "Melin Tool", "series": "VBMG4", "tool_category": "endmill", "geometry": {"flute_count": 4, "tip_style": "spherical_ball"}, "application": {"operations": ["finishing", "profiling"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
    {"id": "melin_vbmg_300", "brand": "Melin Tool", "series": "VBMG 300", "tool_category": "endmill", "geometry": {"tip_style": "spherical_ball", "sweep_deg": 300}, "application": {"operations": ["finishing", "profiling"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
    {"id": "melin_vbmg_270", "brand": "Melin Tool", "series": "VBMG 270", "tool_category": "endmill", "geometry": {"tip_style": "spherical_ball", "sweep_deg": 270}, "application": {"operations": ["finishing", "profiling"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "N"]}, "recommended_grades": []},
    {"id": "melin_hxmg2", "brand": "Melin Tool", "series": "HXMG2", "tool_category": "endmill", "geometry": {"flute_count": 2}, "application": {"operations": ["profiling", "slotting"], "strategy": "high_feed"}, "materials": {"iso_groups": ["N", "P"]}, "recommended_grades": []},
    {"id": "melin_hxmg4", "brand": "Melin Tool", "series": "HXMG4", "tool_category": "endmill", "geometry": {"flute_count": 4}, "application": {"operations": ["roughing", "profiling"], "strategy": "high_feed"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_plura_sq", "brand": "Sandvik Coromant", "series": "CoroMill Plura Square Shoulder", "tool_category": "endmill", "geometry": {"construction": "solid_carbide"}, "application": {"operations": ["profiling", "slotting", "shoulder_milling"], "strategy": "square_shoulder"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_plura_ball", "brand": "Sandvik Coromant", "series": "CoroMill Plura Ball Nose", "tool_category": "endmill", "geometry": {"construction": "solid_carbide", "tip_style": "ball_nose"}, "application": {"operations": ["profiling", "finishing"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_plura_thread", "brand": "Sandvik Coromant", "series": "CoroMill Plura Thread Milling", "tool_category": "endmill", "geometry": {"construction": "solid_carbide"}, "application": {"operations": ["thread_milling"], "strategy": "thread_milling"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_316", "brand": "Sandvik Coromant", "series": "CoroMill 316", "tool_category": "endmill", "geometry": {"construction": "exchangeable_solid_carbide_head"}, "application": {"operations": ["profiling", "shoulder_milling"], "strategy": "exchangeable_head"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_ball_nose", "brand": "Sandvik Coromant", "series": "CoroMill Ball Nose", "tool_category": "endmill", "geometry": {"tip_style": "ball_nose"}, "application": {"operations": ["semi_finish", "profiling"], "strategy": "ball_nose"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_ball_nose_finish", "brand": "Sandvik Coromant", "series": "CoroMill Ball Nose Finishing", "tool_category": "endmill", "geometry": {"tip_style": "ball_nose"}, "application": {"operations": ["finishing", "profiling"], "strategy": "ball_nose_finishing"}, "materials": {"iso_groups": ["P", "M", "S", "H"]}, "recommended_grades": []},
]


cutter_additions = [
    {"id": "kyocera_mof45_r", "brand": "Kyocera", "series": "MOF45-R", "tool_category": "indexable_milling_cutter", "subcategory": "45_degree_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling"], "strategy": "45_degree_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mse45", "brand": "Kyocera", "series": "MSE45", "tool_category": "indexable_milling_cutter", "subcategory": "45_degree_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling"], "strategy": "45_degree_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mso45", "brand": "Kyocera", "series": "MSO45", "tool_category": "indexable_milling_cutter", "subcategory": "45_degree_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling", "shoulder_milling"], "strategy": "45_degree_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_msd45_r", "brand": "Kyocera", "series": "MSD45-R", "tool_category": "indexable_milling_cutter", "subcategory": "45_degree_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling"], "strategy": "45_degree_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mec_mecx", "brand": "Kyocera", "series": "MEC / MECX", "tool_category": "indexable_milling_cutter", "subcategory": "shoulder_endmill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["shoulder_milling"], "strategy": "endmill_for_shouldering"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mfb_r", "brand": "Kyocera", "series": "MFB-R", "tool_category": "indexable_milling_cutter", "subcategory": "45_degree_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling"], "strategy": "face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mso90_r", "brand": "Kyocera", "series": "MSO90-R", "tool_category": "indexable_milling_cutter", "subcategory": "90_degree_shoulder_mill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["shoulder_milling", "face_milling"], "strategy": "90_degree_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mte90", "brand": "Kyocera", "series": "MTE90", "tool_category": "indexable_milling_cutter", "subcategory": "90_degree_shoulder_mill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["shoulder_milling", "face_milling"], "strategy": "90_degree_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_msr", "brand": "Kyocera", "series": "MSR", "tool_category": "indexable_milling_cutter", "subcategory": "15_degree_face_mill", "geometry": {"corner_angle_deg": 15}, "application": {"operations": ["face_milling"], "strategy": "15_degree_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_msm", "brand": "Kyocera", "series": "MSM", "tool_category": "indexable_milling_cutter", "subcategory": "0_degree_face_mill", "geometry": {"corner_angle_deg": 0}, "application": {"operations": ["face_milling"], "strategy": "high_feed_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_msp15_mse15", "brand": "Kyocera", "series": "MSP15 / MSE15", "tool_category": "indexable_milling_cutter", "subcategory": "15_degree_shank_mill", "geometry": {"corner_angle_deg": 15}, "application": {"operations": ["face_milling"], "strategy": "15_degree_shank_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mtp90_meal", "brand": "Kyocera", "series": "MTP90 / MEAL", "tool_category": "indexable_milling_cutter", "subcategory": "0_degree_shank_mill", "geometry": {"corner_angle_deg": 0}, "application": {"operations": ["face_milling", "aluminum_milling"], "strategy": "0_degree_shank_mill"}, "materials": {"iso_groups": ["N", "P"]}, "recommended_grades": []},
    {"id": "kyocera_mtps_mtes", "brand": "Kyocera", "series": "MTPS / MTES", "tool_category": "indexable_milling_cutter", "subcategory": "shoulder_endmill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["shoulder_milling"], "strategy": "endmill_for_shouldering"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mhd", "brand": "Kyocera", "series": "MHD", "tool_category": "indexable_milling_cutter", "subcategory": "shoulder_endmill", "geometry": {}, "application": {"operations": ["shoulder_milling"], "strategy": "shouldering"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_dmc", "brand": "Kyocera", "series": "DMC / DMC-H / DMC-SX", "tool_category": "indexable_milling_cutter", "subcategory": "shoulder_endmill", "geometry": {}, "application": {"operations": ["shoulder_milling"], "strategy": "multifunction_endmill"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "kyocera_plus_mill", "brand": "Kyocera", "series": "Plus Mill", "tool_category": "indexable_milling_cutter", "subcategory": "aluminum_endmill", "geometry": {}, "application": {"operations": ["profiling", "shoulder_milling"], "strategy": "aluminum_machining"}, "materials": {"iso_groups": ["N"]}, "recommended_grades": []},
    {"id": "kyocera_mey", "brand": "Kyocera", "series": "MEY", "tool_category": "indexable_milling_cutter", "subcategory": "multifunction_endmill", "geometry": {}, "application": {"operations": ["profiling", "shoulder_milling"], "strategy": "multi_function"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_mez_g", "brand": "Kyocera", "series": "MEZ-G", "tool_category": "indexable_milling_cutter", "subcategory": "multifunction_endmill", "geometry": {}, "application": {"operations": ["profiling", "shoulder_milling"], "strategy": "multi_function"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "kyocera_ultra_drill_mill", "brand": "Kyocera", "series": "Ultra Drill Mill", "tool_category": "indexable_milling_cutter", "subcategory": "drill_mill", "geometry": {}, "application": {"operations": ["ramping", "profiling"], "strategy": "drill_mill"}, "materials": {"iso_groups": ["P", "M", "K", "N"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_490", "brand": "Sandvik Coromant", "series": "CoroMill 490", "tool_category": "indexable_milling_cutter", "subcategory": "small_cutting_depth_shoulder_mill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["shoulder_milling"], "strategy": "small_cutting_depth"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_390", "brand": "Sandvik Coromant", "series": "CoroMill 390", "tool_category": "indexable_milling_cutter", "subcategory": "face_and_shoulder_mill", "geometry": {"corner_angle_deg": 90}, "application": {"operations": ["face_milling", "shoulder_milling"], "strategy": "deep_and_shallow_shoulder"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_290", "brand": "Sandvik Coromant", "series": "CoroMill 290", "tool_category": "indexable_milling_cutter", "subcategory": "roughing_mill", "geometry": {}, "application": {"operations": ["roughing"], "strategy": "roughing"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_century", "brand": "Sandvik Coromant", "series": "CoroMill Century", "tool_category": "indexable_milling_cutter", "subcategory": "high_speed_mill", "geometry": {}, "application": {"operations": ["face_milling", "finishing"], "strategy": "high_speed_machining"}, "materials": {"iso_groups": ["P", "M", "N"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_790", "brand": "Sandvik Coromant", "series": "CoroMill 790", "tool_category": "indexable_milling_cutter", "subcategory": "router", "geometry": {}, "application": {"operations": ["profiling"], "strategy": "non_ferrous_router"}, "materials": {"iso_groups": ["N"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_690", "brand": "Sandvik Coromant", "series": "CoroMill 690", "tool_category": "indexable_milling_cutter", "subcategory": "long_edge_mill", "geometry": {}, "application": {"operations": ["shoulder_milling"], "strategy": "long_edge"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_331", "brand": "Sandvik Coromant", "series": "CoroMill 331", "tool_category": "indexable_milling_cutter", "subcategory": "side_and_face_mill", "geometry": {}, "application": {"operations": ["slotting", "side_milling", "face_milling"], "strategy": "side_and_face"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_329", "brand": "Sandvik Coromant", "series": "CoroMill 329", "tool_category": "indexable_milling_cutter", "subcategory": "slot_mill", "geometry": {}, "application": {"operations": ["slotting"], "strategy": "slot_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_365", "brand": "Sandvik Coromant", "series": "CoroMill 365", "tool_category": "indexable_milling_cutter", "subcategory": "roughing_face_mill", "geometry": {}, "application": {"operations": ["roughing", "face_milling"], "strategy": "cast_iron_and_steel_roughing"}, "materials": {"iso_groups": ["P", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_360", "brand": "Sandvik Coromant", "series": "CoroMill 360", "tool_category": "indexable_milling_cutter", "subcategory": "heavy_duty_face_mill", "geometry": {}, "application": {"operations": ["face_milling"], "strategy": "heavy_duty"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_345", "brand": "Sandvik Coromant", "series": "CoroMill 345", "tool_category": "indexable_milling_cutter", "subcategory": "face_mill", "geometry": {}, "application": {"operations": ["face_milling"], "strategy": "face_milling"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_245", "brand": "Sandvik Coromant", "series": "CoroMill 245", "tool_category": "indexable_milling_cutter", "subcategory": "light_cutting_face_mill", "geometry": {}, "application": {"operations": ["face_milling"], "strategy": "light_cutting"}, "materials": {"iso_groups": ["P", "M", "K", "N"]}, "recommended_grades": []},
    {"id": "sandvik_tmax_45", "brand": "Sandvik Coromant", "series": "T-Max 45", "tool_category": "indexable_milling_cutter", "subcategory": "heavy_duty_face_mill", "geometry": {"corner_angle_deg": 45}, "application": {"operations": ["face_milling"], "strategy": "heavy_duty_face_mill"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_210", "brand": "Sandvik Coromant", "series": "CoroMill 210", "tool_category": "indexable_milling_cutter", "subcategory": "roughing_face_mill", "geometry": {}, "application": {"operations": ["roughing", "face_milling"], "strategy": "high_productive_roughing"}, "materials": {"iso_groups": ["P", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_300", "brand": "Sandvik Coromant", "series": "CoroMill 300", "tool_category": "indexable_milling_cutter", "subcategory": "semi_finishing_mill", "geometry": {}, "application": {"operations": ["semi_finish", "profiling"], "strategy": "light_cutting_semi_finishing"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_200", "brand": "Sandvik Coromant", "series": "CoroMill 200", "tool_category": "indexable_milling_cutter", "subcategory": "roughing_mill", "geometry": {}, "application": {"operations": ["roughing"], "strategy": "roughing"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_357", "brand": "Sandvik Coromant", "series": "CoroMill 357", "tool_category": "indexable_milling_cutter", "subcategory": "face_mill", "geometry": {}, "application": {"operations": ["face_milling"], "strategy": "face_milling"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_419", "brand": "Sandvik Coromant", "series": "CoroMill 419", "tool_category": "indexable_milling_cutter", "subcategory": "face_mill", "geometry": {}, "application": {"operations": ["face_milling"], "strategy": "face_milling"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_coromill_495", "brand": "Sandvik Coromant", "series": "CoroMill 495", "tool_category": "indexable_milling_cutter", "subcategory": "chamfer_mill", "geometry": {}, "application": {"operations": ["chamfer_milling"], "strategy": "chamfer_milling"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
]


grooving_additions = [
    {"id": "sandvik_tlgp", "brand": "Sandvik Coromant", "series": "Top-Lok GP", "tool_category": "grooving_insert", "designation_family": "TLGP", "geometry": {"insert_width_range_inch": [".031", ".250"]}, "application": {"operations": ["grooving"], "strategy": "precision_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": ["1125", "2135", "3020", "H13A"]},
    {"id": "sandvik_tltf", "brand": "Sandvik Coromant", "series": "Top-Lok Fine Pitch", "tool_category": "grooving_insert", "designation_family": "TLTF", "geometry": {"profile": "60_degree_v"}, "application": {"operations": ["grooving", "threading"], "strategy": "fine_pitch_profile"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": ["1125", "2135", "3020", "H13A"]},
    {"id": "sandvik_tltk", "brand": "Sandvik Coromant", "series": "Top-Lok Positive V-Profile", "tool_category": "grooving_insert", "designation_family": "TLTK", "geometry": {"profile": "60_degree_v_positive"}, "application": {"operations": ["grooving", "threading"], "strategy": "v_profile_positive"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": ["1125", "2135", "3020", "H13A"]},
    {"id": "sandvik_bear_paw", "brand": "Sandvik Coromant", "series": "Bear Paw", "tool_category": "grooving_insert", "designation_family": "BP", "geometry": {"insert_width_range_inch": [".500", ".750"]}, "application": {"operations": ["grooving"], "strategy": "heavy_duty_external"}, "materials": {"iso_groups": ["P", "M", "S"]}, "recommended_grades": ["P45", "M35", "S30"]},
    {"id": "sandvik_corocut_1_2", "brand": "Sandvik Coromant", "series": "CoroCut 1-2", "tool_category": "grooving_insert", "designation_family": "CoroCut 1-2", "geometry": {}, "application": {"operations": ["parting", "grooving", "profiling"], "strategy": "general_parting_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corocut_3_edge", "brand": "Sandvik Coromant", "series": "CoroCut 3 edge", "tool_category": "grooving_insert", "designation_family": "CoroCut 3 edge", "geometry": {"cutting_edges": 3}, "application": {"operations": ["grooving"], "strategy": "multi_edge_grooving"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "sandvik_tmax_q_cut", "brand": "Sandvik Coromant", "series": "T-Max Q-Cut", "tool_category": "grooving_insert", "designation_family": "T-Max Q-Cut", "geometry": {}, "application": {"operations": ["parting", "grooving"], "strategy": "heavy_parting"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "sandvik_corocut_qd", "brand": "Sandvik Coromant", "series": "CoroCut QD", "tool_category": "grooving_insert", "designation_family": "CoroCut QD", "geometry": {}, "application": {"operations": ["parting", "grooving"], "strategy": "parting_off"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgba_kgbas", "brand": "Kyocera", "series": "KGBA / KGBAS", "tool_category": "grooving_insert", "designation_family": "KGBA / KGBAS", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgb_kgbs", "brand": "Kyocera", "series": "KGB / KGBS", "tool_category": "grooving_insert", "designation_family": "KGB / KGBS", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ktgf", "brand": "Kyocera", "series": "KTGF-F / KTGF", "tool_category": "grooving_insert", "designation_family": "KTGF-F / KTGF", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_s_ktgf", "brand": "Kyocera", "series": "S-KTGF", "tool_category": "grooving_insert", "designation_family": "S…KTGF", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ktg", "brand": "Kyocera", "series": "KTG", "tool_category": "grooving_insert", "designation_family": "KTG", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgh_kghs", "brand": "Kyocera", "series": "KGH / KGHS", "tool_category": "grooving_insert", "designation_family": "KGH / KGHS", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kga", "brand": "Kyocera", "series": "KGA", "tool_category": "grooving_insert", "designation_family": "KGA", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgm_kgmt", "brand": "Kyocera", "series": "KGM / KGM-T", "tool_category": "grooving_insert", "designation_family": "KGM / KGM-T", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "automatic_lathe_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgmm_kgms", "brand": "Kyocera", "series": "KGMM / KGMS", "tool_category": "grooving_insert", "designation_family": "KGMM / KGMS", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_kgmu", "brand": "Kyocera", "series": "KGMU", "tool_category": "grooving_insert", "designation_family": "KGMU", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_grooving"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ktkh", "brand": "Kyocera", "series": "KTKH", "tool_category": "grooving_insert", "designation_family": "KTKH", "geometry": {}, "application": {"operations": ["parting"], "strategy": "cut_off"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ktkb", "brand": "Kyocera", "series": "KTKB", "tool_category": "grooving_insert", "designation_family": "KTKB", "geometry": {}, "application": {"operations": ["parting"], "strategy": "cut_off"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ktktb", "brand": "Kyocera", "series": "KTKTB / KTKTBF", "tool_category": "grooving_insert", "designation_family": "KTKTB / KTKTBF", "geometry": {}, "application": {"operations": ["parting"], "strategy": "cut_off"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ceracut_cutoff", "brand": "Kyocera", "series": "CERACUT Cut-Off", "tool_category": "grooving_insert", "designation_family": "CERACUT Cut-Off", "geometry": {}, "application": {"operations": ["parting"], "strategy": "cut_off"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "kyocera_ceracut_plunge_turn", "brand": "Kyocera", "series": "CERACUT Plunge & Turn", "tool_category": "grooving_insert", "designation_family": "CERACUT Plunge & Turn", "geometry": {}, "application": {"operations": ["grooving", "profiling"], "strategy": "plunge_turn"}, "materials": {"iso_groups": ["P", "M", "K", "N", "S"]}, "recommended_grades": []},
    {"id": "iscar_heli_grip", "brand": "ISCAR", "series": "HELI-GRIP", "tool_category": "grooving_insert", "designation_family": "HELI-GRIP", "geometry": {}, "application": {"operations": ["grooving"], "strategy": "external_groove_turn"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "iscar_cut_grip", "brand": "ISCAR", "series": "CUT-GRIP", "tool_category": "grooving_insert", "designation_family": "CUT-GRIP", "geometry": {}, "application": {"operations": ["grooving", "parting"], "strategy": "swiss_and_small_lathe"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "iscar_pentacut", "brand": "ISCAR", "series": "PENTACUT", "tool_category": "grooving_insert", "designation_family": "PENTACUT", "geometry": {"cutting_edges": 5}, "application": {"operations": ["grooving", "turning"], "strategy": "multi_edge_groove_turn"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": ["IC830", "IC808"]},
    {"id": "iscar_swisscut", "brand": "ISCAR", "series": "SWISSCUT", "tool_category": "grooving_insert", "designation_family": "SWISSCUT", "geometry": {}, "application": {"operations": ["grooving", "parting"], "strategy": "swiss_type"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "iscar_picco", "brand": "ISCAR", "series": "PICCO", "tool_category": "grooving_insert", "designation_family": "PICCO", "geometry": {"minimum_bore_mm": 0.6}, "application": {"operations": ["grooving", "internal_grooving"], "strategy": "small_bore_internal"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
]


threading_additions = [
    {"id": "sandvik_tmax_u_lock", "brand": "Sandvik Coromant", "series": "T-Max U-Lock", "tool_category": "threading_insert", "designation_family": "T-Max U-Lock", "geometry": {"profile_style": "laydown"}, "application": {"operations": ["internal_threading"], "strategy": "internal_threading"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
    {"id": "sandvik_tmax_twin_lock", "brand": "Sandvik Coromant", "series": "T-Max Twin-Lock", "tool_category": "threading_insert", "designation_family": "T-Max Twin-Lock", "geometry": {"profile_style": "laydown"}, "application": {"operations": ["external_threading", "internal_threading"], "strategy": "oil_pipe_threading"}, "materials": {"iso_groups": ["P", "S"]}, "recommended_grades": []},
    {"id": "kyocera_vnt", "brand": "Kyocera", "series": "VNT", "tool_category": "threading_insert", "designation_family": "VNT", "geometry": {"profile_style": "laydown"}, "application": {"operations": ["external_threading"], "strategy": "general_threading"}, "materials": {"iso_groups": ["P", "M", "K"]}, "recommended_grades": []},
    {"id": "iscar_tipi_partial", "brand": "ISCAR", "series": "TIPI-Partial Profile", "tool_category": "threading_insert", "designation_family": "TIPI", "geometry": {"profile_style": "partial_profile", "minimum_bore_mm": 20.0}, "application": {"operations": ["internal_threading"], "strategy": "partial_profile"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": ["IC08", "IC908"]},
    {"id": "iscar_gepi_partial", "brand": "ISCAR", "series": "GEPI-Partial Profile", "tool_category": "threading_insert", "designation_family": "GEPI", "geometry": {"profile_style": "partial_profile", "minimum_bore_mm": 12.5}, "application": {"operations": ["internal_threading"], "strategy": "partial_profile"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": ["IC08", "IC908"]},
    {"id": "iscar_tip_partial_full", "brand": "ISCAR", "series": "TIP Partial / Full Profile", "tool_category": "threading_insert", "designation_family": "TIP", "geometry": {"profile_style": "partial_or_full_profile", "minimum_bore_mm": 2.4}, "application": {"operations": ["external_threading"], "strategy": "small_part_threading"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": ["IC08", "IC908"]},
    {"id": "iscar_umgr_partial", "brand": "ISCAR", "series": "UMGR Partial Profile 55°/60°", "tool_category": "threading_insert", "designation_family": "UMGR", "geometry": {"profile_style": "partial_profile", "minimum_bore_mm": 5.2}, "application": {"operations": ["internal_threading"], "strategy": "partial_profile"}, "materials": {"iso_groups": ["P", "M", "K", "S"]}, "recommended_grades": []},
]


def main() -> None:
    turning = [ensure_common(row) for row in load_head("tool_data/normalized/turning/inserts.json")]
    solid = [ensure_common(row) for row in load_head("tool_data/normalized/drilling/solid_drills.json")]
    indexable = [ensure_common(row) for row in load_head("tool_data/normalized/drilling/indexable_drills.json")]
    endmills = [ensure_common(row) for row in load_head("tool_data/normalized/milling/endmills.json")]
    cutters = [ensure_common(row) for row in load_head("tool_data/normalized/milling/indexable_cutters.json")]
    grooving = [ensure_common(row) for row in load_head("tool_data/normalized/grooving/inserts.json")]
    threading = [ensure_common(row) for row in load_head("tool_data/normalized/threading/inserts.json")]
    manifest = load_head("tool_data/tool_data_manifest.json")

    turning = merge_rows(turning, turning_additions, ["id"])
    solid = merge_rows(solid, solid_additions, ["id"])
    indexable = merge_rows(indexable, indexable_additions, ["id"])
    endmills = merge_rows(endmills, endmill_additions, ["id"])
    cutters = merge_rows(cutters, cutter_additions, ["id"])
    grooving = merge_rows(grooving, grooving_additions, ["id"])
    threading = merge_rows(threading, threading_additions, ["id"])

    for rows in [turning, solid, indexable, endmills, cutters, grooving, threading]:
        for row in rows:
            ensure_common(row)

    turning.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    solid.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    indexable.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    endmills.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    cutters.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    grooving.sort(key=lambda row: (row["brand"], row["series"], row["id"]))
    threading.sort(key=lambda row: (row["brand"], row["series"], row["id"]))

    manifest["version"] = "2026-05-05"
    manifest["record_counts"]["turning_inserts"] = len(turning)
    manifest["record_counts"]["solid_drills"] = len(solid)
    manifest["record_counts"]["indexable_drills"] = len(indexable)
    manifest["record_counts"]["endmills"] = len(endmills)
    manifest["record_counts"]["indexable_cutters"] = len(cutters)
    manifest["record_counts"]["grooving_inserts"] = len(grooving)
    manifest["record_counts"]["threading_inserts"] = len(threading)
    manifest["record_counts"]["grooving"] = len(grooving)
    manifest["record_counts"]["threading"] = len(threading)
    extra = "Expanded with direct family-level ingestion from attached WIDIA, Sandvik, Kyocera, Melin, Mitsubishi, ISCAR, and Allied catalog PDFs."
    if extra not in manifest.get("notes", []):
        manifest.setdefault("notes", []).append(extra)

    dump("tool_data/normalized/turning/inserts.json", turning)
    dump("tool_data/normalized/drilling/solid_drills.json", solid)
    dump("tool_data/normalized/drilling/indexable_drills.json", indexable)
    dump("tool_data/normalized/milling/endmills.json", endmills)
    dump("tool_data/normalized/milling/indexable_cutters.json", cutters)
    dump("tool_data/normalized/grooving/inserts.json", grooving)
    dump("tool_data/normalized/threading/inserts.json", threading)
    dump("tool_data/tool_data_manifest.json", manifest)

    print(
        json.dumps(
            {
                "turning_inserts": len(turning),
                "solid_drills": len(solid),
                "indexable_drills": len(indexable),
                "endmills": len(endmills),
                "indexable_cutters": len(cutters),
                "grooving_inserts": len(grooving),
                "threading_inserts": len(threading),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
