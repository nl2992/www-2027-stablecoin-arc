"""Run a streaming replay audit on a normalized Tardis L2 gzip CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validation import validate_sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--max-idle-gap-seconds", type=float, default=30.0)
    args = parser.parse_args()
    result = validate_sample(
        args.input,
        expected_sha256=args.expected_sha256,
        max_idle_gap_seconds=args.max_idle_gap_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{result['status']}: {args.output}")
    if result["status"] == "HASH_MISMATCH":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
