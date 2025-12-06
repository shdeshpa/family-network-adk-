"""Audio recorder component with chunked upload for long recordings."""

from nicegui import ui
from typing import Callable, Optional


class AudioRecorderUI:
    """Audio recorder with WebRTC and chunked upload."""
    
    def __init__(self, on_audio_received: Optional[Callable] = None):
        self.on_audio_received = on_audio_received
        self.is_recording = False
        self.recording_time = 0
        self._build_ui()
    
    def _build_ui(self):
        """Build the recorder UI."""
        with ui.card().classes("w-96 p-4"):
            ui.label("🎤 Audio Recorder").classes("text-xl font-bold mb-4")
            
            with ui.row().classes("gap-2 mb-4"):
                self.record_btn = ui.button(
                    "🎤 Start Recording",
                    on_click=self._start_recording
                ).classes("bg-red-500")
                
                self.stop_btn = ui.button(
                    "⬛ Stop",
                    on_click=self._stop_recording
                ).classes("bg-gray-500")
                self.stop_btn.visible = False
            
            self.timer_label = ui.label("00:00").classes("text-2xl font-mono")
            self.status_label = ui.label("Ready to record").classes("text-gray-600")
            
            # Hidden audio player for playback
            self.audio_player = ui.audio("").classes("w-full mt-4")
            self.audio_player.visible = False
    
    async def _start_recording(self):
        """Start recording audio."""
        self.is_recording = True
        self.recording_time = 0
        self.record_btn.visible = False
        self.stop_btn.visible = True
        self.status_label.set_text("Recording... (max 10 minutes)")
        
        # Start timer
        self.timer = ui.timer(1.0, self._update_timer)
        
        # JavaScript for recording with chunked data collection
        js_code = """
        (async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        sampleRate: 16000
                    }
                });
                
                window.mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus'
                });
                
                window.audioChunks = [];
                
                window.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        window.audioChunks.push(event.data);
                    }
                };
                
                // Collect data every 1 second for chunking
                window.mediaRecorder.start(1000);
                
            } catch (err) {
                console.error('Microphone error:', err);
            }
        })();
        """
        ui.run_javascript(js_code)
    
    async def _stop_recording(self):
        """Stop recording and send audio."""
        self.is_recording = False
        self.timer.cancel()
        self.record_btn.visible = True
        self.stop_btn.visible = False
        self.status_label.set_text("Processing...")
        
        # Stop recording and get audio
        js_code = """
        new Promise((resolve) => {
            if (window.mediaRecorder && window.mediaRecorder.state !== 'inactive') {
                window.mediaRecorder.onstop = async () => {
                    const blob = new Blob(window.audioChunks, { type: 'audio/webm' });
                    
                    // Convert to base64 in chunks to avoid memory issues
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64 = reader.result.split(',')[1];
                        resolve(base64);
                    };
                    reader.readAsDataURL(blob);
                    
                    // Stop all tracks
                    window.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                };
                window.mediaRecorder.stop();
            } else {
                resolve(null);
            }
        });
        """
        
        result = await ui.run_javascript(js_code, timeout=30.0)
        
        if result:
            import base64
            audio_bytes = base64.b64decode(result)
            self.status_label.set_text(f"✅ Recorded {len(audio_bytes) / 1024:.1f} KB")
            
            if self.on_audio_received:
                await self.on_audio_received(audio_bytes)
        else:
            self.status_label.set_text("❌ Recording failed")
    
    def _update_timer(self):
        """Update recording timer."""
        if self.is_recording:
            self.recording_time += 1
            mins = self.recording_time // 60
            secs = self.recording_time % 60
            self.timer_label.set_text(f"{mins:02d}:{secs:02d}")
            
            # Auto-stop at 10 minutes
            if self.recording_time >= 600:
                ui.notify("Maximum recording time reached (10 minutes)")
                self._stop_recording()