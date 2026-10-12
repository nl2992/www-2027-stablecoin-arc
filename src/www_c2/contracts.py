"""Structural validation for a date-specific contract discovery registry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def validate_registry(entries: Sequence[Mapping[str, object]]) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[object, object]] = set()
    required = {"name", "chain_id", "address", "source", "deployment_status", "verification"}
    for index, item in enumerate(entries):
        missing = sorted(required - item.keys())
        if missing:
            errors.append(f"entry {index}: missing fields {', '.join(missing)}")
            continue
        address = item["address"]
        if not isinstance(address, str) or len(address) != 42 or not address.startswith("0x"):
            errors.append(f"entry {index}: address must be a 20-byte hex address")
        elif any(c not in "0123456789abcdefABCDEF" for c in address[2:]):
            errors.append(f"entry {index}: address contains non-hex characters")
        key = (item["chain_id"], address.lower() if isinstance(address, str) else address)
        if key in seen:
            errors.append(f"entry {index}: duplicate chain/address")
        seen.add(key)
        if item["verification"] not in {"SOURCE_DOCUMENTED", "LIVE_VERIFIED", "UNVERIFIED"}:
            errors.append(f"entry {index}: invalid verification level")
        if item["deployment_status"] not in {"HISTORICALLY_VERIFIED", "UNVERIFIED_AT_TARGET_BLOCK"}:
            errors.append(f"entry {index}: invalid deployment status")
        if item["verification"] == "LIVE_VERIFIED" and item["deployment_status"] != "HISTORICALLY_VERIFIED":
            errors.append(f"entry {index}: live verification requires historical deployment verification")
        if not isinstance(item["source"], str) or not item["source"].startswith("https://"):
            errors.append(f"entry {index}: source must be an HTTPS reference")
    return errors
