from www_rescue.fiat_rail import CASES, verdict


def case(median, corr, minutes=100):
    return {"pd_usdt": [{"phase": "post_4w", "minutes": minutes, "median_bps": median}],
            "identification": {"post_4w": {"hours": 50, "corr_hourly": corr}}}


def test_verdict_applies_the_pre_recorded_falsification_rule():
    assert verdict(case(40.0, 0.95)) == "SUPPORTED_SIGN_POSITIVE"
    assert verdict(case(-40.0, 0.95)) == "SUPPORTED_SIGN_NEGATIVE"
    assert verdict(case(9.9, 0.95)) == "FALSIFIED"
    assert verdict(case(40.0, 0.4)) == "FALSIFIED"
    assert verdict(case(40.0, 0.95, minutes=0)) == "INSUFFICIENT_DATA"
    assert verdict({"pd_usdt": [{"phase": "post_4w", "minutes": 5, "median_bps": 1.0}],
                    "identification": {"post_4w": {"hours": 3}}}) == "INSUFFICIENT_DATA"


def test_cases_use_contiguous_documented_phases():
    for spec in CASES.values():
        ph = spec["phases"]
        assert [p[0] for p in ph] == ["pre", "post_4w", "later"]
        assert all(ph[i][2] == ph[i + 1][1] for i in range(len(ph) - 1)) and spec["sources"]
