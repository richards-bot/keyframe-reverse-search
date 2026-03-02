from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.security import require_api_key
from app.settings import settings


def test_api_key_optional():
    app = FastAPI()

    @app.get("/")
    def route(request: Request):
        require_api_key(request)
        return {"ok": True}

    c = TestClient(app)
    settings.api_key = None
    r = c.get("/")
    assert r.status_code == 200


def test_api_key_required():
    app = FastAPI()

    @app.get("/")
    def route(request: Request):
        require_api_key(request)
        return {"ok": True}

    c = TestClient(app)
    settings.api_key = "secret"
    try:
        assert c.get("/").status_code == 401
        assert c.get("/", headers={"x-api-key": "bad"}).status_code == 401
        assert c.get("/", headers={"x-api-key": "secret"}).status_code == 200
    finally:
        settings.api_key = None
