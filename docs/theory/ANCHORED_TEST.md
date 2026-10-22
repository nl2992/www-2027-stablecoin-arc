# The anchored unit-offset test: model, identification, inference (2026-10-22)

Code: `src/www_theory/{gmm,simulate,applied,data}.py`. Outputs: `reports/theory/{simulation,gmm_applied,calibration}.json`.
Paper pieces: `paper/generated/theory_section.tex` (about 0.65 page, ACM two-column), `theory_numbers.tex` (`\NumG...`),
`theory_table.tex` (`tab:theory`). The section needs `\input{generated/theory_numbers}` in the preamble.

## Model

Source s, reference venue r, item a, hour t, all in bps (1e4 log):

    p_{s,a,t} = p*_{a,t} + u_{s,t} + e_{s,a,t}

* Offset shared by non-anchor items: c = u + delta, with u the unit offset and delta source-wide item demand (the alternative).
  Demand enters every non-anchor item and not the anchor.
* Cross-item offset: L = (u_s - u_r) + eps = c + eps (u_r absorbed under A2).
* Anchor k has p*_k = 0 in USD up to its own deviation x (a stablecoin's token discount), so D = u + x + eta.
* x is measured on an independent venue: X = x + xi. Netted anchor Y = D - X = u + eta - xi (xi folded into eta).
* Estimand: lambda = Cov(u, c) / Var(c), the unit share of the offset's variation. delta = 0 gives 1; u = 0 gives 0.

## Assumptions

* A1 Additivity: the model above; every non-anchor item loads one-for-one on c.
* A2 The reference venue's unit is stable over the window (u_r constant).
* A3 X measures x on an independent venue: xi is independent of (u, delta, eps, eta). x may co-move with c (that is the point).
* A4 Instrument: Z = gamma c + nu with gamma != 0 (a second item's offset, e.g. the ETH gap), nu independent of (c, eta, eps),
  and Cov(eta, c) = Cov(eps, eta) = 0. Relevance: Var(c) > 0. Exclusion: Z moves Y only through u.

## Proposition

Under A1-A4,  beta = Cov(D - X, Z) / Cov(L, Z) = lambda.

Proof. Cov(Y, Z) = gamma Cov(u + eta, c) = gamma Cov(u, c), since eta is uncorrelated with c and nu is uncorrelated with u and eta.
Cov(L, Z) = gamma Cov(c + eps, c) = gamma Var(c), since eps and nu are uncorrelated with c. The ratio is Cov(u, c)/Var(c) = lambda. QED.

Corollaries.
1. OLS of Y on L has slope Cov(u, c)/(Var(c) + Var(eps)) = lambda * R with reliability R = Var(c)/(Var(c) + Var(eps)) <= 1: attenuated.
   (If Cov(eps, eta) != 0 there is a further bias.) On the stress window R is about 0.997, so the attenuation is negligible there;
   it matters only when L is noisy (S6).
2. Without netting, the IV slope of D on L is lambda + Cov(x, c)/Var(c) = lambda + phi. In the data phi = -0.256, which is the
   0.71 versus 0.97 gap.
3. Pure unit shift: Cov(delta, .) = 0, lambda = 1. Pure demand: u = 0, lambda = 0, and Y = eta is unrelated to L.

## Over-identification

K anchors and m instruments (z = (1, Z_1..Z_m)): the moments E[z_j (Y_k - mu_k - lambda L)] = 0 identify one lambda and K
intercepts from K(m+1) moments, so Hansen's J is chi-square with K m - 1 degrees of freedom under the null. Two-step GMM,
first step 2SLS weight, second step the inverse Bartlett long-run variance. J has power against (i) an instrument that
carries the anchor's own noise (exclusion fails), and (ii) anchor-specific depegs with different loadings on c. J has NO power
against a depeg that loads on c by the same phi in every anchor (S4: rejection 0.03): the netting by X (A3), not J,
protects against that. With one anchor and one instrument the model is just identified.

## Inference

* HAC (Bartlett) covariance, Andrews (1991) plug-in bandwidth (AR(1) approximating model per moment); the fixed Newey-West
  rule floor(4 (n/100)^(2/9)) is kept as a check and under-smooths persistent moments (S3 coverage 0.33 vs 0.78 for IV).
* Moving-block bootstrap, overlapping blocks drawn with replacement, block length
  b = clip(ceil((2 rho^2 / (1 - rho^2)^2)^(1/3) n^(1/3)), 1, n/4), rho = lag-1 autocorrelation of the IV score series
  (clipped to [0, 0.99]); 999 draws, percentile 95% interval.

## Simulation (1,000 windows of 4,434 hours, seed 20261022, about a minute)

DGP calibrated to the stress window (reports/theory/calibration.json): AR(1) offset rho 0.995, sd 145 bps; noise eps sd 8.2
(rho 0.43); eta sd 13.8 (rho 0.65); depeg loading phi = -0.256, residual sd 70 (rho 0.99); external-price noise sd 6 (assumed,
from the Kraken 1-min vs 60-min cross-check). Two anchors, three instruments, J has 5 df. Results in `paper/generated/theory_table.tex`
and `reports/theory/simulation.json`.

## Applied results (reports/theory/gmm_applied.json)

* Bitfinex stress window, USDT netted with Kraken, instruments ETH, LTC, BCH, ETC gaps (Bitfinex vs Coinbase hourly): see table.
* Binance.US 2023, instruments the first two lags of L (no other item is held there). XLM and XRP on Coinbase cover under
  half the window, and LINK, SOL, DOGE and ADA are not on Coinbase then, so they are not used.

## Caveats the paper must carry

1. lambda = 1 is rejected on the Bitfinex stress window even after netting (0.971, interval 0.961-0.981, HAC and bootstrap);
   the departure is 3%. Say "close to one", not "equal to one".
2. The two-anchor Binance.US test with externally netted USDC rejects J (p < 0.001). The un-netted version does not. The Bitstamp
   USDC price is thin and was itself depegged in March 2023; its measurement error is serially correlated, which violates the
   lag-instrument exclusion. Do not present the two-anchor result as a pass.
3. Binance.US instruments are lags of L, not another item: validity needs serially independent eta and eps.
4. In mixtures (S3) the realised unit share varies from window to window, so the interval around the population lambda covers
   at 0.72-0.78, not 0.95, for HAC and bootstrap alike.
5. Persistence (rho 0.995) means few effective observations; the block bootstrap and HAC intervals are narrow only because
   the series is long. The earlier week- and month-block intervals (anchor_external.json) are wider.
