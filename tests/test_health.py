"""Health probe tests.

The Qdrant check is a FastAPI dependency, so tests replace it with a stub via
`app.dependency_overrides`. That keeps unit tests deterministic and offline:
they pass with or without a running Qdrant, and they exercise both the healthy
and the degraded path.
"""

from fastapi.testclient import TestClient

from citegrep.api.health import qdrant_ready
from citegrep.app import create_app


def make_client(qdrant_ok: bool) -> TestClient:
    app = create_app()

    def stub() -> bool:
        return qdrant_ok

    app.dependency_overrides[qdrant_ready] = stub
    return TestClient(app)


def test_healthz_is_alive_without_touching_dependencies() -> None:
    client = TestClient(create_app())  # no override: /healthz must not need one
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_readyz_ok_when_qdrant_up() -> None:
    resp = make_client(qdrant_ok=True).get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "qdrant": "ok"}


def test_readyz_503_when_qdrant_down() -> None:
    resp = make_client(qdrant_ok=False).get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"
