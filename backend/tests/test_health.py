from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)


def test_health_up_returns_200_ok():
    with patch('psycopg.connect') as mock_pg, patch('redis.from_url') as mock_redis:
        mock_conn = MagicMock()
        mock_pg.return_value = mock_conn
        mock_r = MagicMock()
        mock_redis.return_value = mock_r
        mock_r.ping.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["redis"] == "ok"


def test_health_down_returns_503_per_component():
    with patch('psycopg.connect') as mock_pg, patch('redis.from_url') as mock_redis:
        mock_pg.side_effect = Exception("DB down")
        mock_r = MagicMock()
        mock_redis.return_value = mock_r
        mock_r.ping.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["database"] == "down"
        assert data["redis"] == "ok"
