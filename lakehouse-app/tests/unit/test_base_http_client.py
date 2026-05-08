"""Unit tests for BaseHttpClient — retry, auth, and pagination."""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest
import requests
import requests.exceptions

from lakehouse_common.clients.base_http import (
    ApiKeyAuth,
    BaseHttpClient,
    BearerTokenAuth,
    NoAuth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status: int = 200, json_body=None, headers=None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = json_body or {}
    resp.headers = headers or {}
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


class _SimpleClient(BaseHttpClient):
    BASE_URL = "https://api.example.com"


# ---------------------------------------------------------------------------
# Auth strategies
# ---------------------------------------------------------------------------

class TestAuthStrategies:
    def test_no_auth_does_not_add_headers(self):
        req = requests.PreparedRequest()
        req.headers = {}
        result = NoAuth().apply(req)
        assert "Authorization" not in result.headers

    def test_bearer_token_adds_authorization_header(self):
        req = requests.PreparedRequest()
        req.headers = {}
        result = BearerTokenAuth(lambda: "my-token").apply(req)
        assert result.headers["Authorization"] == "Bearer my-token"

    def test_bearer_token_calls_provider_on_each_apply(self):
        tokens = iter(["tok1", "tok2"])
        auth = BearerTokenAuth(lambda: next(tokens))
        req1, req2 = requests.PreparedRequest(), requests.PreparedRequest()
        req1.headers, req2.headers = {}, {}
        assert auth.apply(req1).headers["Authorization"] == "Bearer tok1"
        assert auth.apply(req2).headers["Authorization"] == "Bearer tok2"

    def test_api_key_auth_uses_configured_header_name(self):
        req = requests.PreparedRequest()
        req.headers = {}
        result = ApiKeyAuth("X-Api-Key", "secret-key").apply(req)
        assert result.headers["X-Api-Key"] == "secret-key"
        assert "Authorization" not in result.headers


# ---------------------------------------------------------------------------
# GET / POST
# ---------------------------------------------------------------------------

class TestGetPost:
    def test_get_returns_response(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.return_value = _mock_response(200, {"id": 1})

        client = _SimpleClient(session=mock_session)
        resp = client.get("/items/1")
        assert resp.json() == {"id": 1}

    def test_post_sends_json_body(self):
        mock_session = MagicMock()
        prepared = requests.PreparedRequest()
        mock_session.prepare_request.return_value = prepared
        mock_session.send.return_value = _mock_response(201, {"created": True})

        client = _SimpleClient(session=mock_session)
        resp = client.post("/items", json={"name": "test"})
        assert resp.status_code == 201

    def test_raises_on_4xx(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.return_value = _mock_response(404)

        client = _SimpleClient(session=mock_session)
        with pytest.raises(requests.HTTPError):
            client.get("/missing")

    def test_retries_on_connection_error_then_succeeds(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            _mock_response(200, {"ok": True}),
        ]

        client = _SimpleClient(session=mock_session)
        # Patch tenacity sleep so tests run instantly
        with patch("tenacity.nap.time.sleep"):
            resp = client.get("/ping")
        assert resp.json() == {"ok": True}
        assert mock_session.send.call_count == 2

    def test_raises_after_max_retries_exceeded(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.side_effect = requests.exceptions.ConnectionError("down")

        client = _SimpleClient(session=mock_session)
        with patch("tenacity.nap.time.sleep"):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get("/always-fails")
        assert mock_session.send.call_count == 5  # stop_after_attempt(5)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    def test_yields_records_from_single_page(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.return_value = _mock_response(
            200, {"results": [{"id": 1}, {"id": 2}], "next": None}
        )

        client = _SimpleClient(session=mock_session)
        records = list(client.paginate("/items", results_key="results"))
        assert records == [{"id": 1}, {"id": 2}]
        assert mock_session.send.call_count == 1

    def test_follows_next_url_across_pages(self):
        page1 = _mock_response(200, {"results": [{"id": 1}], "next": "/items?page=2"})
        page2 = _mock_response(200, {"results": [{"id": 2}], "next": None})
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.side_effect = [page1, page2]

        client = _SimpleClient(session=mock_session)
        records = list(client.paginate("/items", results_key="results"))
        assert [r["id"] for r in records] == [1, 2]
        assert mock_session.send.call_count == 2

    def test_custom_next_page_fn(self):
        page1 = _mock_response(200, [{"id": 1}])
        page2 = _mock_response(200, [{"id": 2}])
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()

        call_count = 0
        def next_fn(resp):
            nonlocal call_count
            call_count += 1
            return "/items?page=2" if call_count == 1 else None

        mock_session.send.side_effect = [page1, page2]
        client = _SimpleClient(session=mock_session)
        records = list(client.paginate("/items", next_page_fn=next_fn))
        assert len(records) == 2

    def test_body_as_plain_list_no_results_key(self):
        mock_session = MagicMock()
        mock_session.prepare_request.return_value = requests.PreparedRequest()
        mock_session.send.return_value = _mock_response(200, [{"id": 1}, {"id": 2}])

        client = _SimpleClient(session=mock_session)
        records = list(client.paginate("/items"))
        assert len(records) == 2
