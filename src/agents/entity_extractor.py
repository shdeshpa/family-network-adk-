"""Entity extraction agent using Google ADK."""

import json
from typing import Optional

from google import genai
from google.genai import types

from src.config import settings


class EntityExtractorAgent:
    """Extract family entities and relationships from text."""
    
    EXTRACTION_PROMPT = """You are a family information extraction assistant.
    
Extract the following from the given text:
1. **persons**: List of people mentioned with their attributes
2. **relationships**: Family relationships between people
3. **contact_info**: Phone numbers, emails, locations

For each person, extract:
- name (required)
- gender (M/F/Unknown)
- estimated_age or birth_year if mentioned
- location if mentioned
- phone if mentioned
- email if mentioned
- interests or occupations if mentioned

For relationships, identify:
- parent_child (who is parent of whom)
- spouse (married couples)
- sibling (brothers/sisters)

Return ONLY valid JSON in this exact format:
{
    "persons": [
        {"name": "...", "gender": "...", "location": "...", "phone": "...", "interests": [...]}
    ],
    "relationships": [
        {"type": "parent_child", "parent": "person_name", "child": "person_name"},
        {"type": "spouse", "person1": "person_name", "person2": "person_name"},
        {"type": "sibling", "person1": "person_name", "person2": "person_name"}
    ]
}
"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.google_api_key
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash-exp"
    
    def extract_entities(self, text: str) -> dict:
        """
        Extract family entities from transcribed text.
        
        Args:
            text: Transcribed speech text
            
        Returns:
            dict with persons, relationships
        """
        if not text or not text.strip():
            return {"success": False, "error": "Empty text provided"}
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"{self.EXTRACTION_PROMPT}\n\nText to analyze:\n{text}",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2000
                )
            )
            
            # Parse JSON from response
            response_text = response.text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            extracted = json.loads(response_text.strip())
            
            return {
                "success": True,
                "persons": extracted.get("persons", []),
                "relationships": extracted.get("relationships", []),
                "raw_text": text
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse response: {str(e)}",
                "raw_response": response_text if 'response_text' in locals() else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_from_conversation(self, messages: list[str]) -> dict:
        """
        Extract entities from multiple conversation turns.
        
        Args:
            messages: List of transcribed messages
            
        Returns:
            Consolidated extraction results
        """
        combined_text = "\n".join(messages)
        return self.extract_entities(combined_text)


# Simpler function for direct use
def extract_family_info(text: str, api_key: Optional[str] = None) -> dict:
    """Convenience function to extract family info from text."""
    agent = EntityExtractorAgent(api_key=api_key)
    return agent.extract_entities(text)