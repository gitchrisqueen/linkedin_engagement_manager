"""Unit tests for the /api bearer-token gate in cqc_lem.api.main."""

from unittest.mock import patch

import pytest

from cqc_lem.api import main
from cqc_lem.api.main import _api_token_required, _bearer_token

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# _bearer_token — Authorization header parsing
# ---------------------------------------------------------------------------

class TestBearerTokenParsing:
    @pytest.mark.parametrize("header,expected", [
        (None, None),
        ("", None),
        ("Bearer abc123", "abc123"),
        ("bearer abc123", "abc123"),  # scheme is case-insensitive
        ("Bearer   ", None),           # empty token
        ("Basic abc123", None),        # wrong scheme
        ("abc123", None),              # no scheme
    ])
    def test_parses_header(self, header, expected):
        assert _bearer_token(header) == expected


# ---------------------------------------------------------------------------
# _api_token_required — which paths are gated
# ---------------------------------------------------------------------------

class TestApiTokenRequired:
    def test_disabled_when_no_tokens_configured(self):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", set()):
            assert _api_token_required("/api/posts") is False

    @pytest.mark.parametrize("path", [
        "/api/posts",
        "/api/assets",
        "/api/avatar/training",
    ])
    def test_business_routes_gated(self, path):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", {"tok"}):
            assert _api_token_required(path) is True

    @pytest.mark.parametrize("path", [
        "/api/auth/email/init",   # login flow
        "/api/auth/email/verify",
        "/api/auth/session",
        "/api/billing/webhook",   # Stripe (signature-verified)
        "/health",                # non-/api
        "/auth/linkedin/callback",
        "/assets/index.js",       # SPA static
    ])
    def test_public_routes_not_gated(self, path):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", {"tok"}):
            assert _api_token_required(path) is False


# ---------------------------------------------------------------------------
# Middleware behavior via TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with patch("cqc_lem.utilities.observability.track_api_call"):
        from fastapi.testclient import TestClient

        from cqc_lem.api.main import app
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc


class TestGateMiddleware:
    TOKEN = "secret-token-xyz"

    def test_guarded_route_without_token_is_401(self, client):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", {self.TOKEN}):
            resp = client.get("/api/assets", params={"file_name": "x.png"})
        assert resp.status_code == 401

    def test_guarded_route_wrong_token_is_401(self, client):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", {self.TOKEN}):
            resp = client.get(
                "/api/assets",
                params={"file_name": "x.png"},
                headers={"Authorization": "Bearer wrong"},
            )
        assert resp.status_code == 401

    def test_guarded_route_valid_token_passes_gate(self, client):
        # Valid token clears the gate; the handler then 404s on the missing file.
        with patch.object(main, "_API_ACCESS_TOKEN_SET", {self.TOKEN}):
            resp = client.get(
                "/api/assets",
                params={"file_name": "x.png"},
                headers={"Authorization": f"Bearer {self.TOKEN}"},
            )
        assert resp.status_code != 401

    def test_gate_disabled_allows_unauthenticated(self, client):
        with patch.object(main, "_API_ACCESS_TOKEN_SET", set()):
            resp = client.get("/api/assets", params={"file_name": "x.png"})
        assert resp.status_code != 401
