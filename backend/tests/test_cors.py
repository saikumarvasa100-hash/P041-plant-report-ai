"""CORS smoke test for the Vite dev server origin."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_allows_vite_dev_origin():
    resp = client.options(
        "/api/v1/analytics/sample",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
