"""WebSocket server for receiving audio from browser."""

import asyncio
import base64
import json
from typing import Callable, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.audio.processor import AudioProcessor
from src.audio.validator import AudioValidator


class AudioWebSocketServer:
    """Handle WebSocket connections for audio streaming."""
    
    def __init__(
        self,
        on_audio_complete: Optional[Callable] = None,
        sample_rate: int = 16000
    ):
        self.on_audio_complete = on_audio_complete
        self.processor = AudioProcessor(sample_rate=sample_rate)
        self.validator = AudioValidator(sample_rate=sample_rate)
        self.app = FastAPI(title="Family Network Audio Server")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup WebSocket routes."""
        
        @self.app.websocket("/ws/audio")
        async def audio_endpoint(websocket: WebSocket):
            await self._handle_connection(websocket)
        
        @self.app.get("/health")
        async def health():
            return {"status": "ok"}
    
    async def _handle_connection(self, websocket: WebSocket):
        """Handle a single WebSocket connection."""
        await websocket.accept()
        audio_chunks: list[bytes] = []
        
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data["type"] == "audio_chunk":
                    chunk = base64.b64decode(data["data"])
                    audio_chunks.append(chunk)
                    await websocket.send_json({"type": "ack"})
                
                elif data["type"] == "audio_end":
                    result = await self._process_audio(audio_chunks)
                    await websocket.send_json(result)
                    audio_chunks = []
                
                elif data["type"] == "ping":
                    await websocket.send_json({"type": "pong"})
        
        except WebSocketDisconnect:
            pass
    
    async def _process_audio(self, chunks: list[bytes]) -> dict:
        """Process collected audio chunks."""
        if not chunks:
            return {"type": "error", "message": "No audio received"}
        
        combined = b"".join(chunks)
        
        try:
            audio_data = self.processor.bytes_to_numpy(combined)
            validation = self.validator.validate(audio_data)
            
            if not validation["valid"]:
                return {
                    "type": "validation_error",
                    "errors": validation["errors"]
                }
            
            # Remove noise
            cleaned = self.processor.remove_noise(audio_data)
            cleaned = self.processor.normalize(cleaned)
            
            # Callback if provided
            if self.on_audio_complete:
                await self.on_audio_complete(cleaned)
            
            return {
                "type": "success",
                "duration": validation["duration"],
                "message": "Audio processed successfully"
            }
        
        except Exception as e:
            return {"type": "error", "message": str(e)}


def create_app(on_audio_complete: Optional[Callable] = None) -> FastAPI:
    """Create FastAPI app with audio WebSocket."""
    server = AudioWebSocketServer(on_audio_complete=on_audio_complete)
    return server.app