"""Command-line entry point for a reproducible C0 panel-quality report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .quality import audit_parquet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit_parquet(args.panel)
    result["source_revision"] = args.source_revision
    if args.panel.is_file():
        digest = hashlib.sha256()
        with args.panel.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result["sha256"] = digest.hexdigest()
        result["bytes"] = args.panel.stat().st_size
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{result['status']}: {args.output}")


if __name__ == "__main__":
    main()
