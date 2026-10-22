"""Apply the anchored GMM to the held data and write reports/theory/gmm_applied.json and calibration.json.

Bitfinex stress window: anchor USDT netted with Kraken (and un-netted for contrast); instruments the ETH gap, then the
LTC, BCH and ETC gaps (Bitfinex vs Coinbase hourly).  Binance.US 2023: anchors USDT (all 2023) and USDT+USDC (2023-02..07,
where Bitstamp USDC exists), netted with Bitstamp prices; instruments the first two hourly lags of L (no other item is held).
Each spec reports lambda-hat, a HAC (Andrews bandwidth) 95% interval, Wald p-values for lambda = 1 and lambda = 0, and the
Hansen J test; single-instrument specs add a moving-block-bootstrap interval.

    uv run python -m www_theory.applied
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from . import data, gmm

REPO = data.REPO
OUT = REPO / "reports" / "theory" / "gmm_applied.json"
CAL = REPO / "reports" / "theory" / "calibration.json"
BOOT_DRAWS, BOOT_SEED = 999, 20261022


def _ar1(x: np.ndarray) -> float:
    x = x - x.mean()
    return float((x[1:] * x[:-1]).sum() / (x ** 2).sum())


def fit(Y: np.ndarray, L: np.ndarray, Z: np.ndarray, boot: bool = True) -> dict[str, Any]:
    """Stacked GMM for lambda with anchors Y (n,K), offset L, instruments Z (n,m); OLS and bootstrap alongside."""
    Y = np.asarray(Y, float).reshape(len(L), -1)
    Z = np.asarray(Z, float).reshape(len(L), -1)
    r = gmm.stacked_anchor(Y, L, Z)
    w1, p1 = r.wald(0, 1.0)
    w0, p0 = r.wald(0, 0.0)
    lo, hi = r.ci(0)
    o = gmm.ols(Y[:, 0], L)
    out: dict[str, Any] = {"n": int(len(L)), "anchors": int(Y.shape[1]), "instruments": int(Z.shape[1]),
                           "lam": float(r.beta[0]), "se": float(r.se[0]), "ci95": [lo, hi], "hac_lags": int(r.lags),
                           "wald_lam1": w1, "p_lam1": p1, "wald_lam0": w0, "p_lam0": p0,
                           "J": r.J, "J_df": r.J_df, "J_p": None if r.J_df == 0 else r.J_p,
                           "ols_first_anchor": {"lam": float(o.beta[0]), "ci95": list(o.ci(0))}}
    if boot:
        iv1 = gmm.iv(Y[:, 0], L, Z[:, [0]])
        out["iv_first_instrument_first_anchor"] = {"lam": float(iv1.beta[0]), "ci95": list(iv1.ci(0)),
                                                  "bootstrap": gmm.mbb_iv(Y[:, 0], L, Z[:, 0], BOOT_DRAWS, BOOT_SEED)}
    return out


def bitfinex(f=None) -> dict[str, Any]:
    f = data.bitfinex_frame() if f is None else f
    cols = ["L", "D", "X", "E", "LTC", "ETC", "BCH"]
    h = data.complete(f, cols)
    L = h["L"].to_numpy()
    sets = {"eth": ["E"], "eth_ltc": ["E", "LTC"], "eth_ltc_bch": ["E", "LTC", "BCH"], "eth_ltc_bch_etc": ["E", "LTC", "BCH", "ETC"]}
    specs: dict[str, Any] = {}
    for netted, y in (("netted", (h["D"] - h["X"]).to_numpy()), ("not_netted", h["D"].to_numpy())):
        for name, z in sets.items():
            specs[f"{netted}|{name}"] = fit(y, L, h[z].to_numpy(), boot=len(z) == 1)
    return {"window": list(data.STRESS), "hours": int(len(h)), "anchor": "USDT (Bitfinex USTUSD), external price Kraken USDT/USD",
            "primary": "netted|eth_ltc_bch_etc", "specs": specs}


def binance_us(f=None) -> dict[str, Any]:
    f = data.binance_us_frame() if f is None else f
    f = data.add_lags(f, "L", (1, 2))
    specs: dict[str, Any] = {}
    lag = ["L_l1", "L_l2"]
    h = data.complete(f, ["L", "D_USDT", "X_USDT", *lag])
    n = int(len(h))
    for tag, y in (("netted", (h["D_USDT"] - h["X_USDT"])), ("not_netted", h["D_USDT"])):
        specs[f"usdt|{tag}|lags12"] = fit(y.to_numpy(), h["L"].to_numpy(), h[lag].to_numpy(), boot=False)
        specs[f"usdt|{tag}|lag1"] = fit(y.to_numpy(), h["L"].to_numpy(), h[["L_l1"]].to_numpy(), boot=True)
    h2 = data.complete(f, ["L", "D_USDT", "X_USDT", "D_USDC", "X_USDC", *lag])
    h2 = h2[(h2.index >= "2023-02-01")]
    Y = np.column_stack([h2["D_USDT"] - h2["X_USDT"], h2["D_USDC"] - h2["X_USDC"]])
    specs["usdt_usdc|netted|lags12"] = fit(Y, h2["L"].to_numpy(), h2[lag].to_numpy(), boot=False)
    Yn = np.column_stack([h2["D_USDT"], h2["D_USDC"]])
    specs["usdt_usdc|not_netted|lags12"] = fit(Yn, h2["L"].to_numpy(), h2[lag].to_numpy(), boot=False)
    specs["usdc_only|netted|lags12"] = fit((h2["D_USDC"] - h2["X_USDC"]).to_numpy(), h2["L"].to_numpy(), h2[lag].to_numpy(), boot=False)
    return {"hours_usdt_2023": n, "hours_usdt_usdc": int(len(h2)),
            "note": "instruments are the first two hourly lags of L (Binance.US lists no other held item); the J test therefore "
                    "checks serial independence of the anchor and offset errors",
            "primary": "usdt_usdc|netted|lags12", "specs": specs}


def calibration(f=None) -> dict[str, Any]:
    """Magnitudes the simulation matches, measured on the Bitfinex stress window (hourly bps)."""
    f = data.bitfinex_frame() if f is None else f
    h = data.complete(f, ["L", "D", "X", "E"])
    L, A = h["L"].to_numpy(), (h["D"] - h["X"]).to_numpy()
    lam = float(np.cov(A, L)[0, 1] / L.var(ddof=1))
    eta = A - lam * L
    phi = float(np.cov(h["X"], L)[0, 1] / L.var(ddof=1))
    w = h["X"].to_numpy() - phi * L
    nu = (h["E"] - h["L"]).to_numpy()
    return {"source": "reports/unit_td/anchor_external.json definitions, series re-read from the held data",
            "hours": int(len(h)), "sigma_c": float(L.std(ddof=1)), "rho_c": _ar1(L),
            "lambda_hat_netted_ols": lam, "sigma_eta": float(eta.std(ddof=1)), "rho_eta": _ar1(eta),
            "phi_x_on_L": phi, "sigma_w": float(w.std(ddof=1)), "rho_w": _ar1(w),
            "sd_E_minus_L": float(nu.std(ddof=1)), "rho_E_minus_L": _ar1(nu),
            "sigma_eps": float(nu.std(ddof=1) / np.sqrt(2)), "rho_eps": _ar1(nu),
            "sigma_ext": 6.0, "rho_ext": 0.3,
            "sigma_ext_note": "assumed: Kraken 1-minute-median vs 60-minute close differ by 2.0 bps (median) and 14.1 bps (p95) in "
                              "anchor_external.json (crosscheck_60min_usdt_stress)"}


def main() -> int:
    f = data.bitfinex_frame()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    CAL.write_text(json.dumps(calibration(f), indent=1) + "\n")
    res = {"method": __doc__.strip().split("\n\n")[0], "bitfinex": bitfinex(f), "binance_us": binance_us()}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(f"WROTE {OUT} and {CAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
