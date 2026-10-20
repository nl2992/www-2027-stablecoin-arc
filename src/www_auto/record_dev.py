"""Record the UNIT-TD harness output in DEV mode for the final estimator (724455b), with per-asset baselines.

Dev mode only: ``panel.load_panel("dev")`` never reads the test-asset columns, and this script has no final-mode path.

    uv run python -m www_auto.record_dev            # writes reports/unit_td/dev_724455b.txt

Output is the harness's own ``format_result`` lines (fixed seed) followed by ``b0_asset_X`` / ``b1_asset_X`` /
``b2_asset_X``, the baselines scored on one dev asset at a time with the harness's own functions.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import harness as H
from . import panel as P

SEED = 20261020
OUTPUT = H.REPO / "reports" / "unit_td" / "dev_724455b.txt"


def record(seed: int = SEED) -> list[str]:
    raw, _ = P.load_panel("dev")
    res = H.evaluate(raw, H.file_estimator_factory(), "dev", seed)
    lines = [line for line in H.format_result(res) if not line.startswith("runtime_s")]  # runtime is not reproducible
    for kind in ("b0", "b1", "b2"):
        for asset in P.DEV_SCORED:
            gs = {asset: H.pair_gap(raw, asset, H.PAIR)}
            us = {asset: H.baseline_pair_u(raw, asset, H.PAIR, kind)}
            lines.append(f"{kind}_asset_{asset}: {H.score_parts(gs, us)['score']:.6f}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="www_auto.record_dev")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args(argv)
    lines = record(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
