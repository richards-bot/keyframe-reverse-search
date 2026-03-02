from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoints():
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/readyz").status_code == 200
