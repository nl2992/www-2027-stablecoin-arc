"""One-episode oracle audit pilot: Chainlink feeds during the USDC depeg (2023-03-08..17) vs a unit-corrected USD reference.

Stages (``--stage``): ``fetch`` (read-only Ethereum RPC for Chainlink; HTTP probes of Pyth Benchmarks and
CryptoCompare), ``analyze`` (offline, from data/raw/audit and the local candle files), ``all``.
The RPC endpoint comes from WWW_ETH_RPC_URL / .env, is never printed or written, and the total call budget is a hard
1,500 calls across all runs (the cumulative count is stored beside the raw data).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from www_c2.archive_run import Budgeted, StopRun, block_at_or_before, endpoint_from_env
from www_c2.rpc import RpcError, rpc_call
from www_c2.validation_plan import calldata, keccak256

TOTAL_RPC_BUDGET = 1500
RPC_SPACING = 0.2
HTTP_SPACING = 1.0
WINDOWS = {"depeg": ("2023-03-08", "2023-03-17"), "calm": ("2023-02-20", "2023-03-01")}  # [start, end) UTC
RAW = Path("data/raw/audit")

# Documented EACAggregatorProxy addresses (Ethereum mainnet); verified on-chain via description()/decimals().
FEEDS = {
    "USDC/USD": ("0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6", "USDC / USD"),
    "USDT/USD": ("0x3E7d1eAB13ad0104d2750B8863b489D65364e32D", "USDT / USD"),
    "DAI/USD": ("0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9", "DAI / USD"),
    "BTC/USD": ("0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c", "BTC / USD"),
    "ETH/USD": ("0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", "ETH / USD"),
}
ANSWER_UPDATED = "AnswerUpdated(int256,uint256,uint256)"

HTTP_PROBES = {
    "pyth_tradingview_shim_history": "https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol=Crypto.USDC/USD"
                                     "&resolution=60&from=1678233600&to=1678320000",
    "pyth_tradingview_shim_symbols": "https://benchmarks.pyth.network/v1/shims/tradingview/symbols?symbol=Crypto.USDC/USD",
    "pyth_price_feeds_search": "https://benchmarks.pyth.network/v1/price_feeds?query=USDC&asset_type=crypto",
    "pyth_updates_price_historical": "https://benchmarks.pyth.network/v1/updates/price/1678492800"
                                     "?ids[]=eaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a&parsed=true",
    "cryptocompare_histohour_usdc": "https://min-api.cryptocompare.com/data/v2/histohour?fsym=USDC&tsym=USD&limit=24&toTs=1678320000",
}


# --- ABI / log decoding ------------------------------------------------------------------------------

def topic0(signature: str = ANSWER_UPDATED) -> str:
    return "0x" + keccak256(signature.encode()).hex()


def _word(hexstr: str, i: int) -> str:
    h = hexstr[2:] if hexstr.startswith("0x") else hexstr
    return h[64 * i:64 * (i + 1)]


def to_int256(word_hex: str) -> int:
    v = int(word_hex, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def decode_answer_updated(log: dict[str, Any]) -> dict[str, Any]:
    """Decode an AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt) log."""
    topics = log["topics"]
    if len(topics) != 3 or topics[0].lower() != topic0():
        raise ValueError("not an AnswerUpdated log")
    return {"answer": to_int256(topics[1][2:]), "round_id": int(topics[2], 16), "updated_at": int(_word(log["data"], 0), 16),
            "block": int(log["blockNumber"], 16), "tx_hash": log["transactionHash"], "log_index": int(log["logIndex"], 16)}


def decode_string(result: str) -> str:
    offset = int(_word(result, 0), 16) // 32
    n = int(_word(result, offset), 16)
    body = result[2:][64 * (offset + 1):64 * (offset + 1) + 2 * n]
    return bytes.fromhex(body).decode("utf-8", "replace")


def decode_round_data(result: str) -> dict[str, int]:
    names = ("round_id", "answer", "started_at", "updated_at", "answered_in_round")
    return {n: (to_int256(_word(result, i)) if n == "answer" else int(_word(result, i), 16)) for i, n in enumerate(names)}


def fetch_logs(call: Callable[[str, list[Any]], Any], address: str, first: int, last: int, *, chunk: int = 20_000,
               min_chunk: int = 500) -> list[dict[str, Any]]:
    """AnswerUpdated logs for blocks [first, last]; halves the chunk when the provider rejects the range."""
    out: list[dict[str, Any]] = []
    start = first
    while start <= last:
        end = min(start + chunk - 1, last)
        try:
            logs = call("eth_getLogs", [{"address": address, "fromBlock": hex(start), "toBlock": hex(end), "topics": [topic0()]}])
        except RpcError:
            if chunk <= min_chunk:
                raise
            chunk //= 2
            continue
        out.extend(logs)
        start = end + 1
    return out


# --- metrics -----------------------------------------------------------------------------------------

def bps_error(feed: pd.Series, ref: pd.Series) -> pd.Series:
    """1e4 * (log feed - log ref) on the common index; positive = feed above the reference."""
    both = pd.concat([feed, ref], axis=1, join="inner").dropna()
    return 1e4 * (np.log(both.iloc[:, 0]) - np.log(both.iloc[:, 1]))


def error_summary(err: pd.Series) -> dict[str, Any]:
    e = err.dropna()
    if e.empty:
        return {"n": 0}
    a = e.abs()
    return {"n": int(len(e)), "median_signed_bps": float(e.median()), "median_abs_bps": float(a.median()),
            "p95_abs_bps": float(a.quantile(0.95)), "max_abs_bps": float(a.max()), "max_signed_bps": float(e.loc[a.idxmax()]),
            "n_ge_50": int((a >= 50).sum()), "n_ge_100": int((a >= 100).sum())}


def feed_as_of(rounds: pd.DataFrame, labels: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Feed price and age (seconds) at the close of each minute bar: the last round with updated_at <= label+60s."""
    r = rounds.sort_values(["updated_at", "round_id"])
    upd = r["updated_at"].to_numpy(dtype="int64")
    px = r["price"].to_numpy()
    t = labels.asi8 // 10**9 + 60
    idx = np.searchsorted(upd, t, side="right") - 1
    ok = idx >= 0
    price = np.where(ok, px[np.clip(idx, 0, None)], np.nan)
    age = np.where(ok, t - upd[np.clip(idx, 0, None)], np.nan)
    return pd.Series(price, index=labels), pd.Series(age, index=labels)


def best_lag(feed: pd.Series, ref: pd.Series, *, max_lag: int = 120) -> dict[str, Any]:
    """Lag k (minutes) minimising mean |bps error| of feed(m) vs ref(m-k): how far behind the reference the feed runs."""
    maes = {}
    for k in range(0, max_lag + 1):
        e = bps_error(feed, ref.shift(k, freq="1min")).abs()
        if len(e) > 30:
            maes[k] = float(e.mean())
    if not maes:
        return {"lag_min": None}
    k = min(maes, key=maes.get)
    return {"lag_min": int(k), "mae_at_best_bps": maes[k], "mae_at_zero_bps": maes.get(0)}


def staleness(rounds: pd.DataFrame, ref: pd.Series, labels: pd.DatetimeIndex, *, move_bps: float = 50.0) -> dict[str, Any]:
    """Age of the feed's last update at minutes where the reference had moved more than ``move_bps`` since that update."""
    _, age = feed_as_of(rounds, labels)
    upd_s = labels.asi8 // 10**9 + 60 - age.to_numpy()
    ref_at_update = ref.reindex(pd.to_datetime(np.floor(upd_s / 60) * 60 - 60, unit="s", utc=True))
    moved = 1e4 * (np.log(ref.reindex(labels).to_numpy()) - np.log(ref_at_update.to_numpy()))
    stale = pd.Series(age.to_numpy()[np.abs(moved) > move_bps] / 60.0)
    out: dict[str, Any] = {"minutes_ref_moved_gt_%dbps_since_last_update" % move_bps: int(len(stale)),
                           "minutes_observed": int(np.isfinite(moved).sum())}
    if len(stale):
        out.update({"age_median_min": float(stale.median()), "age_p95_min": float(stale.quantile(0.95)), "age_max_min": float(stale.max())})
    return out


def update_stats(rounds: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    r = rounds.sort_values("updated_at")
    ts = pd.to_datetime(r["updated_at"], unit="s", utc=True)
    inw = r[(ts >= start) & (ts < end)]
    gaps = r["updated_at"].diff().dropna() / 60.0
    gaps = gaps[(pd.to_datetime(r["updated_at"], unit="s", utc=True).iloc[1:] >= start).to_numpy()
                & (pd.to_datetime(r["updated_at"], unit="s", utc=True).iloc[1:] < end).to_numpy()]
    out: dict[str, Any] = {"updates_in_window": int(len(inw))}
    if len(gaps):
        out.update({"gap_median_min": float(gaps.median()), "gap_p95_min": float(gaps.quantile(0.95)), "gap_max_min": float(gaps.max())})
    return out


def infer_policy(rounds: pd.DataFrame) -> dict[str, Any]:
    """Heartbeat and deviation threshold inferred from the data (NOT from documentation)."""
    r = rounds.sort_values("updated_at")
    gap_min = r["updated_at"].diff() / 60.0
    move = 1e4 * np.log(r["price"]).diff().abs()
    if gap_min.dropna().empty:
        return {}
    hb = float(gap_min.max())
    # updates that arrive well before the heartbeat were triggered by deviation; their move is >= the threshold
    dev = move[(gap_min < 0.8 * hb)].dropna()
    return {"heartbeat_max_gap_min": hb, "heartbeat_gap_p99_min": float(gap_min.quantile(0.99)),
            "deviation_triggered_move_min_bps": float(dev.min()) if len(dev) else None,
            "deviation_triggered_move_p05_bps": float(dev.quantile(0.05)) if len(dev) else None, "basis": "inferred from observed rounds"}


def ols(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 5 or np.ptp(x) == 0:
        return {"n": int(len(x))}
    slope, icpt = np.polyfit(x, y, 1)
    res = y - (slope * x + icpt)
    r2 = 1 - res.var() / y.var() if y.var() > 0 else float("nan")
    se = float(np.sqrt(res.var(ddof=2) / (len(x) * x.var())))
    return {"n": int(len(x)), "slope": float(slope), "intercept_bps": float(icpt), "r2": float(r2), "slope_se_naive": se,
            "corr": float(np.corrcoef(x, y)[0, 1])}


# --- raw acquisition -----------------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ts_of(date: str) -> int:
    return int(pd.Timestamp(date, tz="UTC").timestamp())


def find_blocks(call: Budgeted, state: dict[str, Any]) -> None:
    """Last block at or before each window boundary; the search is bracketed by blocks known to span Feb-Apr 2023."""
    blocks = state.setdefault("blocks", {})
    lo_n, hi_n = 16_000_000, 17_100_000

    def ts(n: int) -> int:
        return int(call("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)

    lo, hi, t_lo, t_hi = lo_n, hi_n, ts(lo_n), ts(hi_n)
    for w, (a, b) in WINDOWS.items():
        for tag, date in ((f"{w}_start", a), (f"{w}_end", b)):
            if tag in blocks:
                continue
            target = ts_of(date)
            assert t_lo <= target < t_hi
            l, h, tl, th = lo, hi, t_lo, t_hi
            while h - l > 1:
                g = l + int((target - tl) * (h - l) / max(th - tl, 1)) if h - l >= 64 else (l + h) // 2
                g = min(max(g, l + 1), h - 1)
                tg = ts(g)
                if tg <= target:
                    l, tl = g, tg
                else:
                    h, th = g, tg
            blocks[tag] = l


def read_boundaries(call: Budgeted, state: dict[str, Any]) -> None:
    feeds = state.setdefault("feeds", {})
    blocks = state["blocks"]
    for name, (proxy, expect) in FEEDS.items():
        f = feeds.setdefault(name, {"proxy": proxy})
        if "boundary" in f:
            continue
        at = hex(blocks["depeg_start"])
        f["description"] = decode_string(call("eth_call", [{"to": proxy, "data": calldata("description()")}, at]))
        f["description_matches"] = f["description"] == expect
        f["decimals"] = int(call("eth_call", [{"to": proxy, "data": calldata("decimals()")}, at]), 16)
        f["aggregators_by_block"] = {tag: "0x" + call("eth_call", [{"to": proxy, "data": calldata("aggregator()")}, hex(blocks[tag])])[-40:]
                                     for tag in ("calm_start", "depeg_start", "depeg_end")}
        f["boundary"] = {tag: decode_round_data(call("eth_call", [{"to": proxy, "data": calldata("latestRoundData()")}, hex(blk)]))
                         for tag, blk in blocks.items()}


SUB_WINDOWS = {"core": ("2023-03-10 12:00", "2023-03-13 18:00"), "calm_sub": ("2023-02-20", "2023-02-23"),
               "dai_trough": ("2023-03-11 06:00", "2023-03-11 11:00")}
# Round-by-round budget plan, in priority order: (feed, label); "depeg"/"calm" are the full windows.
ROUND_PLAN = [("USDC/USD", "depeg"), ("USDC/USD", "calm"), ("USDT/USD", "depeg"), ("USDT/USD", "calm"),
              ("BTC/USD", "core"), ("ETH/USD", "core"), ("BTC/USD", "calm_sub"), ("ETH/USD", "calm_sub"),
              ("DAI/USD", "dai_trough"), ("DAI/USD", "core"), ("DAI/USD", "calm_sub")]


def est_block(blocks: dict[str, int], t: int) -> int:
    """Block number at time t by linear interpolation between the exact depeg-window anchors (error of order a minute)."""
    t0, t1 = ts_of(WINDOWS["depeg"][0]), ts_of(WINDOWS["depeg"][1])
    return int(blocks["depeg_start"] + (t - t0) * (blocks["depeg_end"] - blocks["depeg_start"]) / (t1 - t0))


def sub_bounds(call: Budgeted, state: dict[str, Any], labels: set[str]) -> None:
    """Round ids at the edges of the sub-windows: latestRoundData at the interpolated block (+/- 100 blocks of margin)."""
    for name, label in ROUND_PLAN:
        if label not in labels:
            continue
        f = state["feeds"][name]
        sub = f.setdefault("sub", {})
        if label in sub:
            continue
        a, b = (ts_of(x.replace(" ", "T") + ":00+00:00") if " " in x else ts_of(x) for x in SUB_WINDOWS[label])
        ids = [decode_round_data(call("eth_call", [{"to": f["proxy"], "data": calldata("latestRoundData()")}, hex(est_block(state["blocks"], t) + m)]))
               for t, m in ((a, -100), (b, 100))]
        sub[label] = {"first": ids[0]["round_id"], "last": ids[1]["round_id"], "window": SUB_WINDOWS[label]}


def fetch_rounds(call: Budgeted, state: dict[str, Any], plan: list[tuple[str, str]]) -> None:
    """One eth_call getRoundData(roundId) per round: the free RPC tier caps eth_getLogs at 10 blocks per request."""
    for name, label in plan:
        f = state["feeds"][name]
        rounds = f.setdefault("rounds", {})
        if label in ("depeg", "calm"):
            first, last = f["boundary"][f"{label}_start"]["round_id"], f["boundary"][f"{label}_end"]["round_id"]
        else:
            first, last = f["sub"][label]["first"], f["sub"][label]["last"]
        if first >> 64 != last >> 64:
            raise StopRun(f"{name}: aggregator phase changed inside the {label} window")
        for rid in range(first, last + 1):
            if str(rid) not in rounds:
                rounds[str(rid)] = decode_round_data(call("eth_call", [{"to": f["proxy"], "data": calldata("getRoundData(uint80)", rid)}, "latest"]))
        f.setdefault("rounds_done", []).append(label)


def http_get(url: str, path: Path) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "www-stablecoin-research/0.1 (audit pilot)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, body = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, body = exc.code, exc.read()
    path.write_bytes(body)
    return {"url": url, "http_status": status, "bytes": len(body), "sha256": sha256_bytes(body), "file": str(path)}


def fetch_all(stage: str = "boundaries", labels: set[str] | None = None, max_calls: int | None = None, budget_total: int = TOTAL_RPC_BUDGET) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    counter, state_path = RAW / "rpc_calls_used.json", RAW / "chainlink_state.json"
    prior = json.loads(counter.read_text())["calls_used"] if counter.exists() else 0
    if not (RAW / "http_probes.json").exists():
        probes = {}
        for k, url in HTTP_PROBES.items():
            probes[k] = http_get(url, RAW / f"probe_{k}.txt")
            time.sleep(HTTP_SPACING)
        (RAW / "http_probes.json").write_text(json.dumps(probes, indent=1))
    endpoint = endpoint_from_env()
    if not endpoint:
        raise SystemExit("Set WWW_ETH_RPC_URL in .env (git-ignored).")
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    allowed = budget_total - prior if max_calls is None else min(max_calls, budget_total - prior)
    rpc = Budgeted(lambda m, p: rpc_call(endpoint, m, p), allowed, RPC_SPACING)
    status = "OK"
    try:
        if rpc("eth_chainId", []) != "0x1":
            raise StopRun("wrong chain")
        find_blocks(rpc, state)
        read_boundaries(rpc, state)
        if stage in ("subbounds", "rounds"):
            sub_bounds(rpc, state, set(SUB_WINDOWS))
        if stage == "rounds":
            fetch_rounds(rpc, state, [(n, l) for n, l in ROUND_PLAN if labels is None or l in labels])
    except StopRun as exc:
        status = f"STOPPED: {exc}"
    finally:
        by: dict[str, int] = {}
        for entry in rpc.log:
            by[entry["method"]] = by.get(entry["method"], 0) + 1
        text = json.dumps(state, indent=1)
        if endpoint in text:
            raise SystemExit("refusing to write output containing the endpoint")
        state_path.write_text(text)
        hist = json.loads(counter.read_text()) if counter.exists() else {"runs": []}
        hist["runs"].append({"calls": rpc.used, "by_method": by, "status": status, "stage": stage})
        hist["calls_used"] = prior + rpc.used
        counter.write_text(json.dumps(hist, indent=1))
    print(f"{status}; rpc calls this run {rpc.used}, cumulative {prior + rpc.used}/{budget_total}")


# --- unit-corrected reference ------------------------------------------------------------------------------

MANIFEST = Path("reports/events/acquisition_manifest.json")
MONTHS = ["2023-02", "2023-03"]


def _traded(grid: pd.DataFrame, prefix: str) -> pd.Series:
    traded = grid[f"{prefix}_traded"].astype(bool)
    s = grid.loc[traded, f"{prefix}_close"].astype(float)
    s.index = s.index.rename(None)
    return s


def load_candles(root: Path = Path("data/raw")) -> dict[str, pd.Series]:
    """Traded-minute closes (minute-bar label, close at label+60s) per venue/pair; hash-verified through the repo loaders."""
    from www_events.binance_klines import read_kline_zip, to_minute_grid, verify_checksum
    from www_events.candles import load_venue_months

    out: dict[str, pd.Series] = {}
    for venue, folder, pairs in (("bitstamp", "bitstamp", ("USDCUSD", "USDTUSD", "BTCUSD", "ETHUSD")),
                                 ("coinbase", "coinbase", ("BTCUSD", "ETHUSD"))):
        for pair in pairs:
            grid, _ = load_venue_months(root / folder, pair, "x", MANIFEST, venue, MONTHS)
            out[f"{venue}:{pair}"] = _traded(grid, "x")
    for pair in ("USDCUSD", "BTCUSD", "DAIUSD"):
        frames = []
        for m in MONTHS:
            archive = root / "binance_us" / f"{pair}-1m-{m}.zip"
            verify_checksum(archive, archive.with_name(archive.name + ".CHECKSUM"))
            frames.append(read_kline_zip(archive).frame)
        frame = pd.concat(frames).sort_index()
        grid = to_minute_grid(frame, frame.index[0].floor("D"), frame.index[-1].floor("D") + pd.Timedelta("1D"), "x")
        out[f"binance_us:{pair}"] = _traded(grid, "x")
    return out


def build_references(c: dict[str, pd.Series]) -> tuple[dict[str, pd.Series], dict[str, Any]]:
    """Reference USD prices on a minute grid. See module docs: USDC/USDT from Bitstamp, BTC/ETH median of Bitstamp+Coinbase,
    Binance.US stablecoin prices corrected by the ledger-dollar offset L (Binance.US vs Bitstamp BTC/USD)."""
    grid = pd.date_range("2023-02-01", "2023-03-31 23:59", freq="1min", tz="UTC")
    full = lambda s, lim: s.reindex(grid).ffill(limit=lim)
    diag: dict[str, Any] = {}
    ref = {"USDC/USD": full(c["bitstamp:USDCUSD"], 60), "USDT/USD": full(c["bitstamp:USDTUSD"], 60)}
    for coin in ("BTC", "ETH"):
        b, k = full(c[f"bitstamp:{coin}USD"], 5), full(c[f"coinbase:{coin}USD"], 5)
        ref[f"{coin}/USD"] = np.exp((np.log(b) + np.log(k)) / 2)  # median of two = mean
        both = pd.concat([c[f"bitstamp:{coin}USD"], c[f"coinbase:{coin}USD"]], axis=1, join="inner").dropna()
        gap = 1e4 * (np.log(both.iloc[:, 0]) - np.log(both.iloc[:, 1])).abs()
        diag[f"{coin}_bitstamp_vs_coinbase_abs_gap_bps"] = {
            w: {"median": float(g.median()), "p95": float(g.quantile(0.95)), "max": float(g.max())}
            for w, g in ((w, gap[(gap.index >= pd.Timestamp(a, tz="UTC")) & (gap.index < pd.Timestamp(z, tz="UTC"))]) for w, (a, z) in WINDOWS.items())}
    both = pd.concat([c["binance_us:BTCUSD"], c["bitstamp:BTCUSD"]], axis=1, join="inner").dropna()
    off = (1e4 * (np.log(both.iloc[:, 0]) - np.log(both.iloc[:, 1]))).reindex(grid)
    L = off.rolling(30, min_periods=5).median().ffill(limit=30)
    diag["ledger_offset_L_bps"] = {w: {"median": float(L[a:z].median()), "p05": float(L[a:z].quantile(0.05)), "p95": float(L[a:z].quantile(0.95))}
                                   for w, (a, z) in WINDOWS.items()}
    ref["USDC/USD:binance_us_minus_L"] = full(c["binance_us:USDCUSD"], 60) * np.exp(-L / 1e4)
    ref["DAI/USD"] = full(c["binance_us:DAIUSD"], 60) * np.exp(-L / 1e4)
    # agreement of the two USDC references on minutes where both venues traded
    a_, b_ = c["bitstamp:USDCUSD"], c["binance_us:USDCUSD"]
    idx = a_.index.intersection(b_.index)
    cross = (b_.reindex(idx) * np.exp(-L.reindex(idx) / 1e4)).dropna()
    d = 1e4 * (np.log(cross) - np.log(a_.reindex(cross.index)))
    agree: dict[str, Any] = {}
    for w, (a, z) in WINDOWS.items():
        x = d[(d.index >= pd.Timestamp(a, tz="UTC")) & (d.index < pd.Timestamp(z, tz="UTC"))]
        y = cross[x.index]
        agree[w] = {"n_common_traded_minutes": int(len(x)), "median_diff_bps": float(x.median()) if len(x) else None,
                    "median_abs_diff_bps": float(x.abs().median()) if len(x) else None,
                    "p95_abs_diff_bps": float(x.abs().quantile(0.95)) if len(x) else None,
                    "corr_levels": float(np.corrcoef(np.log(y), np.log(a_.reindex(x.index)))[0, 1]) if len(x) > 10 and w == "depeg" else None}
    dep = ref["USDC/USD"][WINDOWS["depeg"][0]:WINDOWS["depeg"][1]]
    dep2 = ref["USDC/USD:binance_us_minus_L"][WINDOWS["depeg"][0]:WINDOWS["depeg"][1]]
    agree["depeg_min_price"] = {"bitstamp": float(dep.min()), "bitstamp_at": str(dep.idxmin()),
                                "binance_us_minus_L": float(dep2.min()), "binance_us_minus_L_at": str(dep2.idxmin()),
                                "binance_us_raw_min": float(c["binance_us:USDCUSD"][WINDOWS["depeg"][0]:WINDOWS["depeg"][1]].min())}
    diag["usdc_reference_agreement"] = agree
    return ref, diag


# --- per feed / window analysis -------------------------------------------------------------------------------

def longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for v in mask:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def rounds_frame(feed_state: dict[str, Any]) -> pd.DataFrame:
    dec = feed_state["decimals"]
    rows = [{"round_id": int(k), "price": v["answer"] / 10**dec, "updated_at": v["updated_at"], "started_at": v["started_at"]}
            for k, v in feed_state.get("rounds", {}).items()]
    return pd.DataFrame(rows).sort_values("round_id").reset_index(drop=True)


def analyse_window(rounds: pd.DataFrame, ref: pd.Series, start: str, end: str) -> dict[str, Any]:
    a, z = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    labels = pd.date_range(a, z, freq="1min", inclusive="left")
    price, _ = feed_as_of(rounds, labels)
    err = bps_error(price, ref.reindex(labels))
    hourly = err[err.index.minute == 59]
    per_round = []
    for _, r in rounds[(rounds.updated_at >= a.timestamp()) & (rounds.updated_at < z.timestamp())].iterrows():
        t = pd.Timestamp(int(r.updated_at) // 60 * 60 - 60, unit="s", tz="UTC")
        if t in ref.index and np.isfinite(ref[t]):
            per_round.append(1e4 * (np.log(r.price) - np.log(ref[t])))
    first_ok = bool(rounds["updated_at"].min() <= a.timestamp())
    a_abs = err.abs().to_numpy()
    out = {"window": [start, end], "covers_window_start": first_ok, "minutes_compared": int(len(err)),
           "minute_error": error_summary(err), "hourly_error": error_summary(hourly), "per_round_error": error_summary(pd.Series(per_round, dtype=float)),
           "minutes_abs_ge_50": int((a_abs >= 50).sum()), "minutes_abs_ge_100": int((a_abs >= 100).sum()),
           "longest_run_minutes_abs_ge_50": longest_run(a_abs >= 50), "longest_run_minutes_abs_ge_100": longest_run(a_abs >= 100),
           "hours_any_minute_abs_ge_50": int((err.abs().groupby(err.index.floor("h")).max() >= 50).sum()),
           "lag": best_lag(price, ref), "staleness": staleness(rounds, ref, labels),
           "updates": update_stats(rounds, a, z), "inferred_policy": infer_policy(
               rounds[(rounds.updated_at >= a.timestamp()) & (rounds.updated_at < z.timestamp())])}
    out["_hourly"] = hourly
    return out


def contamination(feed_err_hourly: pd.Series, usdc_ref: pd.Series) -> dict[str, Any]:
    """Regress a feed's hourly error on the USDC depeg size D = -1e4 log(USDC/USD) (positive when USDC is below $1)."""
    D = (-1e4 * np.log(usdc_ref)).reindex(feed_err_hourly.index)
    ok = D.notna() & feed_err_hourly.notna()
    x, y = D[ok].to_numpy(), feed_err_hourly[ok].to_numpy()
    out = {"levels": ols(x, y), "first_differences": ols(np.diff(x), np.diff(y)), "D_max_bps": float(x.max()) if len(x) else None}
    big = ok & (D >= 100)
    out["hours_with_D_ge_100bps"] = int(big.sum())
    if big.any():
        out["median_feed_error_when_D_ge_100_bps"] = float(feed_err_hourly[big].median())
        out["median_D_when_D_ge_100_bps"] = float(D[big].median())
    small = ok & (D < 25)
    out["median_feed_error_when_D_lt_25_bps"] = float(feed_err_hourly[small].median()) if small.any() else None
    return out


def manifest_of(directory: Path) -> list[dict[str, Any]]:
    return [{"file": str(p), "bytes": p.stat().st_size, "sha256": sha256_bytes(p.read_bytes())} for p in sorted(directory.glob("*")) if p.is_file()]


def analyse(out_json: Path = Path("reports/audit/usdc_2023_pilot.json")) -> dict[str, Any]:
    state = json.loads((RAW / "chainlink_state.json").read_text())
    ref, diag = build_references(load_candles())
    results: dict[str, Any] = {}
    hourly: dict[tuple[str, str], pd.Series] = {}
    for name, f in state["feeds"].items():
        rounds = rounds_frame(f)
        if rounds.empty or name not in ref:
            results[name] = {"status": "rounds not pulled (budget)", "description": f["description"]}
            continue
        done = f.get("rounds_done", [])
        if name == "DAI/USD":  # budget left only for the 5-hour trough slice
            rounds = rounds[rounds.round_id >= f["sub"]["dai_trough"]["first"]].reset_index(drop=True)
            wins = {"depeg": SUB_WINDOWS["dai_trough"]}
        elif name in ("USDC/USD", "USDT/USD"):
            wins = {"depeg": WINDOWS["depeg"], "calm": WINDOWS["calm"]}
        else:
            wins = {"depeg": tuple(x + (":00" if " " in x else "") for x in SUB_WINDOWS["core"]), "calm": SUB_WINDOWS["calm_sub"]}
        res = {"proxy": f["proxy"], "description": f["description"], "description_matches_expected": f["description_matches"],
               "decimals": f["decimals"], "aggregators_seen": sorted(set(f["aggregators_by_block"].values())), "rounds_pulled": int(len(rounds)),
               "round_sets_completed": done, "windows": {}}
        for w, (a, z) in wins.items():
            r = analyse_window(rounds, ref[name], a, z)
            hourly[(name, w)] = r.pop("_hourly")
            res["windows"][w] = r
        if name in ("USDC/USD", "USDT/USD"):  # same window as BTC/ETH for a like-for-like comparison
            a, z = (x + (":00" if " " in x else "") for x in SUB_WINDOWS["core"])
            r = analyse_window(rounds, ref[name], a, z)
            hourly[(name, "core")] = r.pop("_hourly")
            res["windows"]["core_like_btc_eth"] = r
        if name == "USDC/USD":  # robustness: second, independent unit-corrected reference
            res["windows_vs_binance_us_minus_L"] = {}
            for w, (a, z) in {**wins, "core_like_btc_eth": tuple(x + (":00" if " " in x else "") for x in SUB_WINDOWS["core"])}.items():
                r = analyse_window(rounds, ref["USDC/USD:binance_us_minus_L"], a, z)
                r.pop("_hourly")
                res["windows_vs_binance_us_minus_L"][w] = r
        results[name] = res
    # key question: contamination of BTC/USD and ETH/USD by the USDC unit
    cont: dict[str, Any] = {}
    for name in ("BTC/USD", "ETH/USD", "USDT/USD"):
        key = (name, "depeg") if name != "USDT/USD" else (name, "core")
        if key in hourly:
            cont[name] = {"core_window_hourly": contamination(hourly[key], ref["USDC/USD"])}
            cont[name]["core_window_hourly_usdc_ref_binance_us_minus_L"] = contamination(hourly[key], ref["USDC/USD:binance_us_minus_L"])
    if ("USDC/USD", "core") in hourly:
        cont["USDC/USD (feed itself)"] = {"core_window_hourly": contamination(hourly[("USDC/USD", "core")], ref["USDC/USD"])}
    worst = []
    if ("BTC/USD", "depeg") in hourly and ("ETH/USD", "depeg") in hourly:
        D = (-1e4 * np.log(ref["USDC/USD"])).reindex(hourly[("BTC/USD", "depeg")].index)
        t = pd.DataFrame({"D_bps": D, "btc_feed_err_bps": hourly[("BTC/USD", "depeg")], "eth_feed_err_bps": hourly[("ETH/USD", "depeg")]})
        if ("USDC/USD", "core") in hourly:
            t["usdc_feed_err_bps"] = hourly[("USDC/USD", "core")]
        worst = [{"hour_end_utc": str(i + pd.Timedelta("1min")), **{k: (None if pd.isna(v) else round(float(v), 1)) for k, v in row.items()}}
                 for i, row in t.sort_values("D_bps", ascending=False).head(12).iterrows()]
    out = {"episode": "USDC depeg, March 2023 (SVB)", "windows_utc": WINDOWS, "sub_windows_utc": SUB_WINDOWS,
           "reference_diagnostics": diag, "feeds": results, "contamination": cont, "peak_depeg_hours": worst,
           "rpc": json.loads((RAW / "rpc_calls_used.json").read_text()), "http_probes": json.loads((RAW / "http_probes.json").read_text()),
           "manifest": manifest_of(RAW), "blocks": state["blocks"]}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["fetch", "analyze"], required=True)
    parser.add_argument("--fetch-stage", choices=["boundaries", "subbounds", "rounds"], default="boundaries")
    parser.add_argument("--max-calls", type=int)
    args = parser.parse_args()
    if args.stage == "fetch":
        fetch_all(args.fetch_stage, max_calls=args.max_calls)
    else:
        analyse()
        print("wrote reports/audit/usdc_2023_pilot.json")


if __name__ == "__main__":
    main()
