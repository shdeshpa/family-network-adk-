"""Whisper-based transcription service with language detection."""

import io
import tempfile
from pathlib import Path
from typing import Optional

from openai import OpenAI

from src.config import settings
from src.audio.converter import AudioConverter


class WhisperService:
    """Transcription service using OpenAI Whisper API."""
    
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "mr": "Marathi", 
        "te": "Telugu",
        "hi": "Hindi",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.client = OpenAI(api_key=self.api_key)
        self.converter = AudioConverter()
    
    def transcribe_webm(
        self,
        webm_data: bytes,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe WebM audio to text.
        
        Args:
            webm_data: Raw WebM audio bytes
            language: Optional language code (en, mr, te, hi)
                     If None, auto-detects language
        
        Returns:
            dict with: text, language, duration
        """
        # Convert WebM to WAV
        wav_data = self.converter.webm_to_wav(webm_data)
        duration = self.converter.get_duration(webm_data, format="webm")
        
        # Write to temp file (Whisper API needs a file)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            temp_path = f.name
        
        try:
            with open(temp_path, "rb") as audio_file:
                # Transcribe with Whisper
                params = {"model": "whisper-1", "file": audio_file}
                if language:
                    params["language"] = language
                
                response = self.client.audio.transcriptions.create(
                    **params,
                    response_format="verbose_json"
                )
            
            detected_lang = getattr(response, "language", "en")
            text = response.text
            
            return {
                "text": text,
                "language": detected_lang,
                "language_name": self.SUPPORTED_LANGUAGES.get(
                    detected_lang, detected_lang
                ),
                "duration": duration,
                "success": True
            }
        
        except Exception as e:
            return {
                "text": "",
                "language": None,
                "error": str(e),
                "success": False
            }
        
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def transcribe_wav(
        self,
        wav_data: bytes,
        language: Optional[str] = None
    ) -> dict:
        """Transcribe WAV audio to text."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            temp_path = f.name
        
        try:
            with open(temp_path, "rb") as audio_file:
                params = {"model": "whisper-1", "file": audio_file}
                if language:
                    params["language"] = language
                
                response = self.client.audio.transcriptions.create(
                    **params,
                    response_format="verbose_json"
                )
            
            return {
                "text": response.text,
                "language": getattr(response, "language", "en"),
                "success": True
            }
        
        except Exception as e:
            return {"text": "", "error": str(e), "success": False}
        
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def translate_to_english(self, audio_data: bytes, format: str = "webm") -> dict:
        """
        Transcribe and translate audio to English.
        Uses Whisper's translation endpoint.
        """
        if format == "webm":
            wav_data = self.converter.webm_to_wav(audio_data)
        else:
            wav_data = audio_data
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            temp_path = f.name
        
        try:
            with open(temp_path, "rb") as audio_file:
                response = self.client.audio.translations.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            return {
                "text": response.text,
                "original_language": getattr(response, "language", "unknown"),
                "translated_to": "en",
                "success": True
            }
        
        except Exception as e:
            return {"text": "", "error": str(e), "success": False}
        
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def transcribe_and_translate(
        self,
        webm_data: bytes
    ) -> dict:
        """
        Full pipeline: transcribe in original language, then translate if needed.
        
        Returns both original transcription and English translation.
        """
        # First, transcribe in original language
        original = self.transcribe_webm(webm_data)
        
        if not original["success"]:
            return original
        
        result = {
            "original_text": original["text"],
            "original_language": original["language"],
            "original_language_name": original.get("language_name"),
            "duration": original.get("duration"),
            "success": True
        }
        
        # If already English, no translation needed
        if original["language"] == "en":
            result["english_text"] = original["text"]
            result["was_translated"] = False
        else:
            # Translate to English
            translation = self.translate_to_english(webm_data)
            if translation["success"]:
                result["english_text"] = translation["text"]
                result["was_translated"] = True
            else:
                result["english_text"] = original["text"]
                result["was_translated"] = False
                result["translation_error"] = translation.get("error")
        
        return result