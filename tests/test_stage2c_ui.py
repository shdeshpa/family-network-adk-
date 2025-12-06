"""Stage 2C Tests: NiceGUI Audio Recorder."""

import pytest


class TestAudioRecorderUI:
    """Test UI components."""
    
    def test_audio_recorder_import(self):
        """AudioRecorderUI should import successfully."""
        from src.ui.audio_recorder import AudioRecorderUI
        assert AudioRecorderUI is not None
    
    def test_main_app_import(self):
        """FamilyNetworkApp should import successfully."""
        from src.ui.main_app import FamilyNetworkApp
        assert FamilyNetworkApp is not None
    
    def test_recordings_dir_creation(self):
        """App should create recordings directory."""
        from src.ui.main_app import FamilyNetworkApp
        app = FamilyNetworkApp()
        assert app.recordings_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])