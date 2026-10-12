from decimal import Decimal as D

import pytest

from www_c1.depth import book_metrics


def test_book_metrics_hand_computed_bands_and_imbalance():
    bids = {D("0.9999"): D("100"), D("0.9990"): D("50"), D("0.9900"): D("1000")}
    asks = {D("1.0001"): D("200"), D("1.0060"): D("10")}
    m = book_metrics(bids, asks)
    assert m["spread_bps"] == pytest.approx(2.0)
    # mid 1.0; 10 bps band = [0.999, 1.001]: bids 0.9999*100 + 0.9990*50, asks 1.0001*200
    assert m["bid_depth_quote_10bps"] == pytest.approx(99.99 + 49.95)
    assert m["ask_depth_quote_10bps"] == pytest.approx(200.02)
    assert m["ask_depth_quote_100bps"] == pytest.approx(200.02 + 10.06)
    assert m["bid_depth_quote_100bps"] == pytest.approx(99.99 + 49.95 + 990.0)
    assert m["imbalance_10bps"] == pytest.approx((149.94 - 200.02) / (149.94 + 200.02))
    assert not m["crossed"] and book_metrics({}, asks) is None
