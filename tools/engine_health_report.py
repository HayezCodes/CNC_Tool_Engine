import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grade_engine.engine import resolve_grade_behavior
from grade_engine.enums import APPLICATION_ZONES, MATERIAL_GROUPS


def make_input(material_group: str, application_zone: str) -> dict[str, str]:
    return {
        "material_group": material_group,
        "application_zone": application_zone,
        "interrupted_cut": "NONE",
        "stickout": "NORMAL",
        "workholding": "GOOD",
        "cutting_speed_band": "NORMAL",
        "doc_band": "MEDIUM",
        "finish_priority": "NORMAL",
    }


def main() -> int:
    total = 0
    passed = 0
    failed: list[str] = []

    for material_group in MATERIAL_GROUPS:
        for application_zone in APPLICATION_ZONES:
            total += 1
            try:
                result = resolve_grade_behavior(make_input(material_group, application_zone))
                if result.get("material_group") == material_group and result.get("application_zone") == application_zone:
                    passed += 1
                else:
                    failed.append(f"{material_group}/{application_zone}: returned mismatched identity fields")
            except Exception as exc:  # pragma: no cover - reporting path only
                failed.append(f"{material_group}/{application_zone}: {exc}")

    print("Engine Health Report")
    print(f"Loaded material groups: {', '.join(MATERIAL_GROUPS)}")
    print(f"Loaded application zones: {', '.join(APPLICATION_ZONES)}")
    print(f"Total tested combinations: {total}")
    print(f"Pass/fail summary: {passed} passed, {len(failed)} failed")
    if failed:
        print("Failures:")
        for item in failed:
            print(f"- {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
