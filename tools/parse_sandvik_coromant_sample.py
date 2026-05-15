"""Runner: parse the Sandvik Coromant sample JSON fixture.

Usage::
    python tools/parse_sandvik_coromant_sample.py
    python tools/parse_sandvik_coromant_sample.py --dry-run
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.tooling_adapters.sandvik_coromant_adapter import parse_sandvik_coromant_file
from tools.import_tooling_records import validate_import_rows

SAMPLE_JSON = _REPO_ROOT / "tools" / "tooling_adapters" / "samples" / "sample_sandvik_coromant_structured.json"
DEFAULT_OUTPUT = _REPO_ROOT / "tools" / "tooling_adapters" / "output" / "sandvik_coromant_sample_records.json"


def run(output_path: Path, dry_run: bool = False) -> int:
    result = parse_sandvik_coromant_file(SAMPLE_JSON)
    print(f"Records parsed:   {result['record_count']}")
    print(f"Records rejected: {result['rejected_count']}")
    all_errors = result["parse_errors"] + result["validation_errors"] + validate_import_rows(result["records"])
    for err in all_errors:
        print(f"  ERROR: {err}")
    if all_errors:
        return 1
    if dry_run:
        print(f"Dry run: {result['record_count']} records would be written to {output_path}")
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result["records"], indent=2) + "\n", encoding="utf-8")
    print(f"Written: {output_path} ({result['record_count']} records)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(Path(args.output), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
