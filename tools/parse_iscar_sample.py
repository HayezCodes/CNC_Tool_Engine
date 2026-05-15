"""Runner script: parse the Iscar sample JSON fixture.

Parses tools/tooling_adapters/samples/sample_iscar_structured.json,
validates the output against the tooling search schema, and writes normalized
JSON records to:

    tools/tooling_adapters/output/iscar_sample_records.json

This script is a demonstration of the adapter pipeline. It does NOT write to
tool_data/tooling_search/records/ — output must go through the audit/review
workflow before records are promoted to the live search index.

Usage::

    python tools/parse_iscar_sample.py
    python tools/parse_iscar_sample.py --dry-run
    python tools/parse_iscar_sample.py --output path/to/custom.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.tooling_adapters.iscar_adapter import parse_iscar_file
from tools.import_tooling_records import validate_import_rows


SAMPLE_JSON = (
    Path(__file__).resolve().parent
    / "tooling_adapters"
    / "samples"
    / "sample_iscar_structured.json"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "tooling_adapters"
    / "output"
    / "iscar_sample_records.json"
)


def run(output_path: Path, dry_run: bool = False) -> int:
    print(f"Source:  {SAMPLE_JSON}")
    print(f"Output:  {output_path}")
    print(f"Mode:    {'dry-run (no file written)' if dry_run else 'write'}")
    print()

    result = parse_iscar_file(SAMPLE_JSON)

    print(f"Records parsed:   {result['record_count']}")
    print(f"Records rejected: {result['rejected_count']}")

    if result["parse_errors"]:
        print()
        print("Parse errors / rejections:")
        for err in result["parse_errors"]:
            print(f"  {err}")

    validation_errors = result["validation_errors"]
    if validation_errors:
        print()
        print("Schema validation errors:")
        for err in validation_errors:
            print(f"  {err}")

    importer_errors = validate_import_rows(result["records"])
    if importer_errors:
        print()
        print("Importer validation errors:")
        for err in importer_errors:
            print(f"  {err}")

    all_keys = {key for record in result["records"] for key in record}
    forbidden_found = [k for k in all_keys if any(
        term in k.lower() for term in ("feed", "speed", "sfm", "rpm", "ipr", "ipm")
    )]
    if forbidden_found:
        print()
        print(f"ERROR: Forbidden keys found in output: {', '.join(sorted(forbidden_found))}")
        return 1

    print()
    print("Records produced:")
    for rec in result["records"]:
        status = rec.get("verification_status", "?")
        cds = rec.get("cutting_data_status", "?")
        print(
            f"  [{rec['tool_category']:22s}] {rec['manufacturer_part_number']:32s} "
            f"  {status} / {cds}"
        )

    all_errors = result["parse_errors"] + validation_errors + importer_errors
    if all_errors:
        print()
        print(f"RESULT: {len(all_errors)} error(s) — output not written.")
        return 1

    if dry_run:
        print()
        print(f"Dry run: {result['record_count']} records would be written to {output_path}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result["records"], indent=2) + "\n",
        encoding="utf-8",
    )
    print()
    print(f"Written: {output_path} ({result['record_count']} records)")
    print()
    print("Next steps:")
    print("  1. Run: python tools/import_iscar_adapter_output.py")
    print("     to import into the live search index.")
    print("  2. Run: python -m tools.audit_tooling_search_records")
    print("     to audit the full records directory.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse the Iscar sample JSON fixture and write normalized JSON output."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output path for normalized JSON records. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize without writing output file.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    return run(Path(args.output), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
