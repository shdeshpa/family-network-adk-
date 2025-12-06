"""FastMCP server for audio transcription with HTTP transport."""

import base64
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from src.transcription.whisper_service import WhisperService
from src.audio.converter import AudioConverter

# Create MCP server with HTTP transport
mcp = FastMCP(
    "transcription-server",
    instructions="Audio transcription service supporting English, Marathi, Telugu, Hindi"
)

# Initialize services
whisper_service: Optional[WhisperService] = None
converter: Optional[AudioConverter] = None


def get_whisper_service() -> WhisperService:
    """Lazy initialization of Whisper service."""
    global whisper_service
    if whisper_service is None:
        whisper_service = WhisperService()
    return whisper_service


def get_converter() -> AudioConverter:
    """Lazy initialization of audio converter."""
    global converter
    if converter is None:
        converter = AudioConverter()
    return converter


@mcp.tool()
def transcribe_audio_file(file_path: str, language: Optional[str] = None) -> dict:
    """
    Transcribe an audio file to text.
    
    Args:
        file_path: Path to audio file (WebM or WAV)
        language: Optional language code (en, mr, te, hi)
    
    Returns:
        dict with text, language, duration, success
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    
    audio_data = path.read_bytes()
    service = get_whisper_service()
    
    if path.suffix.lower() == ".webm":
        return service.transcribe_webm(audio_data, language=language)
    elif path.suffix.lower() == ".wav":
        return service.transcribe_wav(audio_data, language=language)
    else:
        return {"success": False, "error": f"Unsupported format: {path.suffix}"}


@mcp.tool()
def transcribe_audio_base64(
    audio_base64: str,
    format: str = "webm",
    language: Optional[str] = None
) -> dict:
    """
    Transcribe base64-encoded audio to text.
    
    Args:
        audio_base64: Base64-encoded audio data
        format: Audio format (webm or wav)
        language: Optional language code (en, mr, te, hi)
    
    Returns:
        dict with text, language, duration, success
    """
    try:
        audio_data = base64.b64decode(audio_base64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64: {str(e)}"}
    
    service = get_whisper_service()
    
    if format == "webm":
        return service.transcribe_webm(audio_data, language=language)
    elif format == "wav":
        return service.transcribe_wav(audio_data, language=language)
    else:
        return {"success": False, "error": f"Unsupported format: {format}"}


@mcp.tool()
def transcribe_and_translate(file_path: str) -> dict:
    """
    Transcribe audio and translate to English if needed.
    
    Args:
        file_path: Path to audio file (WebM or WAV)
    
    Returns:
        dict with original_text, english_text, language, was_translated
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    
    audio_data = path.read_bytes()
    service = get_whisper_service()
    
    return service.transcribe_and_translate(audio_data)


@mcp.tool()
def convert_audio_format(
    input_path: str,
    output_path: str,
    target_format: str = "wav"
) -> dict:
    """
    Convert audio file to different format.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output file
        target_format: Target format (wav)
    
    Returns:
        dict with success, output_path, duration
    """
    input_file = Path(input_path)
    if not input_file.exists():
        return {"success": False, "error": f"File not found: {input_path}"}
    
    conv = get_converter()
    
    try:
        if target_format == "wav" and input_file.suffix.lower() == ".webm":
            conv.webm_to_wav_file(input_path, output_path)
            duration = conv.get_duration(input_file.read_bytes(), format="webm")
            return {
                "success": True,
                "output_path": output_path,
                "duration": duration
            }
        else:
            return {
                "success": False,
                "error": f"Conversion from {input_file.suffix} to {target_format} not supported"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_supported_languages() -> dict:
    """
    Get list of supported languages for transcription.
    
    Returns:
        dict with language codes and names
    """
    return {
        "success": True,
        "languages": WhisperService.SUPPORTED_LANGUAGES
    }


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the MCP server with HTTP transport."""
    mcp.run(
        transport="sse",
        host=host,
        port=port
    )


if __name__ == "__main__":
    run_server()