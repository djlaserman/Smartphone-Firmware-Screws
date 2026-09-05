"""Update the application VERSION constant for a CI build."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


VERSION_PATTERN = re.compile(r'^(VERSION\s*=\s*["\'])[^"\']+(["\'])', re.MULTILINE)


def update_version(source: Path, version: str) -> None:
    text = source.read_text(encoding="utf-8")
    updated, count = VERSION_PATTERN.subn(rf'\g<1>{version}\g<2>', text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not find exactly one VERSION constant in {source}")
    source.write_text(updated, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="PEP 440-compatible application version")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("src/smartphone_firmware_screws.py"),
        help="Application source file to update",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[.-][0-9A-Za-z.-]+)?", args.version):
        raise SystemExit(f"Invalid version: {args.version}")
    update_version(args.source, args.version)
    print(f"Updated {args.source} to {args.version}")


if __name__ == "__main__":
    main()