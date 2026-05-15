"""Parse the YG-1 synthetic fixture and write adapter output JSON."""
from __future__ import annotations
import json
from pathlib import Path
from tools.tooling_adapters.yg1_adapter import YG1Adapter

_REPO = Path(__file__).resolve().parent.parent
_SAMPLE = _REPO / "tools" / "tooling_adapters" / "samples" / "sample_yg1_structured.json"
_OUTPUT = _REPO / "tools" / "tooling_adapters" / "output" / "yg1_sample_records.json"


def main() -> None:
    adapter = YG1Adapter()
    records = adapter.parse(_SAMPLE)
    if adapter.parse_errors:
        for e in adapter.parse_errors:
            print(f"  ERROR: {e}")
    if adapter.rejected_count:
        print(f"  Rejected: {adapter.rejected_count}")
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(records)} records → {_OUTPUT}")


if __name__ == "__main__":
    main()
