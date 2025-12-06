"""Stage 3B Tests: Whisper Transcription Service."""

import pytest
from pathlib import Path


class TestWhisperService:
    """Test Whisper transcription service."""
    
    def test_service_import(self):
        """WhisperService should be importable."""
        from src.transcription import WhisperService
        assert WhisperService is not None
    
    def test_service_init_with_key(self):
        """Service should initialize with API key."""
        from src.transcription.whisper_service import WhisperService
        service = WhisperService(api_key="test-key")
        assert service.api_key == "test-key"
    
    def test_supported_languages(self):
        """Service should support required languages."""
        from src.transcription.whisper_service import WhisperService
        
        assert "en" in WhisperService.SUPPORTED_LANGUAGES
        assert "mr" in WhisperService.SUPPORTED_LANGUAGES
        assert "te" in WhisperService.SUPPORTED_LANGUAGES
    
    @pytest.mark.skipif(
        not Path("data/recordings/latest_raw.webm").exists(),
        reason="No recording available"
    )
    def test_transcribe_real_file(self):
        """Test transcription with real file if available and API key set."""
        from src.transcription.whisper_service import WhisperService
        from src.config import settings
        
        if not settings.openai_api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        service = WhisperService()
        webm_path = Path("data/recordings/latest_raw.webm")
        webm_data = webm_path.read_bytes()
        
        result = service.transcribe_webm(webm_data)
        
        assert result["success"] == True
        assert len(result["text"]) > 0
        assert result["language"] is not None
        print(f"\nTranscribed: {result['text']}")
        print(f"Language: {result['language']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])