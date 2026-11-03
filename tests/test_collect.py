import io
import json
from datetime import date

import pytest
from helpers import FIXTURES, teodor

from purrfile.collect import QUERY, CollectError, fetch_snapshot, parse_response

TODAY = date(2026, 11, 3)
RESPONSE = json.loads((FIXTURES / "graphql-response.json").read_text())


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_urlopen(payload, seen):
    def urlopen(request, timeout=None):
        seen.append(request)
        return FakeResponse(json.dumps(payload).encode())

    return urlopen


def test_parse_response_matches_the_snapshot():
    snap = parse_response(RESPONSE, TODAY)
    assert [r.name for r in snap.pinned] == [
        "Vulnerable-Drone-PX4-Lab", "DOS-Detection-in-SDN-Docker-Network", "heron-proxy", "Vyzus",
        "CTFd-Docker-Plugin", "quake3-docker-compose",
    ]
    assert max(snap.days) < TODAY
    assert snap.days == teodor().days
    assert snap.repos[0].languages == teodor().repos[0].languages
    assert (snap.login, snap.name, snap.location) == ("teodoramz", "Teodor Amzuloiu", "Bucharest")


def test_fetch_snapshot_sends_an_authorized_query():
    seen = []
    snap = fetch_snapshot("teodoramz", "tok123", TODAY, urlopen=fake_urlopen(RESPONSE, seen))
    assert snap.login == "teodoramz"
    request = seen[0]
    assert request.full_url == "https://api.github.com/graphql"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "bearer tok123"
    body = json.loads(request.data)
    assert body["query"] == QUERY
    assert body["variables"] == {"login": "teodoramz"}
    for needle in ("pinnedItems(first: 6, types: REPOSITORY)", "contributionCalendar", "isFork: false"):
        assert needle in QUERY


def test_graphql_errors_raise():
    with pytest.raises(CollectError, match="Could not resolve"):
        fetch_snapshot("x", "t", TODAY, urlopen=fake_urlopen({"errors": [{"message": "Could not resolve to a User"}]}, []))


def test_missing_user_raises():
    with pytest.raises(CollectError):
        fetch_snapshot("x", "t", TODAY, urlopen=fake_urlopen({"data": {"user": None}}, []))


def test_missing_token_raises():
    with pytest.raises(CollectError, match="token"):
        fetch_snapshot("x", "", TODAY, urlopen=fake_urlopen(RESPONSE, []))


def test_network_errors_become_collect_errors():
    def broken(request, timeout=None):
        raise OSError("connection refused")

    with pytest.raises(CollectError, match="connection refused"):
        fetch_snapshot("x", "t", TODAY, urlopen=broken)
