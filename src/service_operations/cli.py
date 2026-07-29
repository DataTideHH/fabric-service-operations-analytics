"""Command-line interface for generation, validation and local Medallion builds."""

from __future__ import annotations

import argparse
from pathlib import Path

from service_operations.generator import DEFAULT_RECORD_COUNT, generate_dataframe, write_dataset
from service_operations.medallion import run_medallion
from service_operations.validation import validate_file, write_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="service-operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate the synthetic CSV fixture.")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--records", type=int, default=DEFAULT_RECORD_COUNT)
    generate.add_argument("--clean", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate CSV data against the contract.")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--contract", type=Path, required=True)
    validate.add_argument("--report", type=Path)
    validate.add_argument("--expect-total", type=int)
    validate.add_argument("--expect-invalid", type=int)

    medallion = subparsers.add_parser(
        "build-medallion",
        help="Build local Bronze, Silver and Gold outputs.",
    )
    medallion.add_argument("--input", type=Path, required=True)
    medallion.add_argument("--contract", type=Path, required=True)
    medallion.add_argument("--output", type=Path, required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "generate":
        dataframe = generate_dataframe(
            record_count=args.records,
            inject_anomalies=not args.clean,
        )
        write_dataset(dataframe, args.output)
        print(f"Wrote {len(dataframe)} synthetic rows to {args.output}")
        return 0

    if args.command == "build-medallion":
        manifest_path = run_medallion(args.input, args.contract, args.output)
        print(f"Wrote reconciled Medallion outputs to {args.output}")
        print(f"manifest={manifest_path}")
        return 0

    result = validate_file(args.input, args.contract)
    if args.report:
        write_report(result, args.report)

    print(f"total_rows={result.total_rows}")
    print(f"valid_rows={result.valid_rows}")
    print(f"invalid_rows={result.invalid_rows}")
    for issue_code, count in result.issue_counts.items():
        print(f"{issue_code}={count}")

    expectations_match = True
    if args.expect_total is not None:
        expectations_match &= result.total_rows == args.expect_total
    if args.expect_invalid is not None:
        expectations_match &= result.invalid_rows == args.expect_invalid

    if args.expect_total is not None or args.expect_invalid is not None:
        return 0 if expectations_match else 1
    return 0 if result.invalid_rows == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
