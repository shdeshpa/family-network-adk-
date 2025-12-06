"""Stage 1 Tests: Project Foundation and Configuration."""

import pytest
from pathlib import Path


class TestProjectStructure:
    """Verify project structure follows cursor rules."""
    
    def test_cursorrules_exists(self):
        """Cursor rules file must exist."""
        rules_path = Path(__file__).parent.parent / ".cursorrules"
        assert rules_path.exists(), ".cursorrules file missing"
    
    def test_env_example_exists(self):
        """Environment template must exist."""
        env_path = Path(__file__).parent.parent / ".env.example"
        assert env_path.exists(), ".env.example file missing"
    
    def test_no_deep_nesting(self):
        """Verify no directories exceed 2 levels of nesting."""
        src_path = Path(__file__).parent.parent / "src"
        if src_path.exists():
            for path in src_path.rglob("*"):
                if path.is_dir():
                    relative = path.relative_to(src_path)
                    depth = len(relative.parts)
                    assert depth <= 2, f"Too deep: {path} (depth={depth})"


class TestConfiguration:
    """Test configuration loading."""
    
    def test_settings_import(self):
        """Settings module should import without error."""
        from src.config import settings
        assert settings is not None
    
    def test_audio_settings_defaults(self):
        """Audio settings should have sensible defaults."""
        from src.config import AudioSettings
        audio = AudioSettings()
        assert audio.sample_rate == 16000
        assert audio.channels == 1
    
    def test_database_paths(self):
        """Database paths should be configured."""
        from src.config import DatabaseSettings
        db = DatabaseSettings()
        assert "family_graph" in db.graph_db_path
        assert "persons" in db.persons_db_path
    
    def test_webrtc_settings(self):
        """WebRTC should have STUN server configured."""
        from src.config import WebRTCSettings
        rtc = WebRTCSettings()
        assert "stun" in rtc.stun_server


class TestModels:
    """Test data models."""
    
    def test_person_creation(self):
        """Person model should accept basic fields."""
        from src.models import Person
        p = Person(name="Test User", gender="M", phone="1234567890")
        assert p.name == "Test User"
        assert p.phone == "1234567890"
    
    def test_person_age_calculation(self):
        """Person age should calculate from birth_date."""
        from src.models import Person
        from datetime import date
        p = Person(name="Test", birth_date=date(1990, 1, 1))
        assert p.age is not None
        assert p.age >= 34
    
    def test_relationship_model(self):
        """Relationship model should store connection."""
        from src.models import Relationship
        r = Relationship(from_id=1, to_id=2, relation_type="parent_of")
        assert r.from_id == 1
        assert r.relation_type == "parent_of"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])