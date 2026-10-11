import csv
import gzip
from pathlib import Path

from www_c1.reader import iter_l2_rows, iter_local_timestamp_groups
from www_c1.replay import BookReplayer, replay_file


FIXTURE = Path(__file__).parent / "fixtures" / "c1" / "base_book.csv"
FIELDS = ["exchange", "symbol", "timestamp", "local_timestamp", "is_snapshot", "side", "price", "amount"]


def fixture_rows():
    with FIXTURE.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_feed(tmp_path, rows, name="feed.csv.gz"):
    path = tmp_path / name
    with gzip.open(path, "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_snapshot_updates_removals_and_decimal_level_identity(tmp_path):
    rows = fixture_rows()
    rows.extend([
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "99.99999999", "amount": "1"},
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "100.00", "amount": "0"},
    ])
    path = write_feed(tmp_path, rows)
    result = replay_file(path)
    assert result["complete_snapshot_segments"] == 1
    assert result["applied_updates"] == 3
    assert result["zero_amount_removals"] == 2
    assert result["final_best_bid"]["price"] == "99.99999999"
    assert result["final_best_ask"]["amount"] == "5.0"
    assert result["timestamp_regressions"] == 0


def test_snapshot_reset_replaces_old_state(tmp_path):
    rows = fixture_rows()
    rows.extend([
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "is_snapshot": "true", "side": "bid", "price": "90", "amount": "1"},
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "is_snapshot": "true", "side": "ask", "price": "91", "amount": "1"},
        {**rows[-1], "timestamp": "1677628804000000", "local_timestamp": "1677628804000001", "is_snapshot": "false", "side": "bid", "price": "90", "amount": "0.5"},
    ])
    result = replay_file(write_feed(tmp_path, rows))
    assert result["snapshot_segments"] == 2
    assert result["snapshot_resets"] == 1
    assert result["final_best_bid"]["price"] == "90"
    assert result["final_best_ask"]["price"] == "91"
    assert result["final_bid_levels"] == 1


def test_pre_snapshot_updates_are_not_emitted_as_valid_book(tmp_path):
    rows = fixture_rows()[2:]
    rows = [{**row, "is_snapshot": "false"} for row in rows]
    result = replay_file(write_feed(tmp_path, rows))
    assert result["updates_ignored_without_valid_snapshot"] == len(rows)
    assert result["final_book_initialized"] is False
    assert result["final_best_bid"] is None


def test_invalid_negative_size_taints_book_until_new_snapshot(tmp_path):
    rows = fixture_rows()
    rows.append({**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "100", "amount": "-2"})
    result = replay_file(write_feed(tmp_path, rows))
    assert result["anomaly_counts"]["invalid_price_or_amount"] == 1
    assert result["final_book_initialized"] is False


def test_crossed_book_is_detected_after_message_group(tmp_path):
    rows = fixture_rows()
    rows.append({**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "101", "amount": "1"})
    result = replay_file(write_feed(tmp_path, rows))
    assert result["crossed_book_observations"] == 1
    assert any(item["code"] == "crossed_book" for item in result["anomaly_examples"])


def test_identical_local_timestamp_rows_keep_file_order(tmp_path):
    rows = fixture_rows()
    rows.extend([
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "100", "amount": "6"},
        {**rows[-1], "timestamp": "1677628803000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "100", "amount": "7"},
    ])
    path = write_feed(tmp_path, rows)
    grouped = list(iter_local_timestamp_groups(path))
    assert grouped[-1][0].row_number < grouped[-1][1].row_number
    assert replay_file(path)["final_best_bid"]["amount"] == "7"


def test_replay_is_deterministic_and_detects_local_arrival_gap(tmp_path):
    rows = fixture_rows()
    rows.append({**rows[-1], "timestamp": "1677628840000000", "local_timestamp": "1677628840000001", "side": "bid", "price": "100", "amount": "8"})
    path = write_feed(tmp_path, rows)
    first = replay_file(path, max_idle_gap_seconds=10)
    second = replay_file(path, max_idle_gap_seconds=10)
    assert first == second
    assert first["local_arrival_gaps_over_threshold"] >= 1


def test_reader_rejects_missing_schema(tmp_path):
    path = write_feed(tmp_path, fixture_rows())
    # Rewrite a malformed compressed input to ensure schema errors are explicit.
    malformed = tmp_path / "malformed.csv.gz"
    with gzip.open(malformed, "wt") as stream:
        stream.write("timestamp,side,price,amount\n1,bid,2,3\n")
    try:
        list(iter_l2_rows(malformed))
    except ValueError as exc:
        assert "missing required" in str(exc)
    else:
        raise AssertionError("missing schema was accepted")


def test_exchange_timestamp_regression_is_reported_but_source_order_replays(tmp_path):
    rows = fixture_rows()
    rows.append({**rows[-1], "timestamp": "1677628799000000", "local_timestamp": "1677628803000001", "side": "bid", "price": "100", "amount": "4"})
    result = replay_file(write_feed(tmp_path, rows))
    assert result["timestamp_regressions"] == 1
    assert result["final_book_initialized"] is True
    assert result["native_sequence_continuity"] == "UNVERIFIABLE_NOT_PRESENT_IN_NORMALIZED_CSV"


def test_incomplete_snapshot_never_initializes_book(tmp_path):
    rows = fixture_rows()[:1]
    result = replay_file(write_feed(tmp_path, rows))
    assert result["incomplete_snapshot_segments"] == 1
    assert result["final_book_initialized"] is False
    assert result["final_best_bid"] is None
