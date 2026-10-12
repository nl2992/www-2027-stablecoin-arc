import json
from io import BytesIO

import pytest

from www_c2 import rpc


class Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def mock_response(monkeypatch, response):
    def fake_urlopen(request, timeout):
        body = json.loads(request.data)
        assert body["method"] in {"eth_chainId", "eth_getBlockByNumber", "eth_getCode"}
        return Response(json.dumps(response).encode())
    monkeypatch.setattr(rpc.urllib.request, "urlopen", fake_urlopen)


def test_read_only_rpc_probe_decodes_expected_historical_metadata(monkeypatch):
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        {"jsonrpc": "2.0", "id": 1, "result": {"number": "0xabc", "hash": "0x" + "1" * 64}},
        {"jsonrpc": "2.0", "id": 1, "result": "0x6001"},
    ])
    monkeypatch.setattr(rpc.urllib.request, "urlopen", lambda request, timeout: Response(json.dumps(next(responses)).encode()))
    result = rpc.probe("https://rpc.example", "0xabc", "0x" + "a" * 40)
    assert result["chain_id"] == "0x1"
    assert result["block_hash"] == "0x" + "1" * 64
    assert result["code_bytes"] == 2
    assert result["status"] == "LIVE_VERIFIED"


def test_probe_can_run_read_only_eth_call_at_requested_block(monkeypatch):
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        {"jsonrpc": "2.0", "id": 1, "result": {"number": "0xabc", "hash": "0x" + "2" * 64}},
        {"jsonrpc": "2.0", "id": 1, "result": "0x6001"},
        {"jsonrpc": "2.0", "id": 1, "result": "0x0000000000000000000000000000000000000000000000000000000000000001"},
    ])
    monkeypatch.setattr(rpc.urllib.request, "urlopen", lambda request, timeout: Response(json.dumps(next(responses)).encode()))
    result = rpc.probe("https://rpc.example", "0xabc", "0x" + "a" * 40, "0x1234")
    assert result["eth_call_result"].endswith("1")


def test_probe_rejects_provider_returning_wrong_block(monkeypatch):
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        {"jsonrpc": "2.0", "id": 1, "result": {"number": "0xabd", "hash": "0x" + "3" * 64}},
    ])
    monkeypatch.setattr(rpc.urllib.request, "urlopen", lambda request, timeout: Response(json.dumps(next(responses)).encode()))
    with pytest.raises(rpc.RpcError, match="different block"):
        rpc.probe("https://rpc.example", "0xabc", "0x" + "a" * 40)


def test_probe_rejects_invalid_historical_block_hash(monkeypatch):
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        {"jsonrpc": "2.0", "id": 1, "result": {"number": "0xabc", "hash": "0x123"}},
    ])
    monkeypatch.setattr(rpc.urllib.request, "urlopen", lambda request, timeout: Response(json.dumps(next(responses)).encode()))
    with pytest.raises(rpc.RpcError, match="invalid block hash"):
        rpc.probe("https://rpc.example", "0xabc", "0x" + "a" * 40)


def test_wrong_chain_is_rejected(monkeypatch):
    mock_response(monkeypatch, {"jsonrpc": "2.0", "id": 1, "result": "0x89"})
    with pytest.raises(rpc.RpcError, match="wrong chain"):
        rpc.probe("https://rpc.example", "0xabc", "0x" + "a" * 40)


def test_provider_error_is_reported_without_endpoint(monkeypatch):
    mock_response(monkeypatch, {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "archive unavailable"}})
    with pytest.raises(rpc.RpcError, match="endpoint redacted"):
        rpc.rpc_call("https://secret.example/key", "eth_chainId", [])


def test_rpc_rejects_http_and_write_methods():
    with pytest.raises(ValueError, match="HTTPS"):
        rpc.rpc_call("http://rpc.example", "eth_chainId", [])
    with pytest.raises(ValueError, match="read-only"):
        rpc.rpc_call("https://rpc.example", "eth_sendRawTransaction", [])


def test_probe_rejects_invalid_block_and_address():
    with pytest.raises(ValueError, match="hex quantity"):
        rpc.probe("https://rpc.example", "latest", "0x" + "a" * 40)
    with pytest.raises(ValueError, match="20-byte"):
        rpc.probe("https://rpc.example", "0x1", "0x123")
