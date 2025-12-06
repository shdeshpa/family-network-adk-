"""Stage 2B Tests: WebSocket Audio Server."""

import pytest
from fastapi.testclient import TestClient


class TestAudioWebSocketServer:
    """Test WebSocket server setup."""
    
    def test_create_app(self):
        """App should be created successfully."""
        from src.audio.websocket_server import create_app
        app = create_app()
        assert app is not None
        assert app.title == "Family Network Audio Server"
    
    def test_health_endpoint(self):
        """Health endpoint should return ok."""
        from src.audio.websocket_server import create_app
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_websocket_ping(self):
        """WebSocket should respond to ping."""
        from src.audio.websocket_server import create_app
        import json
        
        app = create_app()
        client = TestClient(app)
        
        with client.websocket_connect("/ws/audio") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_json()
            assert response["type"] == "pong"
    
    def test_websocket_empty_audio(self):
        """Empty audio should return error."""
        from src.audio.websocket_server import create_app
        import json
        
        app = create_app()
        client = TestClient(app)
        
        with client.websocket_connect("/ws/audio") as ws:
            ws.send_text(json.dumps({"type": "audio_end"}))
            response = ws.receive_json()
            assert response["type"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])