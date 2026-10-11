import gzip

from www_c1.validation import sha256_file, validate_sample


def test_hash_pin_blocks_replay_on_mismatch(tmp_path):
    path = tmp_path / "empty.csv.gz"
    with gzip.open(path, "wt") as stream:
        stream.write("exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount\n")
    result = validate_sample(path, expected_sha256="wrong")
    assert result["status"] == "HASH_MISMATCH"
    assert result["sha256_matches_expected"] is False
    assert sha256_file(path) == result["sha256"]
