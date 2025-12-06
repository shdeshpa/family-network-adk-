"""Audio format conversion utilities."""

import io
from pathlib import Path
from typing import Union

from pydub import AudioSegment


class AudioConverter:
    """Convert between audio formats."""
    
    def __init__(self, target_sample_rate: int = 16000):
        self.target_sample_rate = target_sample_rate
    
    def webm_to_wav(self, webm_data: bytes) -> bytes:
        """Convert WebM audio bytes to WAV bytes."""
        audio = AudioSegment.from_file(io.BytesIO(webm_data), format="webm")
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(self.target_sample_rate)
        
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()
    
    def webm_to_wav_file(
        self,
        webm_path: Union[str, Path],
        wav_path: Union[str, Path]
    ) -> Path:
        """Convert WebM file to WAV file."""
        webm_path = Path(webm_path)
        wav_path = Path(wav_path)
        
        audio = AudioSegment.from_file(str(webm_path), format="webm")
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(self.target_sample_rate)
        audio.export(str(wav_path), format="wav")
        
        return wav_path
    
    def get_duration(self, audio_bytes: bytes, format: str = "webm") -> float:
        """Get duration of audio in seconds."""
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
        return len(audio) / 1000.0