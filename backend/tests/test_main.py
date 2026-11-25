from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_liveness_probe():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "pod" in data
    assert "version" in data


@patch("app.main.get_db_connection")
@patch("app.main.get_redis_client")
def test_readiness_probe_healthy(mock_redis, mock_db):
    mock_redis.return_value.ping.return_value = True
    mock_db.return_value = MagicMock()

    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["redis"] == "up"
    assert data["postgres"] == "up"


@patch("app.main.get_db_connection")
@patch("app.main.get_redis_client")
def test_readiness_probe_unhealthy(mock_redis, mock_db):
    mock_redis.side_effect = ConnectionError("Redis down")
    mock_db.return_value = MagicMock()

    response = client.get("/readyz")
    assert response.status_code == 503


@patch("app.main.get_db_connection")
@patch("app.main.get_redis_client")
def test_visits_endpoint(mock_redis, mock_db):
    mock_redis.return_value.incr.return_value = 42

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            "id": 1,
            "visitor_name": "DevOps Engineer",
            "message": "Testing EKS Rolling Update!",
            "served_by_pod": "backend-pod-1",
            "created_at": "2026-11-25 12:00:00",
        }
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_db.return_value = mock_conn

    response = client.get("/api/visits")
    assert response.status_code == 200
    data = response.json()
    assert data["total_visits"] == 42
    assert "version" in data
    assert len(data["recent_notes"]) == 1


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "visit_counter_http_requests_total" in response.text


def test_cpu_load_endpoint():
    response = client.get("/api/load?iterations=2000")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
