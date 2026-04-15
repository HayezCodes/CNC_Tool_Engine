from urllib.parse import quote_plus
from .supplier_maps import SUPPLIER_MAPS_V1, GRADE_DESCRIPTIONS

SUPPLIER_SEARCH = {
    "MSC": "https://www.mscdirect.com/browse/tn?searchterm={query}",
    "ISCAR": "https://www.iscar.com/eCatalog/?q={query}",
    "SANDVIK": "https://www.sandvik.coromant.com/en-us/search?text={query}",
    "KENNAMETAL": "https://www.kennametal.com/us/en/search-results.html?q={query}",
}

SUPPLIER_MATERIAL_FAMILIES = {
    "ISCAR": {
        "P": "steel",
        "M": "stainless",
        "K": "cast iron",
        "N": "aluminum non-ferrous polished",
        "S": "super alloy",
        "H": "hardened steel",
    },
    "SANDVIK": {
        "P": "steel",
        "M": "stainless",
        "K": "cast iron",
        "N": "non-ferrous aluminum polished",
        "S": "HRSA super alloy",
        "H": "hardened steel CBN",
    },
    "KYOCERA": {
        "P": "steel",
        "M": "stainless",
        "K": "cast iron",
        "N": "aluminum non-ferrous",
        "S": "super alloy",
        "H": "hardened steel",
    },
    "KENNAMETAL": {
        "P": "steel",
        "M": "stainless",
        "K": "cast iron",
        "N": "aluminum polished",
        "S": "super alloy",
        "H": "hardened steel",
    },
    "MSC": {
        "P": "ISO P steel",
        "M": "ISO M stainless",
        "K": "ISO K cast iron",
        "N": "ISO N polished aluminum non-ferrous",
        "S": "ISO S super alloy",
        "H": "ISO H hardened steel",
    },
}

# MSC bucket grades are internal placeholders in this app, so search with ISO-class aliases
# instead of the placeholder key to keep the catalog query stable and human-readable.
MSC_GRADE_SEARCH_ALIASES = {
    "MSC_ISO_P30": "ISO P30",
    "MSC_ISO_P25": "ISO P25",
    "MSC_ISO_P20": "ISO P20",
    "MSC_ISO_P15": "ISO P15",
    "MSC_ISO_M30": "ISO M30",
    "MSC_ISO_M25": "ISO M25",
    "MSC_ISO_M20": "ISO M20",
    "MSC_ISO_M15": "ISO M15",
    "MSC_ISO_K30": "ISO K30",
    "MSC_ISO_K25": "ISO K25",
    "MSC_ISO_K20": "ISO K20",
    "MSC_ISO_K15": "ISO K15",
    "MSC_ISO_N20": "ISO N20",
    "MSC_ISO_N10": "ISO N10",
    "MSC_ISO_N05": "ISO N05",
    "MSC_ISO_S30": "ISO S30",
    "MSC_ISO_S25": "ISO S25",
    "MSC_ISO_S20": "ISO S20",
    "MSC_ISO_S15": "ISO S15",
    "MSC_ISO_H20": "ISO H20",
    "MSC_ISO_H15": "ISO H15",
    "MSC_ISO_H10": "ISO H10",
}

GENERIC_CHIPBREAKER_TERMS = {"GENERAL", "GENERAL-PURPOSE", "GENERALPURPOSE", "FAMILY"}

def normalize_insert_code(geometry: str) -> str:
    geo = (geometry or "").upper().strip()
    if not geo:
        return "CNMG"
    for code in ["DNMG","CNMG","VNMG","WNMG","SNMG"]:
        if code in geo:
            return code
    return geo.split()[0]

def normalize_chipbreaker_family(chipbreaker: str) -> str:
    text = (chipbreaker or "").upper().strip()
    if not text:
        return ""
    compact = text.replace(" ", "")
    if any(term in compact for term in GENERIC_CHIPBREAKER_TERMS):
        return ""
    for code in ["MRR","MR","MF","MN","MP","SM","SF","TF","QM","MM","XM"]:
        if code in text:
            return code
    return ""

def get_material_word(material_group: str) -> str:
    return {
        "P":"steel","M":"stainless","K":"cast iron","N":"aluminum","S":"super alloy","H":"hardened steel"
    }.get(material_group, "turning")

def get_supplier_grade_search_term(supplier: str, grade: str) -> str:
    if supplier == "MSC":
        return MSC_GRADE_SEARCH_ALIASES.get(grade, grade)
    return grade

def compact_query_tokens(*tokens: str) -> str:
    cleaned = []
    seen = set()
    for token in tokens:
        value = " ".join((token or "").split()).strip()
        if not value:
            continue
        key = value.upper()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return " ".join(cleaned)

def build_supplier_query(supplier: str, material_group: str, grade: str, geometry: str, chipbreaker: str, insert_identity: dict = None):
    identity = insert_identity or {}
    insert_code = identity.get("shape") or normalize_insert_code(geometry)
    breaker = normalize_chipbreaker_family(chipbreaker)
    material_word = get_material_word(material_group)
    family_hint = SUPPLIER_MATERIAL_FAMILIES.get(supplier, {}).get(material_group, material_word)
    size = identity.get("ansi_size", "432")
    grade_term = get_supplier_grade_search_term(supplier, grade)

    if supplier == "MSC":
        return compact_query_tokens(insert_code, size, breaker, grade_term, family_hint, "turning insert")
    if supplier == "SANDVIK":
        return compact_query_tokens(grade_term, insert_code, size, breaker, family_hint, "turning insert")
    if supplier == "KYOCERA":
        return compact_query_tokens(grade_term, insert_code, size, breaker, family_hint, "turning insert")
    if supplier == "KENNAMETAL":
        return compact_query_tokens(grade_term, insert_code, size, breaker, family_hint, "turning insert")
    if supplier == "ISCAR":
        return compact_query_tokens(grade_term, insert_code, size, breaker, family_hint, "turning insert")
    return compact_query_tokens(grade_term, insert_code, size, breaker, material_word, "turning insert")

def build_supplier_links(supplier, material_group, grade, geometry, chipbreaker, insert_identity: dict = None):
    query = build_supplier_query(supplier, material_group, grade, geometry, chipbreaker, insert_identity)
    search_url = SUPPLIER_SEARCH.get(supplier, "").format(query=quote_plus(query))
    if search_url:
        return {"Search": search_url}
    return {}

def map_behavior_to_supplier_grades(material_group: str, application_zone: str, preferred_coating: str, geometry_hint: dict, chipbreaker_hint: dict, insert_identity: dict = None) -> dict:
    if material_group not in ["P","M","K","N","S","H"]:
        return {
            "SYSTEM": {
                "recommended_grade": "Behavior engine live",
                "fallback_grade": "Supplier mapping coming next",
                "preferred_coating": preferred_coating,
                "description": "Material group added to the behavior engine. Supplier-grade mapping for this group still needs tuned tables.",
                "links": {},
            }
        }

    output = {}
    for supplier, supplier_map in SUPPLIER_MAPS_V1.items():
        zone_map = supplier_map.get(material_group, {}).get(application_zone)
        if not zone_map:
            continue
        recommended = zone_map["alt_by_coating"].get(preferred_coating, zone_map["primary"])
        search_query = build_supplier_query(
            supplier,
            material_group,
            recommended,
            geometry_hint.get("geometry", "CNMG"),
            chipbreaker_hint.get("family", "MR"),
            insert_identity,
        )
        output[supplier] = {
            "recommended_grade": recommended,
            "fallback_grade": zone_map["primary"],
            "preferred_coating": preferred_coating,
            "description": GRADE_DESCRIPTIONS.get(recommended, ""),
            "search_query": search_query,
            "links": build_supplier_links(
                supplier,
                material_group,
                recommended,
                geometry_hint.get("geometry", "CNMG"),
                chipbreaker_hint.get("family", "MR"),
                insert_identity,
            ),
        }
    return output
