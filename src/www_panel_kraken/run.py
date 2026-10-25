"""Step 3: pre-registered estimation (autoresearch/program_panel_kraken.md). Writes reports/panel_kraken/results.json.

    uv run python -m www_panel_kraken.run

D - X = lambda L + day effects + error, within-day OLS and IV (L2 instruments L), 7-day moving-block bootstrap, 1,000 draws, seed 20261025.
The estimation code is www_panel.run's (imported), with only the seed changed. Hours need L, L2, D and X (so ETH-based IV uses hours up
to 2023-12, where Bitstamp ETH/USD ends). K1 and K2 are evaluated on stress months as in the panel's P1 and P2; calm-month and
all-month estimates are reported alongside.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

import pandas as pd

from www_panel import run as PR

from .classify import OUT as MONTHS
from .data import available_fiats, gap, log_bps, read_bitstamp_usd, read_close

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "reports" / "panel_kraken" / "results.json"
SEED, DRAWS, BLOCK = 20261025, 1000, 7


@contextlib.contextmanager
def _seed():
    old = PR.SEED
    PR.SEED = SEED
    try:
        yield
    finally:
        PR.SEED = old


def estimate(stats: dict) -> dict:
    with _seed():
        return PR.estimate(stats, block=BLOCK)


def build_panel(months: dict) -> pd.DataFrame:
    """Hourly L, L2, D, X for every stress or calm month, per Kraken currency."""
    xb, xe = read_bitstamp_usd("BTCUSD"), read_bitstamp_usd("ETHUSD")
    x = log_bps(read_close("USDT", "USD"))
    frames = []
    for fiat in available_fiats():
        st = {m: r["status"] for m, r in months["units"][fiat]["months"].items() if r["status"] in ("stress", "calm")}
        if not st:
            continue
        f = pd.concat({"L": gap(read_close("XBT", fiat), xb), "L2": gap(read_close("ETH", fiat), xe)}, axis=1)
        f["D"] = log_bps(read_close("USDT", fiat)).reindex(f.index)
        f["X"] = x.reindex(f.index)
        f["month"] = f.index.strftime("%Y-%m")
        f = f[f["month"].isin(st)]
        f["status"] = f["month"].map(st)
        f["unit"], f["fiat"] = fiat, fiat
        frames.append(f)
    return pd.concat(frames)


def est(f: pd.DataFrame) -> dict:
    return estimate(PR.hourly_stats(f))


def used_months(f: pd.DataFrame) -> int:
    """Months with at least one hour carrying L, L2, D and X."""
    g = f.dropna(subset=["L", "L2", "D", "X"])
    return int(g.groupby("unit")["month"].nunique().sum())


def run() -> dict:
    months = json.loads(MONTHS.read_text())
    panel = build_panel(months)
    fiats = sorted(panel["fiat"].unique())
    stress, calm = PR.sel(panel, status="stress"), PR.sel(panel, status="calm")
    res: dict = {"design": {"seed": SEED, "draws": DRAWS, "block_days": BLOCK, "min_hours_per_day": PR.MIN_HOURS_PER_DAY,
                            "months_file": "reports/panel_kraken/months.json",
                            "rule": "K1 and K2 on stress months, as the panel's P1 and P2; calm and all-month estimates reported alongside"},
                 "pooled_stress": est(stress) if len(stress) else {"n_days": 0},
                 "pooled_calm": est(calm) if len(calm) else {"n_days": 0}, "pooled_all": est(panel), "by_currency": {}}
    for fiat in fiats:
        s, c = PR.sel(stress, fiat=fiat), PR.sel(calm, fiat=fiat)
        row = {"stress_months": used_months(s) if len(s) else 0, "calm_months": used_months(c) if len(c) else 0,
               "classified_stress_months": int(months["units"][fiat]["counts"]["stress"]),
               "classified_calm_months": int(months["units"][fiat]["counts"]["calm"]),
               "all": est(PR.sel(panel, fiat=fiat))}
        row["all_months"] = row["stress_months"] + row["calm_months"]
        if len(s):
            row["stress"] = est(s)
        if len(c):
            row["calm"] = est(c)
        res["by_currency"][fiat] = row
    res["by_month"] = [{"unit": u, "month": m, "status": f["status"].iloc[0], **est(f)}
                       for (u, m), f in panel.groupby(["unit", "month"], sort=True) if len(f.dropna(subset=["L", "L2", "D", "X"])) > 2]
    # ---- K1, K2, evaluated mechanically
    ps = res["pooled_stress"].get("iv")
    k1 = {"set": "stress", "defined": ps is not None}
    if ps:
        k1.update(lam=ps["lam"], lo=ps["lo"], hi=ps["hi"], excludes_0=bool(ps["lo"] > 0 or ps["hi"] < 0))
    k1["pass"] = bool(k1.get("excludes_0", False))
    pa = res["pooled_all"]["iv"]
    k1["all_months"] = {"lam": pa["lam"], "lo": pa["lo"], "hi": pa["hi"], "excludes_0": bool(pa["lo"] > 0 or pa["hi"] < 0)}
    elig = {k: v for k, v in res["by_currency"].items() if v["stress_months"] >= 3}
    inside = {k: bool(0.8 <= v["stress"]["iv"]["lam"] <= 1.2) for k, v in elig.items()}
    k2 = {"set": "stress", "eligible": sorted(elig), "in_0.8_1.2": inside, "n_inside": int(sum(inside.values())), "n_eligible": len(elig)}
    k2["pass"] = bool(k2["n_inside"] > k2["n_eligible"] / 2)
    elig_all = {k: v for k, v in res["by_currency"].items() if v["all_months"] >= 3}
    in_all = {k: bool(0.8 <= v["all"]["iv"]["lam"] <= 1.2) for k, v in elig_all.items()}
    k2["all_months"] = {"eligible": sorted(elig_all), "in_0.8_1.2": in_all, "n_inside": int(sum(in_all.values())),
                        "n_eligible": len(elig_all), "pass": bool(sum(in_all.values()) > len(elig_all) / 2)}
    res["K1"], res["K2"] = k1, k2
    return res


def main() -> None:
    res = run()
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("K1", "K2")}, indent=1))


if __name__ == "__main__":
    main()
