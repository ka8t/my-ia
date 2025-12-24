"""
Tests pour le endpoint health check

Tests de base pour vérifier que l'API répond correctement.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """
    Test que le endpoint /health retourne 200 OK
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_metrics_endpoint(client: TestClient):
    """
    Test que le endpoint /metrics retourne les métriques Prometheus
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert b"# HELP" in response.content
