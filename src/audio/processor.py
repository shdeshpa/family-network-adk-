"""Audio processing with noise removal."""

import io
import wave
from pathlib import Path
from typing import Union

import numpy as np
import noisereduce as nr


class AudioProcessor:
    """Process audio: noise removal and normalization."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
    
    def remove_noise(
        self,
        audio_data: np.ndarray,
        noise_clip: np.ndarray | None = None
    ) -> np.ndarray:
        """Remove background noise from audio."""
        reduced = nr.reduce_noise(
            y=audio_data,
            sr=self.sample_rate,
            y_noise=noise_clip,
            prop_decrease=0.8,
            stationary=noise_clip is None
        )
        return reduced
    
    def normalize(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to -1 to 1 range."""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val
        return audio_data
    
    def bytes_to_numpy(self, audio_bytes: bytes) -> np.ndarray:
        """Convert WAV bytes to numpy array."""
        with io.BytesIO(audio_bytes) as buf:
            with wave.open(buf, 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                return audio.astype(np.float32) / 32768.0
    
    def numpy_to_bytes(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy array to WAV bytes."""
        audio_int16 = (audio_data * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio_int16.tobytes())
        return buf.getvalue()