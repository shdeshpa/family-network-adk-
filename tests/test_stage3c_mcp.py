"""Stage 3C Tests: FastMCP Transcription Server."""

import pytest
from pathlib import Path


class TestTranscriptionMCP:
    """Test MCP transcription server."""
    
    def test_mcp_import(self):
        """MCP server should be importable."""
        from src.mcp.transcription_server import mcp
        assert mcp is not None
        assert mcp.name == "transcription-server"
    
    def test_mcp_has_tool_manager(self):
        """MCP should have tool manager."""
        from src.mcp.transcription_server import mcp
        assert mcp._tool_manager is not None
    
    def test_whisper_service_directly(self):
        """Test WhisperService supported languages."""
        from src.transcription.whisper_service import WhisperService
        
        assert "en" in WhisperService.SUPPORTED_LANGUAGES
        assert "mr" in WhisperService.SUPPORTED_LANGUAGES
        assert "te" in WhisperService.SUPPORTED_LANGUAGES
    
    def test_converter_directly(self):
        """Test AudioConverter initialization."""
        from src.audio.converter import AudioConverter
        
        conv = AudioConverter(target_sample_rate=16000)
        assert conv.target_sample_rate == 16000
    
    @pytest.mark.skipif(
        not Path("data/recordings/latest_raw.webm").exists(),
        reason="No recording available"
    )
    def test_transcribe_real_file_via_service(self):
        """Test transcription with real file using service directly."""
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
        print(f"\nTranscribed: {result['text']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])