from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    # "A" unless COPY_NAME says otherwise (D23), "dev" unless APP_VERSION does (D31).
    assert response.json() == {"status": "ok", "copy": "A", "version": "dev"}
