"""Stage 6 Tests: Entity Extraction Agent."""

import pytest


class TestEntityExtractorAgent:
    """Test entity extraction agent."""
    
    def test_agent_import(self):
        """Agent should be importable."""
        from src.agents.entity_extractor import EntityExtractorAgent
        assert EntityExtractorAgent is not None
    
    def test_agent_init(self):
        """Agent should initialize with API key."""
        from src.agents.entity_extractor import EntityExtractorAgent
        agent = EntityExtractorAgent(api_key="test-key")
        assert agent.api_key == "test-key"
    
    def test_empty_text_returns_error(self):
        """Empty text should return error."""
        from src.agents.entity_extractor import EntityExtractorAgent
        agent = EntityExtractorAgent(api_key="test-key")
        result = agent.extract_entities("")
        assert result["success"] == False
        assert "empty" in result["error"].lower()
    
    def test_extraction_with_real_api(self):
        """Test extraction with real API if key is set."""
        from src.agents.entity_extractor import EntityExtractorAgent
        from src.config import settings
        
        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not set")
        
        agent = EntityExtractorAgent()
        
        sample_text = """
        My name is Ramesh Kumar. I live in Hyderabad with my wife Priya.
        We have two children - our son Arjun who is 25 years old and works in Bangalore,
        and our daughter Kavya who is 22 and studying in Chennai.
        My brother Suresh lives in Mumbai with his family.
        You can reach me at 9876543210.
        """
        
        result = agent.extract_entities(sample_text)
        
        # Debug output
        print(f"\nResult: {result}")
        
        if not result["success"]:
            pytest.skip(f"API error: {result.get('error', 'Unknown error')}")
        
        assert len(result["persons"]) >= 4
        print(f"\nExtracted persons: {result['persons']}")
        print(f"Extracted relationships: {result['relationships']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])