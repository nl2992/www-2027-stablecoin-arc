"""Hand-computed synthetic books; these validate arithmetic only and are not market results."""

from decimal import Decimal

import pytest

from www_capacity.orderbook import (
    capacity_within_cost, levels_from_book, normalize_levels, triangle_restoration, walk, walk_quote,
)
from www_c1.replay import Book


ASKS = [(100.0, 1.0), (101.0, 1.0)]


def test_walk_partial_fill_reports_depth_exhaustion():
    full = walk(ASKS, 1.5)
    assert full.vwap == pytest.approx((100 + 0.5 * 101) / 1.5) and full.complete and full.levels_used == 2
    partial = walk(ASKS, 3.0)
    assert partial.filled_base == 2.0 and not partial.complete and partial.worst_price == 101.0


def test_walk_quote_spends_quote_currency():
    out = walk_quote([(100.0, 1.0), (200.0, 1.0)], 150.0)
    assert out.filled_base == pytest.approx(1.25) and out.quote_notional == pytest.approx(150.0)


def test_normalize_sorts_aggregates_and_rejects_bad_levels():
    assert normalize_levels([(101, 1), (100, 2), (100, 1), (99, 0)], "ask") == [(100, 3), (101, 1)]
    assert normalize_levels([(99, 1), (100, 1)], "bid")[0] == (100, 1)
    with pytest.raises(ValueError):
        normalize_levels([(0, 1)], "ask")
    with pytest.raises(ValueError):
        normalize_levels([(1, 1)], "mid")


def test_capacity_within_cost_solves_partial_level_exactly():
    asks = [(100.0, 1.0), (102.0, 1.0)]
    assert capacity_within_cost(asks, "ask", 100.0, 100) == pytest.approx(2.0)  # VWAP exactly 101
    q = capacity_within_cost(asks, "ask", 100.0, 50)
    assert q == pytest.approx(4 / 3)
    assert walk(asks, q).vwap == pytest.approx(100.5)
    assert capacity_within_cost([(100.0, 1.0), (98.0, 1.0)], "bid", 100.0, 100) == pytest.approx(2.0)
    assert capacity_within_cost([(103.0, 1.0)], "ask", 100.0, 100) == 0.0


def test_fees_shrink_cost_bounded_capacity():
    asks = [(100.0, 1.0), (102.0, 1.0)]
    assert capacity_within_cost(asks, "ask", 100.0, 100, fee_bps=10) < capacity_within_cost(asks, "ask", 100.0, 100)


USDC_BIDS = [(102.0, 1.0), (100.5, 1.0)]
PAR = [(1.0, 1_000.0)]


def test_triangle_restoration_stops_where_marginal_loop_return_hits_zero():
    r = triangle_restoration(ASKS, USDC_BIDS, PAR)
    assert r.restoration_btc == pytest.approx(1.0, abs=1e-6)
    assert r.restoration_profit_usd == pytest.approx(2.0, abs=1e-4)
    assert r.limited_by == "marginal_parity" and r.initial_marginal_bps == pytest.approx(200.0)


def test_triangle_restoration_depth_and_inventory_limits():
    depth = triangle_restoration([(100.0, 1.0)], [(102.0, 5.0)], PAR)
    assert depth.limited_by == "depth" and depth.restoration_btc == pytest.approx(1.0)
    inv = triangle_restoration(ASKS, USDC_BIDS, PAR, max_usd=50.0)
    assert inv.limited_by == "inventory" and inv.restoration_btc == pytest.approx(0.5)
    assert inv.restoration_profit_usd == pytest.approx(1.0, abs=1e-6)


def test_stablecoin_redemption_leg_can_be_the_binding_constraint():
    thin_usdc = [(1.0, 51.0), (0.9, 1_000.0)]
    r = triangle_restoration(ASKS, [(102.0, 5.0)], thin_usdc)
    assert r.restoration_btc == pytest.approx(0.5, abs=1e-6)
    assert r.restoration_profit_usd == pytest.approx(1.0, abs=1e-4)


def test_fees_can_eliminate_the_opportunity_entirely():
    r = triangle_restoration(ASKS, USDC_BIDS, PAR, fee_bps=100)
    assert r.restoration_btc == 0.0 and r.initial_marginal_bps < 0


def test_levels_from_c1_book_state():
    book = Book()
    book.apply("ask", Decimal("101"), Decimal("2"))
    book.apply("ask", Decimal("100"), Decimal("1"))
    book.apply("ask", Decimal("102"), Decimal("0"))  # removal leaves no level
    assert levels_from_book(book.asks, "ask") == [(100.0, 1.0), (101.0, 2.0)]
    assert levels_from_book(book.asks, "ask", depth=1) == [(100.0, 1.0)]


def test_exhausted_stablecoin_leg_is_labelled_depth_not_parity():
    r = triangle_restoration(ASKS, [(102.0, 5.0)], [(1.0, 51.0)])
    assert r.restoration_btc == pytest.approx(0.5, abs=1e-6) and r.limited_by == "depth"
