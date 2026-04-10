MODIFIER_RULES = {
    "interrupted_cut": {
        "LIGHT": {"toughness": 1, "wear": 0, "coating_bias": "PVD"},
        "HEAVY": {"toughness": 2, "wear": -1, "coating_bias": "PVD"},
    },
    "stickout": {"LONG": {"toughness": 1, "wear": 0, "coating_bias": "PVD"}},
    "workholding": {
        "AVERAGE": {"toughness": 1, "wear": 0, "coating_bias": None},
        "POOR": {"toughness": 2, "wear": -1, "coating_bias": "PVD"},
    },
    "cutting_speed_band": {
        "LOW": {"toughness": 1, "wear": -1, "coating_bias": None},
        "HIGH": {"toughness": -1, "wear": 2, "coating_bias": "CVD"},
    },
    "doc_band": {
        "LIGHT": {"toughness": -1, "wear": 1, "coating_bias": "CVD"},
        "HEAVY": {"toughness": 1, "wear": 0, "coating_bias": None},
    },
    "finish_priority": {"HIGH": {"toughness": -1, "wear": 1, "coating_bias": "CVD"}},
}
