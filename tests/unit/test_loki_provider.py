from providers.log_store.loki import LokiLogStore, _extract_log_lines, _extract_signature_series
from core.models import LogQueryRequest, TimeRange


def test_loki_build_signature_counts_json():
    provider = LokiLogStore("loki_main", {"base_url_env": "LOG_STORE_URL", "auth": {"kind": "none"}})
    req = LogQueryRequest(
        subject="payments",
        environment="prod",
        time_range=TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z"),
        intent="signature_counts",
        stream_selectors={"app": "payments"},
        parse={"format": "json", "fields": {"env": "attributes.env", "err_msg": "attributes.error.message"}},
        filters={},
        limit=10,
    )

    query = provider._build_signature_counts(req)
    assert "json" in query
    assert "err_msg" in query


def test_loki_build_samples_non_json():
    provider = LokiLogStore("loki_main", {"base_url_env": "LOG_STORE_URL", "auth": {"kind": "none"}})
    req = LogQueryRequest(
        subject="payments",
        environment="prod",
        time_range=TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z"),
        intent="samples",
        stream_selectors={"app": "payments"},
        parse={"format": "text"},
        filters={},
        limit=10,
    )

    query = provider._build_samples(req)
    assert query == '{app="payments"}'


def test_extract_log_lines_and_signatures():
    payload = {
        "data": {
            "result": [
                {"values": [["1", "line1"], ["2", "line2"]]},
            ]
        }
    }
    lines = _extract_log_lines(payload, limit=10)
    assert lines == ["line1", "line2"]

    sig_payload = {
        "data": {
            "result": [
                {"metric": {"err_type": "X", "err_msg": "Y"}, "values": [["1", "2"], ["2", "3"]]},
                {"metric": {"err_type": "A", "err_msg": "B"}, "values": [["1", "1"]]},
            ]
        }
    }
    sigs = _extract_signature_series(sig_payload)
    assert sigs[0]["count"] >= sigs[1]["count"]
