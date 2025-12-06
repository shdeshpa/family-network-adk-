"""Stage 2 Tests: Audio Processing."""

import pytest
import numpy as np


class TestAudioProcessor:
    """Test audio processing utilities."""
    
    def test_processor_init(self):
        """Processor should initialize with sample rate."""
        from src.audio.processor import AudioProcessor
        proc = AudioProcessor(sample_rate=16000)
        assert proc.sample_rate == 16000
    
    def test_normalize_audio(self):
        """Normalize should scale audio to -1 to 1."""
        from src.audio.processor import AudioProcessor
        proc = AudioProcessor()
        audio = np.array([0.0, 0.5, -0.5, 0.25], dtype=np.float32)
        normalized = proc.normalize(audio)
        assert np.max(np.abs(normalized)) <= 1.0
    
    def test_noise_removal_returns_same_shape(self):
        """Noise removal should return same shape array."""
        from src.audio.processor import AudioProcessor
        proc = AudioProcessor(sample_rate=16000)
        audio = np.random.randn(16000).astype(np.float32) * 0.5
        reduced = proc.remove_noise(audio)
        assert reduced.shape == audio.shape
    
    def test_bytes_conversion_roundtrip(self):
        """Audio should survive bytes conversion roundtrip."""
        from src.audio.processor import AudioProcessor
        proc = AudioProcessor(sample_rate=16000)
        original = np.array([0.0, 0.5, -0.5, 0.25, 0.1], dtype=np.float32)
        wav_bytes = proc.numpy_to_bytes(original)
        recovered = proc.bytes_to_numpy(wav_bytes)
        assert np.allclose(original, recovered, atol=0.001)


class TestAudioValidator:
    """Test audio validation."""
    
    def test_valid_audio(self):
        """Valid audio should pass validation."""
        from src.audio.validator import AudioValidator
        validator = AudioValidator(sample_rate=16000)
        # 2 seconds of sine wave (guaranteed valid)
        t = np.linspace(0, 2, 32000)
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        result = validator.validate(audio)
        assert result["valid"] == True
        assert result["duration"] == 2.0
    
    def test_silent_audio_fails(self):
        """Silent audio should fail validation."""
        from src.audio.validator import AudioValidator
        validator = AudioValidator(sample_rate=16000)
        audio = np.zeros(32000, dtype=np.float32)
        result = validator.validate(audio)
        assert result["valid"] == False
        assert result["is_silent"] == True
    
    def test_too_short_fails(self):
        """Audio shorter than minimum should fail."""
        from src.audio.validator import AudioValidator
        validator = AudioValidator(min_duration=2.0, sample_rate=16000)
        audio = np.random.randn(8000).astype(np.float32) * 0.3
        result = validator.validate(audio)
        assert result["valid"] == False
        assert "Too short" in result["errors"][0]
    
    def test_clipped_audio_detected(self):
        """Clipped audio should be detected."""
        from src.audio.validator import AudioValidator
        validator = AudioValidator(sample_rate=16000)
        audio = np.ones(32000, dtype=np.float32) * 0.5
        audio[1000:2000] = 1.0  # Clipped section
        result = validator.validate(audio)
        assert result["is_clipped"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    