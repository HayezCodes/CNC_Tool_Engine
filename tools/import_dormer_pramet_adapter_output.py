"""Import Dormer Pramet adapter output into the Enterprise Tooling Search index.

Reads:
    tools/tooling_adapters/output/dormer_pramet_sample_records.json

Validates using the standard tooling import workflow, then writes to:
    tool_data/tooling_search/records/dormer_pramet_imported_tools.json

Forbidden feed/speed fields cause the import to abort.
Does NOT promote records to reviewed/ — use tools/review_tooling_records.py.

Usage::

    python tools/import_dormer_pramet_adapter_output.py
    python tools/import_dormer_pramet_adapter_output.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.import_tooling_records import import_tooling_records
from grade_engine.tooling_search import RECORDS_DIR


ADAPTER_OUTPUT = (
    Path(__file__).resolve().parent
    / "tooling_adapters"
    / "output"
    / "dormer_pramet_sample_records.json"
)
DEFAULT_OUTPUT = RECORDS_DIR / "dormer_pramet_imported_tools.json"


def run(output_path: Path, dry_run: bool = False) -> int:
    print(f"Source:  {ADAPTER_OUTPUT}")
    print(f"Output:  {output_path}")
    print(f"Mode:    {'dry-run (no file written)' if dry_run else 'write'}")
    print()

    if not ADAPTER_OUTPUT.exists():
        print(f"ERROR: Adapter output not found: {ADAPTER_OUTPUT}")
        print("Run 'python tools/parse_dormer_pramet_sample.py' first.")
        return 1

    result = import_tooling_records(
        ADAPTER_OUTPUT,
        output_path=output_path,
        dry_run=dry_run,
    )

    print(f"Records read:       {result['record_count']}")
    print(f"Records normalized: {result['normalized_record_count']}")

    if result["errors"]:
        print()
        print("Import errors:")
        for err in result["errors"]:
            print(f"  {err}")
        print()
        print(f"RESULT: {len(result['errors'])} error(s) — no records written.")
        return 1

    if dry_run:
        print()
        print(f"Dry run: {result['record_count']} records would be written to {output_path}")
        return 0

    print()
    print(f"Written: {result['output_path']} ({result['normalized_record_count']} records)")
    print()
    print("Next steps:")
    print("  1. Run: python -m tools.audit_tooling_search_records")
    print("  2. Run: python -m tools.review_tooling_records <path> ...")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Dormer Pramet adapter output into the Enterprise Tooling Search index."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output path for imported JSON records. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, do not write output file.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    return run(Path(args.output), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
