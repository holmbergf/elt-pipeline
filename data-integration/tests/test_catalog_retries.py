"""A catalog 429 must be retried, not kill the publish: PyIceberg raises
TooManyRequestsError (no .response), which once classified as permanent
and aborted a scheduled ingest run at the NCAAF semantic publish."""

import time

from elt_ingest.iceberg import _is_transient, with_retries


class TooManyRequestsError(Exception):
    pass


def test_too_many_requests_is_transient():
    assert _is_transient(TooManyRequestsError("Rate limit exceeded: too many write requests"))
    assert not _is_transient(ValueError("bad schema"))


def test_with_retries_recovers_from_rate_limit(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TooManyRequestsError("429 Client Error: Too Many Requests")
        return "ok"

    assert with_retries(flaky, attempts=4, base_delay=0) == "ok"
    assert calls["n"] == 3
