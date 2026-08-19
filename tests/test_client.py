"""Tests for the Cargo API client (urllib-based, no external network)."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from tekken_counter.client import fetch_character


def _cargo_response(rows: list[dict[str, str]]) -> bytes:
    return json.dumps({"cargoquery": [{"title": row} for row in rows]}).encode("utf-8")


def test_fetch_character_single_page() -> None:
    rows = [{"id": "Steve-1", "name": "Jab", "input": "1"}]
    mock_resp = MagicMock()
    mock_resp.read.return_value = _cargo_response(rows)
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_character("Steve")

    assert len(result) == 1
    assert result[0]["id"] == "Steve-1"


def test_fetch_character_paginates() -> None:
    page1 = [{"id": "Steve-1", "name": "Jab"}]
    page2 = [{"id": "Steve-2", "name": "Jab 2"}]
    empty = []

    def side_effect(req, **_):
        url = req.full_url
        mock_resp = MagicMock()
        if "offset=0" in url or "offset=" not in url:
            body = page1
        elif "offset=1" in url:
            body = page2
        else:
            body = empty
        mock_resp.read.return_value = _cargo_response(body)
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=side_effect):
        result = fetch_character("Steve", limit=1)

    assert len(result) == 2


def test_fetch_character_retries_503() -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = _cargo_response([])
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None)
        return mock_resp

    with patch("time.sleep"):
        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = fetch_character("Steve")

    assert call_count == 2
    assert result == []


def test_fetch_character_http_error_not_retried() -> None:
    with patch("time.sleep"):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None),
        ):
            with pytest.raises(urllib.error.HTTPError):
                fetch_character("Steve")


def test_fetch_character_url_error_retries() -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = _cargo_response([])
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise urllib.error.URLError("network down")
        return mock_resp

    with patch("time.sleep"):
        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = fetch_character("Steve")

    assert call_count == 2
    assert result == []
