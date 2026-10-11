import numpy as np
import pandas as pd

from www_events.screen import cluster, episodes, match_registry, r1_membership


def test_r1_membership_requires_30_traded_breaches_within_24h():
    n = 3 * 1440
    dev = np.zeros(n)
    traded = np.ones(n, bool)
    dev[100:130] = -150  # exactly 30 breaching minutes
    dev[2000] = -500     # isolated spike: never part of a satisfying window
    m = r1_membership(dev, traded)
    assert m[100:130].all() and not m[2000] and m.sum() == 30
    traded[110] = False  # one untraded minute drops the count to 29
    assert not r1_membership(dev, traded).any()


def test_episodes_merge_within_14_days_and_split_beyond():
    t = pd.date_range("2022-01-01", periods=40 * 1440, freq="1min", tz="UTC")
    dev = np.zeros(len(t))
    member = np.zeros(len(t), bool)
    for day in (1, 10, 30):  # day 10 is < 14 days after day 1; day 30 is not
        member[day * 1440:(day * 1440) + 40] = True
        dev[day * 1440:(day * 1440) + 40] = -120 - day
    eps = episodes(t, dev, member, "USDTUSD")
    assert len(eps) == 2 and eps[0]["breach_minutes"] == 80 and eps[1]["extreme_bps"] == -150


def test_cross_coin_clustering_and_registry_matching():
    eps = [
        {"coin": "USDCUSD", "start_utc": "2023-03-11T00:00:00+00:00", "end_utc": "2023-03-13T00:00:00+00:00", "extreme_bps": -900},
        {"coin": "DAIUSD", "start_utc": "2023-03-11T06:00:00+00:00", "end_utc": "2023-03-12T00:00:00+00:00", "extreme_bps": -700},
        {"coin": "USDTUSD", "start_utc": "2021-06-01T00:00:00+00:00", "end_utc": "2021-06-01T03:00:00+00:00", "extreme_bps": 130},
    ]
    clusters = cluster(eps)
    assert len(clusters) == 2 and clusters[1]["primary"] == "USDCUSD" and len(clusters[1]["members"]) == 2
    registry = [{"cluster_id": "CL-2023-03-SVB", "reported_window_utc": {"start": "2023-03-10", "end": "2023-03-13"}}]
    match_registry(clusters, registry)
    assert clusters[1]["classification"] == "MATCHES_REGISTRY" and clusters[0]["classification"] == "NEW_CANDIDATE"
