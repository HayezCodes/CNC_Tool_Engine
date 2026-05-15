"""Import Helical Solutions adapter output into the Enterprise Tooling Search index.

Usage::
    python tools/import_helical_solutions_adapter_output.py
    python tools/import_helical_solutions_adapter_output.py --dry-run
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.import_tooling_records import import_tooling_records
from grade_engine.tooling_search import RECORDS_DIR

ADAPTER_OUTPUT = _REPO_ROOT / "tools" / "tooling_adapters" / "output" / "helical_solutions_sample_records.json"
DEFAULT_OUTPUT = RECORDS_DIR / "helical_solutions_imported_tools.json"


def run(output_path: Path, dry_run: bool = False) -> int:
    if not ADAPTER_OUTPUT.exists():
        print(f"ERROR: Adapter output not found: {ADAPTER_OUTPUT}")
        print("Run 'python tools/parse_helical_solutions_sample.py' first.")
        return 1
    result = import_tooling_records(ADAPTER_OUTPUT, output_path=output_path, dry_run=dry_run)
    print(f"Records read:       {result['record_count']}")
    print(f"Records normalized: {result['normalized_record_count']}")
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")
        return 1
    if dry_run:
        print(f"Dry run: {result['record_count']} records would be written to {output_path}")
        return 0
    print(f"Written: {result['output_path']} ({result['normalized_record_count']} records)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(Path(args.output), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
