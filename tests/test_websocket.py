"""Tests del sistema WebSocket."""
import pytest
from starlette.websockets import WebSocketDisconnect


class TestWebSocketConnection:
    def test_connect_to_valid_channel(self, client):
        with client.websocket_connect("/ws/users") as ws:
            # Consumir mensaje de bienvenida
            welcome = ws.receive_json()
            assert welcome["type"] == "connection"
            assert welcome["channel"] == "users"

            # Ping-pong
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_connect_to_invalid_channel(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/invalid") as ws:
                ws.receive_json()

    def test_get_stats(self, client):
        with client.websocket_connect("/ws/users") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "get_stats"})
            data = ws.receive_json()
            assert data["type"] == "stats"
            assert "data" in data

    def test_echo_message(self, client):
        with client.websocket_connect("/ws/users") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "custom", "payload": "hello"})
            data = ws.receive_json()
            assert data["type"] == "echo"
            assert data["original"]["payload"] == "hello"


class TestWebSocketStats:
    def test_stats_endpoint(self, client):
        response = client.get("/ws/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "channels" in stats or "total_connections" in stats
