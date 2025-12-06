"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioSettings(BaseSettings):
    """Audio capture and processing settings."""
    
    model_config = SettingsConfigDict(env_prefix="AUDIO_")
    
    sample_rate: int = 16000
    channels: int = 1
    max_recording_seconds: int = 600


class DatabaseSettings(BaseSettings):
    """Database path settings."""
    
    graph_db_path: str = "data/family_graph.db"
    persons_db_path: str = "data/persons.db"
    crm_db_path: str = "data/crm.db"
    
    def ensure_dirs(self) -> None:
        """Create data directory if needed."""
        Path("data").mkdir(exist_ok=True)


class WebRTCSettings(BaseSettings):
    """WebRTC configuration."""
    
    model_config = SettingsConfigDict(env_prefix="WEBRTC_")
    
    stun_server: str = "stun:stun.l.google.com:19302"


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    openai_api_key: str = ""
    google_api_key: str = ""
    
    audio: AudioSettings = AudioSettings()
    database: DatabaseSettings = DatabaseSettings()
    webrtc: WebRTCSettings = WebRTCSettings()


settings = Settings()