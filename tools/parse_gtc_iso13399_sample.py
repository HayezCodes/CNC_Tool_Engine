"""Runner script: parse the sample GTC/ISO 13399 XML fixture.

Parses tools/tooling_adapters/samples/sample_gtc_iso13399.xml, validates the
output against the tooling search schema, and writes normalized JSON records to:

    tools/tooling_adapters/output/sample_gtc_iso13399_records.json

This script is a demonstration of the adapter pipeline. It does NOT write to
tool_data/tooling_search/records/ — output must go through the audit/review
workflow before records are promoted to the live search index.

Usage::

    python tools/parse_gtc_iso13399_sample.py
    python tools/parse_gtc_iso13399_sample.py --dry-run
    python tools/parse_gtc_iso13399_sample.py --output path/to/custom.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.tooling_adapters.gtc_iso13399_adapter import parse_gtc_file
from tools.import_tooling_records import validate_import_rows


SAMPLE_XML = Path(__file__).resolve().parent / "tooling_adapters" / "samples" / "sample_gtc_iso13399.xml"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "tooling_adapters" / "output" / "sample_gtc_iso13399_records.json"


def run(output_path: Path, dry_run: bool = False) -> int:
    print(f"Source:  {SAMPLE_XML}")
    print(f"Output:  {output_path}")
    print(f"Mode:    {'dry-run (no file written)' if dry_run else 'write'}")
    print()

    # ── Parse ─────────────────────────────────────────────────────────────────
    result = parse_gtc_file(SAMPLE_XML)

    print(f"Records parsed:  {result['record_count']}")
    print(f"Records rejected: {result['rejected_count']}")

    if result["parse_errors"]:
        print()
        print("Parse errors / rejections:")
        for err in result["parse_errors"]:
            print(f"  {err}")

    # ── Schema validation (base adapter) ─────────────────────────────────────
    validation_errors = result["validation_errors"]
    if validation_errors:
        print()
        print("Schema validation errors:")
        for err in validation_errors:
            print(f"  {err}")

    # ── Importer validation (existing import workflow) ─────────────────────
    importer_errors = validate_import_rows(result["records"])
    if importer_errors:
        print()
        print("Importer validation errors:")
        for err in importer_errors:
            print(f"  {err}")

    # ── Feed/speed guard ───────────────────────────────────────────────────
    all_keys = {key for record in result["records"] for key in record}
    forbidden_found = [k for k in all_keys if any(
        term in k.lower() for term in ("feed", "speed", "sfm", "rpm", "ipr", "ipm")
    )]
    if forbidden_found:
        print()
        print(f"ERROR: Forbidden keys found in output: {', '.join(sorted(forbidden_found))}")
        return 1

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("Records produced:")
    for rec in result["records"]:
        status = rec.get("verification_status", "?")
        cds = rec.get("cutting_data_status", "?")
        print(
            f"  [{rec['tool_category']:20s}] {rec['manufacturer_part_number']:30s} "
            f"  {status} / {cds}"
        )

    all_errors = result["parse_errors"] + validation_errors + importer_errors
    if all_errors:
        print()
        print(f"RESULT: {len(all_errors)} error(s) — output not written.")
        return 1

    # ── Write output ───────────────────────────────────────────────────────
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
    print("  1. Run: python tools/audit_tooling_search_records.py")
    print("     to audit before promoting to records/")
    print("  2. Run: python tools/review_tooling_records.py")
    print("     to batch-review and promote to records/reviewed/")
    print("  3. Copy promoted records to tool_data/tooling_search/records/")
    print("     only after audit and review are clean.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse the GTC/ISO 13399 sample XML fixture and write normalized JSON output."
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
