"""Simulation study for the anchored unit-offset estimator; writes reports/theory/simulation.json.

Data-generating process (hourly, bps; n and the scales come from reports/theory/calibration.json, measured on the Bitfinex
stress window).  Common offset c = u + d (unit part u, source-wide demand part d, each AR(1)), L = c + eps, instruments
Z_j = c + nu_j (j = 1..3), K = 2 anchors with netted offsets  D_k - X_k = u + eta_k - e_k  (e_k = measurement noise of the
external venue's price).  The estimand is lambda = Cov(u, c)/Var(c).  Scenarios:
  S1 pure unit shift (lambda 1); S2 pure demand (0); S3 mixture with equal variances (0.5);
  S4 unit shift + anchor-specific depeg x_k = phi u + w_k, NOT netted (naive; true unit share 1);
  S5 as S4 but netted with the external price; S6 as S1 with L measured with heavy noise (reliability 0.5);
  S7 (extra) as S4 with heterogeneous phi across the two anchors, to show where the J test has power.
Estimators: OLS of anchor 1 on L; IV with Z_1 (just identified); two-anchor two-step GMM with all 3 instruments (J has 5 df);
IV with the fixed Newey-West bandwidth (shows the under-smoothing).  Tests are 5% Wald tests with a HAC covariance (Andrews
bandwidth) unless stated; the block-bootstrap interval is evaluated on the first BOOT_REPS replications.

    uv run python -m www_theory.simulate        # 1,000 replications per scenario, seed fixed, about a minute
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import gmm
from .applied import CAL

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "theory" / "simulation.json"
REPS, BOOT_REPS, BOOT_DRAWS, SEED, BATCH = 1000, 200, 299, 20261022, 100
M_INSTR, K_ANCH = 3, 2

SCENARIOS: dict[str, dict[str, Any]] = {
    "S1": dict(text="pure unit shift", unit_share=1.0, x=False, netted=True, noisy_L=False, phi=(0.0, 0.0), truth=1.0),
    "S2": dict(text="pure source-wide demand", unit_share=0.0, x=False, netted=True, noisy_L=False, phi=(0.0, 0.0), truth=0.0),
    "S3": dict(text="mixture, unit share 0.5", unit_share=0.5, x=False, netted=True, noisy_L=False, phi=(0.0, 0.0), truth=0.5),
    "S4": dict(text="unit shift + anchor depeg, not netted", unit_share=1.0, x=True, netted=False, noisy_L=False, phi=(-0.256, -0.256), truth=1.0),
    "S5": dict(text="unit shift + anchor depeg, netted", unit_share=1.0, x=True, netted=True, noisy_L=False, phi=(-0.256, -0.256), truth=1.0),
    "S6": dict(text="unit shift, heavy noise in L", unit_share=1.0, x=False, netted=True, noisy_L=True, phi=(0.0, 0.0), truth=1.0),
    "S7": dict(text="as S4, depeg loadings differ by anchor", unit_share=1.0, x=True, netted=False, noisy_L=False, phi=(-0.256, 0.20), truth=1.0),
}


def ar1(rho: float, sigma: float, shape: tuple[int, ...], n: int, rng: np.random.Generator) -> np.ndarray:
    """Stationary AR(1) paths with marginal sd sigma; shape (*shape, n)."""
    out = np.empty((*shape, n))
    s_in = sigma * np.sqrt(1.0 - rho * rho)
    e = rng.standard_normal((*shape, n))
    out[..., 0] = sigma * rng.standard_normal(shape)
    for t in range(1, n):
        out[..., t] = rho * out[..., t - 1] + s_in * e[..., t]
    return out


def draw(sc: dict[str, Any], cal: dict[str, float], R: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    n = int(cal["hours"])
    sc_c, rho_c = cal["sigma_c"], cal["rho_c"]
    share = sc["unit_share"]
    u = ar1(rho_c, sc_c * np.sqrt(share), (R,), n, rng) if share > 0 else np.zeros((R, n))
    d = ar1(rho_c, sc_c * np.sqrt(1 - share), (R,), n, rng) if share < 1 else np.zeros((R, n))
    c = u + d
    s_eps = sc_c if sc["noisy_L"] else cal["sigma_eps"]
    L = c + ar1(cal["rho_eps"], s_eps, (R,), n, rng)
    Z = c[:, None, :] + ar1(cal["rho_eps"], s_eps, (R, M_INSTR), n, rng)
    eta = ar1(cal["rho_eta"], cal["sigma_eta"], (R, K_ANCH), n, rng)
    y = u[:, None, :] + eta
    if sc["x"]:
        phi = np.array(sc["phi"])[None, :, None]
        x = phi * u[:, None, :] + ar1(cal["rho_w"], cal["sigma_w"], (R, K_ANCH), n, rng)
        y = y + x
        if sc["netted"]:
            ext = ar1(cal["rho_ext"], cal["sigma_ext"], (R, K_ANCH), n, rng)
            y = y - (x + ext)                     # D - X with X = x + external measurement noise
    elif sc["netted"]:
        y = y - ar1(cal["rho_ext"], cal["sigma_ext"], (R, K_ANCH), n, rng)
    return {"L": L, "Z": Z, "y": y}


def _tests(beta: float, se: float, truth: float) -> dict[str, float]:
    return {"est": beta, "rej1": float(abs(beta - 1.0) / se > gmm.Z975), "rej0": float(abs(beta) / se > gmm.Z975),
            "cover": float(abs(beta - truth) <= gmm.Z975 * se)}


def one_rep(L: np.ndarray, Z: np.ndarray, y: np.ndarray, truth: float) -> dict[str, dict[str, float]]:
    o = gmm.iv(y[0], L, L[:, None], "auto", two_step=False)   # OLS: the regressor is its own instrument
    i = gmm.iv(y[0], L, Z[0][:, None], "auto", two_step=False)
    inw = gmm.iv(y[0], L, Z[0][:, None], "nw", two_step=False)
    g = gmm.stacked_anchor(y.T, L, Z.T, "auto")
    out = {"ols": _tests(o.beta[0], o.se[0], truth), "iv": _tests(i.beta[0], i.se[0], truth),
           "iv_nw": _tests(inw.beta[0], inw.se[0], truth), "gmm": _tests(g.beta[0], g.se[0], truth)}
    out["gmm"]["J_rej"] = float(g.J_p < 0.05)
    out["gmm"]["lags"] = float(g.lags)
    return out


def run_scenario(name: str, cal: dict[str, float], reps: int, boot_reps: int, boot_draws: int, seed: int) -> dict[str, Any]:
    sc = SCENARIOS[name]
    rng = np.random.default_rng(seed)
    rows: list[dict[str, dict[str, float]]] = []
    boot_cover, boot_rej1, boot_rej0, nb = 0.0, 0.0, 0.0, 0
    done = 0
    while done < reps:
        R = min(BATCH, reps - done)
        d = draw(sc, cal, R, rng)
        for r in range(R):
            rows.append(one_rep(d["L"][r], d["Z"][r], d["y"][r], sc["truth"]))
            if done + r < boot_reps:
                b = gmm.mbb_iv(d["y"][r, 0], d["L"][r], d["Z"][r, 0], boot_draws, seed + done + r)
                lo, hi = b["ci95"]
                boot_cover += float(lo <= sc["truth"] <= hi)
                boot_rej1 += float(not (lo <= 1.0 <= hi))
                boot_rej0 += float(not (lo <= 0.0 <= hi))
                nb += 1
        done += R
    res: dict[str, Any] = {"text": sc["text"], "truth": sc["truth"], "reps": reps, "estimators": {}}
    for est in ("ols", "iv", "iv_nw", "gmm"):
        v = {k: np.array([r[est][k] for r in rows]) for k in rows[0][est]}
        e = v["est"]
        res["estimators"][est] = {"mean": float(e.mean()), "bias": float(e.mean() - sc["truth"]), "sd": float(e.std(ddof=1)),
                                  "rmse": float(np.sqrt(((e - sc["truth"]) ** 2).mean())),
                                  "rej_lam1": float(v["rej1"].mean()), "rej_lam0": float(v["rej0"].mean()), "coverage95": float(v["cover"].mean())}
    res["J_rejection_5pct"] = float(np.mean([r["gmm"]["J_rej"] for r in rows]))
    res["J_df"] = K_ANCH * M_INSTR - 1
    res["mean_hac_lags_gmm"] = float(np.mean([r["gmm"]["lags"] for r in rows]))
    res["bootstrap_iv"] = {"reps": nb, "draws": boot_draws, "coverage95": boot_cover / nb, "rej_lam1": boot_rej1 / nb, "rej_lam0": boot_rej0 / nb}
    return res


def main(argv: list[str] | None = None) -> int:
    cal = json.loads(CAL.read_text())
    t0 = time.time()
    out: dict[str, Any] = {"method": __doc__.strip().split("\n\n")[0], "reps": REPS, "seed": SEED, "hours": int(cal["hours"]),
                           "calibration_file": "reports/theory/calibration.json", "calibration": cal,
                           "instruments": M_INSTR, "anchors": K_ANCH, "scenarios": {}}
    for i, name in enumerate(SCENARIOS):
        out["scenarios"][name] = run_scenario(name, cal, REPS, BOOT_REPS, BOOT_DRAWS, SEED + 1000 * i)
        print(f"{name} done {time.time() - t0:.0f}s", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
