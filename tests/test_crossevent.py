import math

import pytest

from www_events.crossevent import holm, random_effects, sign_test, summarize_by_mechanism


def test_random_effects_homogeneous_estimates_reduce_to_fixed_effect():
    re = random_effects([1.0, 1.0, 1.0], [0.5, 0.5, 0.5])
    assert re.pooled == pytest.approx(1.0) and re.tau2 == 0 and re.i2 == 0
    assert re.se == pytest.approx(0.5 / math.sqrt(3))


def test_random_effects_matches_hand_computed_dersimonian_laird():
    # y = (0, 2), se = (1, 1): fixed = 1, Q = 2, C = 1, tau2 = 1, weights 1/2 each, se = 1
    re = random_effects([0.0, 2.0], [1.0, 1.0])
    assert re.q == pytest.approx(2.0) and re.tau2 == pytest.approx(1.0)
    assert re.pooled == pytest.approx(1.0) and re.se == pytest.approx(1.0) and re.i2 == pytest.approx(0.5)
    with pytest.raises(ValueError):
        random_effects([1.0], [1.0])


def test_holm_adjustment_is_monotone_and_matches_textbook_example():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})
    with pytest.raises(ValueError):
        holm({"x": 1.5})


def test_sign_test_exact_values():
    assert sign_test(3, 3) == pytest.approx(0.25)  # three independent events cannot reach 5%
    assert sign_test(5, 5) == pytest.approx(0.0625)
    assert sign_test(2, 4) == 1.0


def test_summary_pools_only_primaries_within_mechanism_and_flags_singletons():
    rows = [
        {"cluster_id": "A", "mechanism": "BANK_RESERVE_RUN", "role": "PRIMARY", "estimate": 1.0, "se": 0.5},
        {"cluster_id": "A", "mechanism": "BANK_RESERVE_RUN", "role": "LINKED_LEG", "estimate": 9.0, "se": 0.1},
        {"cluster_id": "B", "mechanism": "BANK_RESERVE_RUN", "role": "PRIMARY", "estimate": 2.0, "se": 0.5},
        {"cluster_id": "C", "mechanism": "VENUE_INFRASTRUCTURE", "role": "PRIMARY", "estimate": 5.0, "se": 1.0},
    ]
    out = summarize_by_mechanism(rows)
    assert out["BANK_RESERVE_RUN"]["k"] == 2 and out["BANK_RESERVE_RUN"]["random_effects"]["pooled"] == pytest.approx(1.5)
    assert out["VENUE_INFRASTRUCTURE"]["random_effects"] is None
    with pytest.raises(ValueError):
        summarize_by_mechanism(rows + [{"cluster_id": "B", "mechanism": "X", "role": "PRIMARY", "estimate": 0, "se": 1}])
