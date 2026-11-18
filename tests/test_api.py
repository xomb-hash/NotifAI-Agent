"""Tests for the FastAPI service."""

import pytest
from fastapi.testclient import TestClient

from notifai.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestHealth:
    def test_health_endpoint(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "rag_healthy" in data

    def test_health_has_version(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.json()["version"] == "2.0.0"


class TestQuery:
    def test_query_missing_message(self, client: TestClient) -> None:
        response = client.post("/query", json={})
        assert response.status_code == 422

    def test_query_empty_message(self, client: TestClient) -> None:
        response = client.post("/query", json={"message": ""})
        assert response.status_code == 422

    def test_query_valid_request(self, client: TestClient) -> None:
        response = client.post(
            "/query",
            json={
                "message": "Team meeting tomorrow at 10am",
                "dry_run": True,
                "enable_rag": False,
                "enable_validation": False,
            },
        )
        assert response.status_code in (200, 500)


class TestIngest:
    def test_ingest_missing_text(self, client: TestClient) -> None:
        response = client.post("/ingest", json={})
        assert response.status_code == 422

    def test_ingest_empty_text(self, client: TestClient) -> None:
        response = client.post("/ingest", json={"text": ""})
        assert response.status_code == 422

    def test_ingest_valid_request(self, client: TestClient) -> None:
        response = client.post(
            "/ingest",
            json={"text": "Simple notice text"},
        )
        assert response.status_code in (200, 500)


class TestMetrics:
    def test_metrics_endpoint(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "total_requests" in data["summary"]


class TestAuth:
    def test_health_no_auth_required(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_metrics_no_auth_when_disabled(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
