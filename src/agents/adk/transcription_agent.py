"""Transcription Agent - handles audio to text conversion."""

from pathlib import Path
from typing import Optional

from src.transcription.whisper_service import WhisperService


class TranscriptionAgent:
    """Agent for audio transcription using Whisper."""
    
    def __init__(self):
        self.whisper = WhisperService()
    
    def process(self, audio_path: str, need_english: bool = True) -> dict:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file (WebM or WAV)
            need_english: Translate to English if needed
        
        Returns:
            dict with text, language, success
        """
        path = Path(audio_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {audio_path}"}
        
        audio_bytes = path.read_bytes()
        
        try:
            if need_english:
                result = self.whisper.transcribe_and_translate(audio_bytes)
            else:
                if path.suffix.lower() == ".webm":
                    result = self.whisper.transcribe_webm(audio_bytes)
                else:
                    result = self.whisper.transcribe_wav(audio_bytes)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}