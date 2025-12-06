"""Stage 3A Tests: Audio Format Conversion."""

import pytest
from pathlib import Path


class TestAudioConverter:
    """Test audio format conversion."""
    
    def test_converter_init(self):
        """Converter should initialize with sample rate."""
        from src.audio.converter import AudioConverter
        conv = AudioConverter(target_sample_rate=16000)
        assert conv.target_sample_rate == 16000
    
    def test_converter_import(self):
        """AudioConverter should be importable from module."""
        from src.audio import AudioConverter
        assert AudioConverter is not None
    
    def test_webm_to_wav_with_real_file(self):
        """Test conversion if a real WebM file exists."""
        from src.audio.converter import AudioConverter
        
        webm_path = Path("data/recordings/latest_raw.webm")
        if not webm_path.exists():
            pytest.skip("No WebM recording available")
        
        conv = AudioConverter()
        webm_data = webm_path.read_bytes()
        wav_data = conv.webm_to_wav(webm_data)
        
        assert wav_data[:4] == b"RIFF"  # WAV header
        assert len(wav_data) > 0
    
    def test_get_duration_with_real_file(self):
        """Test duration calculation if a real WebM file exists."""
        from src.audio.converter import AudioConverter
        
        webm_path = Path("data/recordings/latest_raw.webm")
        if not webm_path.exists():
            pytest.skip("No WebM recording available")
        
        conv = AudioConverter()
        webm_data = webm_path.read_bytes()
        duration = conv.get_duration(webm_data, format="webm")
        
        assert duration > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])