"""Tests for security headers and X-Request-ID middleware (IN-6, IN-8)."""
import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_security_headers_present(client):
    resp = client.get("/health")
    assert "X-Frame-Options" in resp.headers
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in resp.headers
    assert "Content-Security-Policy" in resp.headers


def test_request_id_echoed(client):
    resp = client.get("/health", headers={"X-Request-ID": "test-trace-123"})
    assert resp.headers.get("X-Request-ID") == "test-trace-123"


def test_request_id_generated_if_missing(client):
    resp = client.get("/health")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) == 36  # UUID v4 format
