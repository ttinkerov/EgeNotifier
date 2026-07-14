from __future__ import annotations

import argparse
import sys
from pathlib import Path

from egebot.content.university_catalog import (
    CATALOG_PATH,
    load_programs_from_path,
    update_catalog_from_file,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and optionally install a universities catalog JSON file",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to JSON catalog (array of UniversityProgram objects)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only validate the file, do not write universities.json",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help=f"Destination path (default: {CATALOG_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            programs = load_programs_from_path(args.source)
            print(f"OK: {len(programs)} programs in {args.source}")
            return 0
        count = update_catalog_from_file(args.source, dest=args.dest)
        dest = args.dest or CATALOG_PATH
        print(f"Installed {count} programs → {dest}")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
