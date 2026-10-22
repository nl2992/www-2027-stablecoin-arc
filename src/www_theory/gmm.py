"""Linear GMM with HAC weighting, the Hansen J test, Wald tests and a moving-block bootstrap, in numpy only.

Moment form. For observations t = 1..n the moment vector is  g_t(b) = a_t - B_t b,  with a_t of length q and B_t of shape
(q, p). The GMM estimator for a weight matrix W is  b = (Bbar' W Bbar)^-1 Bbar' W abar  (bars are sample means).  Two steps:
step 1 uses a supplied W1 (for IV, the inverse of the instruments' second-moment matrix, i.e. 2SLS); step 2 uses
W = S^-1 where S is the Bartlett-kernel (Newey-West) long-run variance of g_t(b_1).  The covariance is
(Bbar' S^-1 Bbar)^-1 / n and  J = n g(b_2)' S^-1 g(b_2)  is chi-square with q - p degrees of freedom under the null that all
moment conditions hold.  When q = p the model is just identified and J = 0.

Bandwidth.  ``lags="auto"`` uses Andrews' (1991) plug-in for the Bartlett kernel with AR(1) approximating models fitted to
each moment series: lags = floor(1.1447 (alpha n)^(1/3)), alpha = sum 4 r^2 s^4 / ((1-r)^6 (1+r)^2) / sum s^4/(1-r)^4,
capped at n/4.  ``lags="nw"`` uses the fixed Newey-West rule floor(4 (n/100)^(2/9)), which badly under-smooths very
persistent moments (see the simulation).  An int gives the number of lags.

Moving-block bootstrap.  Block length b = clip(ceil((2 rho^2 / (1 - rho^2)^2)^(1/3) n^(1/3)), 1, n/4), with rho the
lag-1 autocorrelation of the estimating-equation score series (clipped to [0, 0.99]); this is the AR(1) plug-in for the
bias-optimal block length of a mean-type statistic.  Blocks are drawn with replacement from all n-b+1 overlapping blocks
and the resample is truncated to n.  The interval is the percentile interval of the re-estimated statistic.

Only numpy is used; the chi-square survival function is computed from the regularised incomplete gamma function.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

Z975 = 1.959963984540054


# ---- distribution functions ----------------------------------------------------------------------------------------------

def chi2_sf(x: float, df: int) -> float:
    """P(chi-square_df > x) from the regularised upper incomplete gamma Q(df/2, x/2) (series / continued fraction)."""
    if df <= 0:
        return float("nan")
    if x <= 0:
        return 1.0
    a, z = df / 2.0, x / 2.0
    if z < a + 1.0:                      # series for P, then Q = 1 - P
        term = s = 1.0 / a
        ap = a
        for _ in range(2000):
            ap += 1.0
            term *= z / ap
            s += term
            if abs(term) < abs(s) * 1e-16:
                break
        return float(max(0.0, 1.0 - s * math.exp(-z + a * math.log(z) - math.lgamma(a))))
    tiny = 1e-300                         # Lentz continued fraction for Q
    b = z + 1.0 - a
    c, d = 1.0 / tiny, 1.0 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return float(min(1.0, math.exp(-z + a * math.log(z) - math.lgamma(a)) * h))


def norm_sf2(z: float) -> float:
    """Two-sided normal tail probability P(|N(0,1)| > |z|)."""
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


# ---- long-run variance ---------------------------------------------------------------------------------------------------

def _lag1(x: np.ndarray) -> float:
    xc = x - x.mean()
    den = float((xc ** 2).sum())
    return float((xc[1:] * xc[:-1]).sum() / den) if den > 0 else 0.0


def andrews_lags(g: np.ndarray) -> int:
    """Andrews (1991) Bartlett-kernel bandwidth with AR(1) plug-in over the columns of g (n x q); capped at n/4."""
    n = g.shape[0]
    num = den = 0.0
    for j in range(g.shape[1]):
        r = min(max(_lag1(g[:, j]), 0.0), 0.99)
        sig4 = (float(np.var(g[:, j])) * (1.0 - r * r)) ** 2      # squared AR(1) innovation variance
        num += 4.0 * r * r * sig4 / ((1.0 - r) ** 6 * (1.0 + r) ** 2)
        den += sig4 / (1.0 - r) ** 4
    alpha = num / den if den > 0 else 0.0
    return int(min(math.floor(1.1447 * (alpha * n) ** (1.0 / 3.0)), n // 4))


def nw_lags(n: int) -> int:
    return int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


def hac(g: np.ndarray, lags: int | str = "auto") -> tuple[np.ndarray, int]:
    """Bartlett long-run variance of the (n x q) series g (not re-centred, as moments have mean zero under the null)."""
    n = g.shape[0]
    L = andrews_lags(g) if lags == "auto" else nw_lags(n) if lags == "nw" else int(lags)
    S = g.T @ g / n
    for j in range(1, L + 1):
        G = g[j:].T @ g[:-j] / n
        S += (1.0 - j / (L + 1.0)) * (G + G.T)
    return (S + S.T) / 2.0, L


# ---- GMM -----------------------------------------------------------------------------------------------------------------

@dataclass
class GMMResult:
    beta: np.ndarray
    cov: np.ndarray
    se: np.ndarray
    J: float
    J_df: int
    J_p: float
    n: int
    lags: int
    names: list[str] = field(default_factory=list)

    def wald(self, i: int, null: float) -> tuple[float, float]:
        """Wald statistic and chi-square(1) p-value for H0: beta[i] = null."""
        w = (self.beta[i] - null) ** 2 / self.cov[i, i]
        return float(w), chi2_sf(w, 1)

    def ci(self, i: int = 0) -> tuple[float, float]:
        return float(self.beta[i] - Z975 * self.se[i]), float(self.beta[i] + Z975 * self.se[i])


def _solve(Bbar: np.ndarray, abar: np.ndarray, W: np.ndarray) -> np.ndarray:
    return np.linalg.solve(Bbar.T @ W @ Bbar, Bbar.T @ W @ abar)


def gmm_linear(a: np.ndarray, B: np.ndarray, W1: np.ndarray, lags: int | str = "auto", two_step: bool = True) -> GMMResult:
    """Two-step efficient GMM for moments g_t(b) = a_t - B_t b.  a: (n, q); B: (n, q, p); W1: (q, q) first-step weight."""
    n, q = a.shape
    p = B.shape[2]
    if q < p:
        raise ValueError(f"under-identified: {q} moments for {p} parameters")
    abar, Bbar = a.mean(0), B.mean(0)
    b1 = _solve(Bbar, abar, W1)
    g1 = a - np.einsum("tqp,p->tq", B, b1)
    S, L = hac(g1, lags)
    Si = np.linalg.pinv(S, rcond=1e-12)
    if q == p:
        # just identified: b is the same for every W; use the sandwich with the first-step residuals
        Binv = np.linalg.inv(Bbar)
        cov = Binv @ S @ Binv.T / n
        return GMMResult(b1, cov, np.sqrt(np.diag(cov)), 0.0, 0, float("nan"), n, L)
    b2 = _solve(Bbar, abar, Si) if two_step else b1
    g2 = a - np.einsum("tqp,p->tq", B, b2)
    gm = g2.mean(0)
    if two_step:
        S2, L = hac(g2, lags)               # variance of the step-2 moments for the covariance
        Si2 = np.linalg.pinv(S2, rcond=1e-12)
        cov = np.linalg.inv(Bbar.T @ Si2 @ Bbar) / n
        J = float(n * gm @ Si2 @ gm)
    else:
        M = np.linalg.inv(Bbar.T @ W1 @ Bbar) @ Bbar.T @ W1
        cov = M @ S @ M.T / n
        J = float(n * gm @ Si @ gm)
    df = q - p
    return GMMResult(b2, cov, np.sqrt(np.diag(cov)), J, df, chi2_sf(J, df), n, L)


def _with_const(M: np.ndarray) -> np.ndarray:
    M = np.asarray(M, float)
    if M.ndim == 1:
        M = M[:, None]
    return np.column_stack([np.ones(len(M)), M])


def iv(y: np.ndarray, x: np.ndarray, Z: np.ndarray, lags: int | str = "auto", two_step: bool = True) -> GMMResult:
    """Linear IV  y = c + lam x + e  with instruments Z (n x m, constant added); beta = [lam, c].  m = 1 is just identified."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    Zc = _with_const(Z)
    n = len(y)
    a = Zc * y[:, None]
    B = np.stack([Zc * x[:, None], Zc], axis=2)
    W1 = np.linalg.inv(Zc.T @ Zc / n)
    r = gmm_linear(a, B, W1, lags, two_step)
    r.names = ["lam", "const"]
    return r


def ols(y: np.ndarray, x: np.ndarray, lags: int | str = "auto") -> GMMResult:
    """OLS of y on [x, const] with a HAC covariance (IV with the regressor as its own instrument)."""
    r = iv(y, x, np.asarray(x, float)[:, None], lags)
    return r


def stacked_anchor(Y: np.ndarray, L: np.ndarray, Z: np.ndarray, lags: int | str = "auto", two_step: bool = True) -> GMMResult:
    """Common-lambda GMM across K anchors: moments E[z (Y_k - c_k - lam L)] = 0, k = 1..K, z = (1, instruments).

    Y: (n, K) netted anchor offsets D_k - X_k; L: (n,); Z: (n, m).  Parameters [lam, c_1..c_K];
    moments K(m+1), so the J test has K m - 1 degrees of freedom.  beta[0] is lambda.
    """
    Y = np.asarray(Y, float)
    if Y.ndim == 1:
        Y = Y[:, None]
    n, K = Y.shape
    Zc = _with_const(Z)
    m1 = Zc.shape[1]
    L = np.asarray(L, float)
    a = np.concatenate([Zc * Y[:, [k]] for k in range(K)], axis=1)
    B = np.zeros((n, K * m1, 1 + K))
    for k in range(K):
        B[:, k * m1:(k + 1) * m1, 0] = Zc * L[:, None]
        B[:, k * m1:(k + 1) * m1, 1 + k] = Zc
    W1 = np.kron(np.eye(K), np.linalg.inv(Zc.T @ Zc / n))
    r = gmm_linear(a, B, W1, lags, two_step)
    r.names = ["lam"] + [f"c{k + 1}" for k in range(K)]
    return r


# ---- moving-block bootstrap ----------------------------------------------------------------------------------------------

def block_length(score: np.ndarray) -> int:
    """AR(1) plug-in block length for the score series (see module docstring)."""
    n = len(score)
    r = min(max(_lag1(np.asarray(score, float)), 0.0), 0.99)
    b = math.ceil((2.0 * r * r / (1.0 - r * r) ** 2) ** (1.0 / 3.0) * n ** (1.0 / 3.0))
    return int(min(max(b, 1), max(n // 4, 1)))


def mbb_indices(n: int, b: int, draws: int, rng: np.random.Generator) -> np.ndarray:
    """(draws, n) integer indices of moving-block resamples (overlapping blocks of length b, truncated to n)."""
    nb = -(-n // b)
    starts = rng.integers(0, n - b + 1, size=(draws, nb))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(draws, nb * b)
    return idx[:, :n]


def iv_slope_vec(y: np.ndarray, x: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Just-identified IV slope cov(y,z)/cov(x,z) along the last axis (works on (draws, n) arrays)."""
    zc = z - z.mean(-1, keepdims=True)
    return (zc * y).sum(-1) / (zc * x).sum(-1)


def iv_score(y: np.ndarray, x: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Estimating-equation score series (z - zbar)(y - ybar - beta (x - xbar)) of the just-identified IV slope."""
    zc, xc, yc = z - z.mean(), x - x.mean(), y - y.mean()
    beta = float((zc * yc).sum() / (zc * xc).sum())
    return zc * (yc - beta * xc)


def mbb_iv(y: np.ndarray, x: np.ndarray, z: np.ndarray, draws: int = 999, seed: int = 0, b: int | None = None) -> dict:
    """Moving-block bootstrap for the just-identified IV slope: point estimate, block length, 95% percentile interval,
    and the bootstrap p-values of H0: lam = 1 and H0: lam = 0 (the interval-inversion form: 2 min tail share)."""
    y, x, z = (np.asarray(v, float) for v in (y, x, z))
    n = len(y)
    b = block_length(iv_score(y, x, z)) if b is None else b
    rng = np.random.default_rng(seed)
    out = []
    step = max(1, 4_000_000 // n)
    for s in range(0, draws, step):
        idx = mbb_indices(n, b, min(step, draws - s), rng)
        out.append(iv_slope_vec(y[idx], x[idx], z[idx]))
    est = np.concatenate(out)
    est = est[np.isfinite(est)]
    lo, hi = np.percentile(est, [2.5, 97.5])
    point = float(iv_slope_vec(y, x, z))

    def p(null: float) -> float:
        below = (np.sum(est <= null) + 1) / (len(est) + 1)
        return float(min(1.0, 2.0 * min(below, 1.0 - below + 1.0 / (len(est) + 1))))

    return {"est": point, "block": b, "ci95": [float(lo), float(hi)], "p_lam_eq_1": p(1.0), "p_lam_eq_0": p(0.0)}


def mbb_generic(estimator, arrays: list[np.ndarray], draws: int = 499, seed: int = 0, b: int | None = None,
                score: np.ndarray | None = None) -> dict:
    """Moving-block bootstrap of any estimator(*arrays) -> float on same-length arrays (slower, loop over draws)."""
    n = len(arrays[0])
    if b is None:
        b = block_length(score if score is not None else arrays[0])
    rng = np.random.default_rng(seed)
    idx = mbb_indices(n, b, draws, rng)
    est = np.array([estimator(*(a[i] for a in arrays)) for i in idx])
    est = est[np.isfinite(est)]
    lo, hi = np.percentile(est, [2.5, 97.5])
    return {"est": float(estimator(*arrays)), "block": b, "ci95": [float(lo), float(hi)], "draws": int(len(est))}
