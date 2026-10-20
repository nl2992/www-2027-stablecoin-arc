"""Synthetic, offline checks for the continuous detector evaluation (software validation, not research results)."""

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from www_rescue import detector_eval as de
from www_rescue.detector_eval import Episode, VenueData

D = date.fromisoformat


def hours(start, n):
    return pd.date_range(start, periods=n, freq="1h", tz="UTC")


def flag_series(start, n, on=()):
    """All-False evaluated hours; ``on`` = (day, count) pairs set True from hour 0 of that day."""
    s = pd.Series(False, index=hours(start, n))
    for day, count in on:
        t = pd.Timestamp(day, tz="UTC")
        s.loc[t: t + pd.Timedelta(hours=count - 1)] = True
    return s


def pos(id_, report, end=None, venue="bitfinex"):
    r = D(report)
    return Episode(id_, venue, "deposit_pause", r, de.truth_window(r, D(end) if end else None), True)


def conf(id_, lo, hi, venue="bitfinex"):
    return Episode(id_, venue, "confounder", D(lo), (D(lo), D(hi)), False)


# ---------------------------------------------------------------- flags, days, episodes

def test_hour_flags_rule_and_evaluated_hours():
    idx = hours("2020-01-01", 5)
    L = pd.Series([150, 150, 50, 150, 150.0], idx)
    S = pd.Series([150, 100, 50, 120, np.nan], idx)
    f = de.hour_flags(L, S)
    assert list(f.index) == list(idx[:4])  # hour 4 has no S: not evaluated
    assert list(f) == [True, False, False, True]  # |100-150|=50 > 37.5; |120-150|=30 <= 37.5; |L|=50 < 100
    assert list(de.hour_flags(L, S, threshold=50)) == [True, False, True, True]
    assert list(de.hour_flags(L, S, agree=0.5)) == [True, True, False, True]


def test_gap_flags_ignore_the_second_asset():
    L = pd.Series([150, -150, 99.9, np.nan], hours("2020-01-01", 4))
    assert list(de.gap_flags(L)) == [True, True, False]


def test_alarm_days_need_min_hours():
    s = flag_series("2020-01-01", 72, [("2020-01-01", 6), ("2020-01-02", 5), ("2020-01-03", 12)])
    assert de.alarm_days(s) == [D("2020-01-01"), D("2020-01-03")]
    assert de.alarm_days(s, min_hours=3) == [D("2020-01-01"), D("2020-01-02"), D("2020-01-03")]
    assert de.alarm_days(s, min_hours=12) == [D("2020-01-03")]


def test_episodes_merge_when_gap_is_three_or_fewer_days():
    days = [D(x) for x in ("2020-01-01", "2020-01-02", "2020-01-06", "2020-01-11")]
    # 01-02 -> 01-06: three non-alarm days (3,4,5) merge; 01-06 -> 01-11: four (7..10) do not
    assert de.alarm_episodes(days) == [(D("2020-01-01"), D("2020-01-06")), (D("2020-01-11"), D("2020-01-11"))]
    assert de.alarm_episodes(days, merge_gap_days=4) == [(D("2020-01-01"), D("2020-01-11"))]
    assert de.alarm_episodes(days, merge_gap_days=0)[0] == (D("2020-01-01"), D("2020-01-02"))
    assert de.alarm_episodes([]) == []


# ---------------------------------------------------------------- baselines

def test_b2_matches_hand_computation_and_skips_warmup():
    L = pd.Series([1.0, -1.0] * 50 + [6.0, 5.0], hours("2020-01-01", 102))
    f = de.robust_z_flags(L, min_obs=24)
    assert f.index[0] == L.index[24]  # the first 24 hours have no trailing window
    # trailing 100 values alternate +-1: median 0, MAD 1, cutoff 4 * 1.4826 = 5.93
    assert bool(f.loc[L.index[100]]) is True  # 6 >= 5.93
    assert bool(f.loc[L.index[101]]) is False  # 5 < 5.93 (window now holds the 6 as well; median and MAD stay near 0 and 1)
    assert not f.loc[f.index < L.index[100]].any()  # odd-count windows with MAD 0 are not evaluated


def test_b2_uses_trailing_window_only_no_look_ahead():
    rng = np.random.default_rng(1)
    base = pd.Series(rng.normal(0, 10, 400), hours("2020-01-01", 400))
    f0 = de.robust_z_flags(base, window="5D", min_obs=24)
    bumped = base.copy()
    bumped.iloc[300:] += 5000.0  # future shock from hour 300 on
    f1 = de.robust_z_flags(bumped, window="5D", min_obs=24)
    before = f0.index[f0.index < base.index[300]]
    assert list(f1.loc[before]) == list(f0.loc[before])  # nothing earlier moves
    assert f1.loc[base.index[300]]  # the shock hour is judged against the past only
    spike = base.copy()
    spike.iloc[200] = 1e6  # the current hour is excluded from its own window, so a spike cannot hide itself
    assert de.robust_z_flags(spike, window="5D", min_obs=24).loc[base.index[200]]


def test_b3_premium_flags():
    D_ = pd.Series([120, -100, 99, np.nan], hours("2020-01-01", 4))
    assert list(de.premium_flags(D_)) == [True, True, False]


# ---------------------------------------------------------------- labels

def write_labels(tmp_path):
    eps = [
        {"id": "A", "venue": "Binance.US", "type": "rail_shutdown", "first_public_report_date": "2023-06-09",
         "impairment_start": "2023-06-05", "impairment_end": None},
        {"id": "B", "venue": "binance-us", "type": "banking_partner_loss", "first_public_report_date": "2023-06-13",
         "impairment_end": "2023-08-01"},
        {"id": "C", "venue": "binance_us", "type": "confounder", "first_public_report_date": "2023-03-10",
         "impairment_start": "2023-03-10", "impairment_end": "2023-03-12"},
        {"id": "D", "venue": "Bitfinex", "type": "withdrawal_delay", "first_public_report_date": "2017-04-13"},
        {"id": "E", "venue": "Bitfinex", "type": "hack_note", "first_public_report_date": "2016-08-02"},
    ]
    p = tmp_path / "labels.json"
    p.write_text(json.dumps({"episodes": eps}))
    return p


def test_truth_window_and_venue_normalisation(tmp_path):
    p = write_labels(tmp_path)
    got = {e.id: e for e in de.load_labels(p, "Binance_US")}
    assert set(got) == {"A", "B", "C"}  # three spellings of one venue; Bitfinex entries excluded
    assert got["A"].window == (D("2023-05-10"), D("2023-09-07"))  # report - 30 d .. report + 90 d (no end documented)
    assert got["B"].window == (D("2023-05-14"), D("2023-08-01"))  # documented impairment_end
    assert got["A"].positive and got["B"].positive and not got["C"].positive
    assert got["C"].window == (D("2023-03-10"), D("2023-03-12"))
    assert [e.id for e in de.load_labels(p, "bitfinex")] == ["D"]  # unknown types are ignored
    assert de.norm_venue("Binance.US") == de.norm_venue("binance-us") == "binance_us"


# ---------------------------------------------------------------- scopes

def test_scope_masks():
    idx = pd.DatetimeIndex(pd.to_datetime(["2017-01-15", "2017-02-15", "2018-10-01", "2019-08-01", "2021-05-05"], utc=True))
    assert list(de.scope_mask(idx, "bitfinex", "seen")) == [False, True, True, False, False]
    assert list(de.scope_mask(idx, "bitfinex", "unseen")) == [True, False, False, True, True]
    assert de.scope_mask(idx, "coinbase", "seen").sum() == 0 and de.scope_mask(idx, "coinbase", "unseen").all()
    bus = pd.DatetimeIndex(pd.to_datetime(["2023-07-31 23:00", "2023-08-01 00:00"], utc=True))
    assert list(de.scope_mask(bus, "binance_us", "seen")) == [True, False]


# ---------------------------------------------------------------- metrics arithmetic

def make_eval():
    # 120 days of evaluated hours from 2020-01-01 (2880 h)
    s = flag_series("2020-01-01", 2880, [("2020-02-15", 6), ("2020-02-16", 8), ("2020-04-02", 6), ("2020-04-20", 6)])
    positives = [pos("A", "2020-02-20", end="2020-03-01"),  # window 2020-01-21..03-01, caught
                 pos("B", "2020-01-15", end="2020-01-20"),  # window 2019-12-16..01-20: 20/36 days with data, missed
                 pos("C", "2021-06-01")]  # no data at all: not covered
    confs = [conf("X", "2020-04-01", "2020-04-03")]
    return de.evaluate(s, positives, confs), s


def test_recall_lead_and_coverage():
    ev, _ = make_eval()
    by = {r["id"]: r for r in ev["positives"]}
    assert [by[k]["covered"] for k in "ABC"] == [True, True, False]
    assert ev["covered_positives"] == 2 and ev["caught"] == 1 and ev["recall"] == 0.5
    assert by["A"]["first_alarm_day"] == "2020-02-15" and by["A"]["lead_days"] == -5
    assert by["B"]["lead_days"] is None and not by["B"]["caught"]


def test_false_alarm_split_and_per_venue_year():
    ev, _ = make_eval()
    assert ev["episodes"] == [["2020-02-15", "2020-02-16"], ["2020-04-02", "2020-04-02"], ["2020-04-20", "2020-04-20"]]
    fa = ev["false_alarms"]
    assert (fa["n"], fa["confounder"], fa["unexplained"]) == (2, 1, 1)
    assert [f["class"] for f in fa["episodes"]] == ["confounder", "unexplained"]
    years = 2880 / (24 * 365.25)
    assert ev["venue_years"] == pytest.approx(years)
    assert fa["per_venue_year"]["unexplained"] == pytest.approx(1 / years)
    assert fa["per_venue_year"]["total"] == pytest.approx(2 / years)


def test_hour_level_precision_and_recall():
    ev, _ = make_eval()
    # flagged 6 + 8 + 6 + 6 = 26 h; 14 inside A's window (41 days = 984 h); B contributes 20 days of data = 480 h
    assert ev["flagged_hours"] == 26
    assert ev["hour_precision"] == pytest.approx(14 / 26)
    assert ev["hour_recall"] == pytest.approx(14 / (984 + 480))
    assert ev["episode_precision"] == pytest.approx(1 / 3)


def test_alarm_before_window_does_not_catch_and_late_alarm_has_no_lead():
    p = pos("A", "2020-02-20", end="2020-03-25")  # window 01-21..03-25
    early = de.evaluate(flag_series("2020-01-01", 2880, [("2020-01-02", 6)]), [p], [])
    assert early["positives"][0]["caught"] is False and early["false_alarms"]["n"] == 1
    late = de.evaluate(flag_series("2020-01-01", 2880, [("2020-03-25", 6)]), [p], [])
    r = late["positives"][0]
    assert r["caught"] is True and r["lead_days"] is None  # 03-25 is 34 days after the report: outside report + 30


def test_evaluation_with_no_data_is_safe():
    ev = de.evaluate(pd.Series(dtype=bool, index=pd.DatetimeIndex([], tz="UTC")), [pos("A", "2020-02-20")], [])
    assert ev["recall"] is None and ev["false_alarms"]["per_venue_year"]["unexplained"] is None
    assert de.evaluate(None, [], []) is None


# ---------------------------------------------------------------- leave-one-episode-out

def test_loeo_selects_grid_point_without_the_held_out_episode():
    idx = hours("2020-01-01", 400 * 24)
    L = pd.Series(0.0, idx)
    for day, val in (("2020-03-02", 150.0), ("2020-07-02", 250.0), ("2020-11-02", 250.0), ("2020-05-01", 150.0)):
        t = pd.Timestamp(day, tz="UTC")
        L.loc[t: t + pd.Timedelta(hours=7)] = val  # 8 flagged hours wherever the level is cleared
    vd = VenueData(L, L.copy())
    labels = {"bitfinex": [pos("Pa", "2020-03-01", end="2020-03-06"), pos("Pb", "2020-07-01", end="2020-07-06"),
                           pos("Pc", "2020-11-01", end="2020-11-06")]}  # 2020-05-01 is unexplained noise
    out = de.loeo({"bitfinex": vd}, labels)
    rows = {r["id"]: r for r in out["episodes"]}
    assert out["n"] == 3 and out["headline_recall"] == 1.0
    # without Pa, the 150 bps noise day hurts precision at 50 and 100 but not at 200: (200, 0.1) wins by grid order
    assert (rows["Pa"]["chosen_threshold"], rows["Pa"]["chosen_agreement"]) == (200.0, 0.1)
    assert rows["Pa"]["caught"] is False and rows["Pa"]["headline_caught"] is True
    # without Pb, 100 bps beats 200 (200 would miss Pa); the tie with 50 goes to the headline point
    assert (rows["Pb"]["chosen_threshold"], rows["Pb"]["chosen_agreement"]) == (100.0, 0.25)
    assert rows["Pb"]["caught"] and rows["Pb"]["lead_days"] == 1
    assert out["loeo_recall"] == pytest.approx(2 / 3)


# ---------------------------------------------------------------- P1-P4

def fake(*, n_fa=0, unexp=0.0, recall=None, covered=0, caught=0, leads=(), share=0.0, ndays=1000):
    return {"false_alarms": {"n": n_fa, "per_venue_year": {"unexplained": unexp}}, "recall": recall,
            "covered_positives": covered, "caught": caught, "alarm_day_share": share, "evaluated_days": ndays,
            "alarm_days": int(share * ndays),
            "positives": [{"id": f"e{i}", "caught": True, "lead_days": ld} for i, ld in enumerate(leads)]}


def results(*, p1_bfx=0.5, p1_cb=0.0, det_fa=1, b1_fa=3, det_rec=1.0, b1_rec=1.0, leads=(-3, 7), cb_share=0.0):
    return {"all": {"bitfinex": {"detector": fake(n_fa=det_fa, recall=det_rec, leads=leads, covered=1, caught=1),
                                 "b1": fake(n_fa=b1_fa, recall=b1_rec)},
                    "coinbase": {"detector": fake(share=cb_share), "b1": fake(n_fa=2)}},
            "unseen": {"bitfinex": {"detector": fake(unexp=p1_bfx)}, "coinbase": {"detector": fake(unexp=p1_cb)}}}


def test_predictions_all_pass():
    s = de.score_predictions(results())
    assert [s[k]["status"] for k in ("P1", "P2", "P3", "P4")] == ["PASS"] * 4 and s["falsified"] is False


def test_p1_boundary_and_falsification_needs_both_venues():
    assert de.score_predictions(results(p1_bfx=1.0, p1_cb=1.0))["P1"]["status"] == "PASS"  # at most 1 per venue-year
    one = de.score_predictions(results(p1_bfx=1.5))
    assert one["P1"]["status"] == "FAIL" and one["falsified"] is False  # P1 needs both; falsification needs both to fail
    both = de.score_predictions(results(p1_bfx=1.5, p1_cb=2.0))
    assert both["P1"]["status"] == "FAIL" and both["falsified"] is True


def test_p2_needs_no_more_false_alarms_and_no_lower_recall():
    assert de.score_predictions(results(det_fa=3, b1_fa=3))["P2"]["status"] == "PASS"
    worse = de.score_predictions(results(det_fa=4, b1_fa=3))
    assert worse["P2"]["status"] == "FAIL" and worse["falsified"] is True
    assert de.score_predictions(results(det_rec=0.5, b1_rec=1.0))["P2"]["status"] == "FAIL"


def test_p3_lead_limit_and_missing_lead():
    assert de.score_predictions(results(leads=(7,)))["P3"]["status"] == "PASS"
    late = de.score_predictions(results(leads=(-2, 8)))
    assert late["P3"]["status"] == "FAIL" and late["P3"]["violations"] == ["e1"]
    assert de.score_predictions(results(leads=(None,)))["P3"]["status"] == "FAIL"
    assert de.score_predictions(results(leads=()))["P3"]["status"] == "UNDEFINED"
    assert not de.score_predictions(results(leads=(30,)))["falsified"]  # P3 is not part of the falsification rule


def test_p4_alarm_share_is_strictly_below_one_percent():
    assert de.score_predictions(results(cb_share=0.0099))["P4"]["status"] == "PASS"
    assert de.score_predictions(results(cb_share=0.01))["P4"]["status"] == "FAIL"
    assert "undefined" in de.score_predictions(results())["P4"]["recall_note"]


# ---------------------------------------------------------------- end to end on synthetic data

def test_report_runs_and_is_json_serialisable():
    idx = hours("2017-02-01", 60 * 24)
    L = pd.Series(5.0, idx)
    L.loc["2017-03-10": "2017-03-12"] = 300.0
    vd = VenueData(L, L + 10.0, L_alt=L * 0.5, D_usdt=None)
    labels = {"bitfinex": [pos("A", "2017-03-11", end="2017-03-20")], "coinbase": [], "binance_us": []}
    data = {"bitfinex": vd, "coinbase": VenueData(L * 0, L * 0), "binance_us": VenueData(L[:0], L[:0])}
    out = de.report(data, labels)
    json.dumps(out)
    m = out["metrics"]["all"]["bitfinex"]
    assert m["detector"]["recall"] == 1.0 and m["detector"]["positives"][0]["lead_days"] == -1
    assert m["b3"] is None and out["metrics"]["seen"]["coinbase"]["detector"]["evaluated_hours"] == 0
    assert out["metrics"]["all"]["coinbase"]["detector"]["alarm_days"] == 0
    assert len(out["robustness"]["grid"]["bitfinex"]) == 9 and set(out["robustness"]["min_hours"]["bitfinex"]) == {"3", "12"}
    assert "bitfinex" in out["robustness"]["alt_reference"]
    assert out["alarm_episodes"]["bitfinex"]["detector"] == [["2017-03-10", "2017-03-12"]]


def test_build_venues_tolerates_missing_files(tmp_path):
    (tmp_path / "bitfinex").mkdir()
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"records": []}))
    data, meta = de.build_venues(tmp_path, manifest)
    assert set(data) == {"bitfinex", "binance_us", "coinbase"} and all(len(d.L) == 0 for d in data.values())
    assert meta["binance_us_months_on_disk"] == [] and "bitfinex:BTCUSD" in meta["missing_months"]
