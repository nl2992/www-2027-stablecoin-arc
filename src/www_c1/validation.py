"""Input hashing and source-file integrity checks for C1 replay runs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .replay import replay_file


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sample(
    path: Path,
    *,
    expected_sha256: str | None = None,
    max_idle_gap_seconds: float = 30.0,
) -> dict[str, Any]:
    digest = sha256_file(path)
    result: dict[str, Any] = {
        "input": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest,
        "expected_sha256": expected_sha256,
        "sha256_matches_expected": digest == expected_sha256 if expected_sha256 else None,
    }
    if expected_sha256 and digest != expected_sha256:
        result.update({"status": "HASH_MISMATCH", "reason": "input does not match pinned C0 sample"})
        return result
    result.update(replay_file(path, max_idle_gap_seconds=max_idle_gap_seconds))
    return result
