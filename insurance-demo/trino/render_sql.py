#!/usr/bin/env python3
"""Render Trino SQL templates with environment variable placeholders."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULTS = {
    "CATALOG": "hive",
    "DATABASE": "insurance_leo_trino",
    "RAW_BASE": "s3a://lhdemocdpbca1/insurancedemo/raw",
    "ICEBERG_BASE": "s3a://lhdemocdpbca1/insurancedemo/iceberg",
}


def quote_catalog(name: str) -> str:
    """Quote catalog for Trino when name contains hyphens etc."""
    if name.startswith('"') and name.endswith('"'):
        return name
    if any(ch in name for ch in "-."):
        return f'"{name}"'
    return name


def render_sql(text: str) -> str:
    catalog = os.getenv("INSURANCE_CATALOG", DEFAULTS["CATALOG"])
    values = {
        "CATALOG": quote_catalog(catalog),
        "DATABASE": os.getenv("INSURANCE_DATABASE", DEFAULTS["DATABASE"]),
        "RAW_BASE": os.getenv("RAW_BASE", DEFAULTS["RAW_BASE"]),
        "ICEBERG_BASE": os.getenv("ICEBERG_BASE", DEFAULTS["ICEBERG_BASE"]),
    }
    for key, value in values.items():
        text = text.replace(f"${{{key}}}", value)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Render insurance-demo Trino SQL")
    parser.add_argument("sql_file", help="SQL file name inside trino/ (e.g. 00_setup.sql)")
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print rendered SQL to stdout",
    )
    parser.add_argument(
        "--out",
        help="Optional output path for rendered SQL",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    source = root / args.sql_file
    if not source.exists():
        print(f"File not found: {source}", file=sys.stderr)
        sys.exit(1)

    rendered = render_sql(source.read_text(encoding="utf-8"))

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote {out_path}")

    if args.print or not args.out:
        print(rendered)


if __name__ == "__main__":
    main()
