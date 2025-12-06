"""Audio Input Page with WebRTC and ADK Agent."""

from nicegui import ui
import base64
import tempfile
import os


class AudioPage:
    def __init__(self):
        self.is_recording = False
        
    def build(self):
        ui.label("Audio Input").classes("text-2xl font-bold mb-4")
        
        # Audio Recording
        with ui.card().classes("w-full mb-4"):
            ui.label("🎤 Record Audio").classes("font-semibold mb-2")
            
            with ui.row().classes("gap-4 items-center"):
                self.record_btn = ui.button("Start Recording", on_click=self.toggle_recording, icon="mic")
                self.record_btn.props("color=red")
                self.recording_status = ui.label("").classes("text-gray-500")
            
            ui.add_body_html('''
                <script>
                let mediaRecorder = null;
                let audioChunks = [];
                
                window.startRecording = async function() {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);
                        audioChunks = [];
                        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
                        mediaRecorder.onstop = async () => {
                            const blob = new Blob(audioChunks, { type: 'audio/webm' });
                            const reader = new FileReader();
                            reader.onloadend = () => emitEvent('audio_recorded', { audio: reader.result.split(',')[1] });
                            reader.readAsDataURL(blob);
                            stream.getTracks().forEach(t => t.stop());
                        };
                        mediaRecorder.start();
                    } catch (err) { console.error(err); }
                };
                window.stopRecording = () => { if (mediaRecorder) mediaRecorder.stop(); };
                </script>
            ''')
            ui.on('audio_recorded', self.handle_audio)
        
        # Text Input
        with ui.card().classes("w-full mb-4"):
            ui.label("Or enter text:").classes("font-semibold")
            self.text_input = ui.textarea(placeholder="My name is Ramesh...").classes("w-full").props("rows=4")
            
            with ui.row().classes("gap-2 mt-2"):
                ui.button("Process", on_click=self.process_text, icon="smart_toy").props("color=primary")
                ui.button("Clear", on_click=self.clear_all, icon="clear").props("flat")
        
        self.status = ui.label("").classes("w-full")
        self.results = ui.column().classes("w-full")
    
    async def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.text = "Stop"
            self.record_btn.props("color=negative")
            self.recording_status.text = "🔴 Recording..."
            await ui.run_javascript('window.startRecording()')
        else:
            self.is_recording = False
            self.record_btn.text = "Start Recording"
            self.record_btn.props("color=red")
            self.recording_status.text = "Processing..."
            await ui.run_javascript('window.stopRecording()')
    
    def handle_audio(self, e):
        audio = e.args.get('audio', '')
        if audio:
            self._transcribe(audio)
    
    def _transcribe(self, audio_base64: str):
        try:
            import whisper
            audio_bytes = base64.b64decode(audio_base64)
            
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                f.write(audio_bytes)
                path = f.name
            
            model = whisper.load_model("base")
            result = model.transcribe(path)
            self.text_input.value = result.get("text", "")
            self.recording_status.text = "✅ Transcribed"
            os.unlink(path)
        except ImportError:
            self.recording_status.text = "❌ Whisper not installed"
        except Exception as e:
            self.recording_status.text = f"❌ {e}"
    
    def process_text(self):
        text = self.text_input.value
        if not text:
            ui.notify("Enter text first", type="warning")
            return
        
        self.status.text = "🤖 Processing..."
        self.results.clear()
        
        # Run synchronously (already uses thread pool internally)
        from src.agents.adk.family_agent import process_family_text
        result = process_family_text(text)
        
        if result.success:
            self.status.text = "✅ Done"
            with self.results:
                with ui.card().classes("w-full"):
                    ui.label(result.response[:500] if result.response else "Processed")
                    
                    from src.graph import FamilyGraph
                    g = FamilyGraph()
                    ui.label(f"Graph: {len(g.get_all_persons())} persons, {len(g.get_all_relationships())} rels")
        else:
            self.status.text = f"❌ {result.error}"
    
    def clear_all(self):
        self.text_input.value = ""
        self.status.text = ""
        self.results.clear()


def create_audio_page():
    page = AudioPage()
    page.build()
    return page
