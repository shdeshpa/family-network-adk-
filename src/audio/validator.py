"""Audio validation utilities."""

import numpy as np


class AudioValidator:
    """Validate audio quality and parameters."""
    
    def __init__(
        self,
        min_duration: float = 1.0,
        max_duration: float = 300.0,
        sample_rate: int = 16000
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.sample_rate = sample_rate
    
    def validate(self, audio_data: np.ndarray) -> dict:
        """Validate audio and return status with details."""
        duration = len(audio_data) / self.sample_rate
        is_silent = self._is_silent(audio_data)
        is_clipped = self._is_clipped(audio_data)
        
        errors = []
        if duration < self.min_duration:
            errors.append(f"Too short: {duration:.1f}s < {self.min_duration}s")
        if duration > self.max_duration:
            errors.append(f"Too long: {duration:.1f}s > {self.max_duration}s")
        if is_silent:
            errors.append("Audio is silent")
        if is_clipped:
            errors.append("Audio is clipped")
        
        return {
            "valid": len(errors) == 0,
            "duration": duration,
            "is_silent": is_silent,
            "is_clipped": is_clipped,
            "errors": errors
        }
    
    def _is_silent(self, audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Check if audio is mostly silent."""
        rms = np.sqrt(np.mean(audio ** 2))
        return rms < threshold
    
    def _is_clipped(self, audio: np.ndarray, threshold: float = 0.99) -> bool:
        """Check if audio has clipping."""
        return np.any(np.abs(audio) > threshold)