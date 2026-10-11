"""Cross-event inference specified in docs/PRE_ANALYSIS_PLAN.md.

Events are summarized one at a time; pooling is allowed only within a mechanism
group of independent clusters, via DerSimonian-Laird random effects, and is
always reported with its heterogeneity. Linked legs never enter a summary.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RandomEffects:
    pooled: float
    se: float
    ci95: tuple[float, float]
    tau2: float
    q: float
    i2: float
    k: int


def random_effects(estimates: Sequence[float], ses: Sequence[float]) -> RandomEffects:
    """DerSimonian-Laird random-effects summary of k >= 2 independent estimates."""
    k = len(estimates)
    if k < 2 or k != len(ses):
        raise ValueError("need at least two estimates with matching standard errors")
    if any(s <= 0 for s in ses):
        raise ValueError("standard errors must be positive")
    w = [1 / s**2 for s in ses]
    fixed = sum(wi * y for wi, y in zip(w, estimates)) / sum(w)
    q = sum(wi * (y - fixed) ** 2 for wi, y in zip(w, estimates))
    c = sum(w) - sum(wi**2 for wi in w) / sum(w)
    tau2 = max(0.0, (q - (k - 1)) / c)
    w_star = [1 / (s**2 + tau2) for s in ses]
    pooled = sum(wi * y for wi, y in zip(w_star, estimates)) / sum(w_star)
    se = math.sqrt(1 / sum(w_star))
    i2 = max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0
    return RandomEffects(pooled, se, (pooled - 1.959964 * se, pooled + 1.959964 * se), tau2, q, i2, k)


def holm(pvalues: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (family-wise error control)."""
    if any(not 0 <= p <= 1 for p in pvalues.values()):
        raise ValueError("p-values must lie in [0, 1]")
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(ordered), 0.0, {}
    for rank, (key, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * p))
        out[key] = running
    return out


def sign_test(successes: int, n: int) -> float:
    """Exact two-sided binomial sign test p-value under p = 0.5."""
    if not 0 <= successes <= n or n == 0:
        raise ValueError("invalid counts")
    tail = min(successes, n - successes)
    p = sum(math.comb(n, i) for i in range(tail + 1)) / 2**n
    return min(1.0, 2 * p)


def summarize_by_mechanism(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """rows: {cluster_id, mechanism, role, estimate, se}. Only PRIMARY rows, one per cluster, are used."""
    primaries = [r for r in rows if r["role"] == "PRIMARY"]
    clusters = [r["cluster_id"] for r in primaries]
    if len(clusters) != len(set(clusters)):
        raise ValueError("more than one primary estimate per cluster")
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for r in primaries:
        groups.setdefault(r["mechanism"], []).append(r)
    out: dict[str, Any] = {}
    for mechanism, members in sorted(groups.items()):
        entry: dict[str, Any] = {"clusters": sorted(m["cluster_id"] for m in members), "k": len(members)}
        if len(members) >= 2:
            re = random_effects([m["estimate"] for m in members], [m["se"] for m in members])
            entry["random_effects"] = re.__dict__
        else:
            entry["random_effects"] = None
            entry["note"] = "single cluster: reported individually, not pooled"
        out[mechanism] = entry
    return out
