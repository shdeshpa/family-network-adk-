"""
Extraction Agent - First pass extraction from text.

Extracts persons, relationships, and qualities from transcribed audio.
Supports multilingual input (English, Hindi, Marathi, Tamil, Telugu).

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import re

from src.agents.adk.utils.text_utils import TextUtils
from src.agents.adk.utils.relationship_map import RelationshipMap


@dataclass
class ExtractedPerson:
    """Person extracted from text."""
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    is_speaker: bool = False
    raw_mentions: list[str] = field(default_factory=list)


@dataclass
class ExtractedRelationship:
    """Relationship extracted from text."""
    person1: str
    person2: str
    relation_term: str
    normalized_term: str
    relation_type: str
    context: str = ""


@dataclass 
class ExtractionResult:
    """Result from extraction agent."""
    persons: list[ExtractedPerson]
    relationships: list[ExtractedRelationship]
    languages_detected: list[str]
    speaker_name: Optional[str] = None
    raw_text: str = ""
    success: bool = True
    error: Optional[str] = None


EXTRACTION_PROMPT = """Extract family information from the text below. Output ONLY a JSON object, no other text.

The text may mix English with Hindi/Marathi/Tamil/Telugu. Recognize relationship terms:
- wife, husband, son, daughter, brother, sister, father, mother
- Marathi: bhau (brother), bayko (wife), navra (husband), mulga (son), mulgi (daughter)
- Hindi: bhai (brother), behen (sister), pati (husband), patni (wife)

JSON format (output ONLY this, nothing else):
{"speaker_name":"Name","persons":[{"name":"Name","gender":"M or F","location":"City","is_speaker":true}],"relationships":[{"person1":"Name1","person2":"Name2","relation_term":"wife"}]}"""


class ExtractionAgent:
    """Agent that extracts family information from text."""
    
    def __init__(self, model_id: str = "ollama/llama3"):
        self.model_id = model_id
        self.relationship_map = RelationshipMap()
        self.text_utils = TextUtils()
    
    def extract(self, text: str) -> ExtractionResult:
        """Extract persons and relationships from text."""
        if not text or not text.strip():
            return ExtractionResult(
                persons=[], relationships=[],
                languages_detected=['english'],
                raw_text=text, success=False, error="Empty text"
            )
        
        languages = self.text_utils.detect_language_hints(text)
        
        try:
            llm_result = self._call_llm_sync(text)
            persons, relationships, speaker = self._parse_llm_response(llm_result)
            persons = self._enhance_persons(persons)
            relationships = self._normalize_relationships(relationships)
            
            return ExtractionResult(
                persons=persons,
                relationships=relationships,
                languages_detected=languages,
                speaker_name=speaker,
                raw_text=text,
                success=True
            )
        except Exception as e:
            return ExtractionResult(
                persons=[], relationships=[],
                languages_detected=languages,
                raw_text=text, success=False, error=str(e)
            )
    
    def _call_llm_sync(self, text: str) -> str:
        """Call LLM synchronously."""
        try:
            from litellm import completion
            
            response = completion(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            
            return response.choices[0].message.content or ""
            
        except ImportError:
            return self._call_ollama_direct(text)
    
    def _call_ollama_direct(self, text: str) -> str:
        """Call Ollama directly via HTTP."""
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"{EXTRACTION_PROMPT}\n\nText:\n{text}",
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama error: {response.status_code}")
    
    def _parse_llm_response(self, response: str) -> tuple:
        """Parse LLM JSON response with robust error handling."""
        persons = []
        relationships = []
        speaker = None
        
        if not response:
            return persons, relationships, speaker
        
        # Try to extract JSON from response
        json_str = self._extract_json(response)
        
        if not json_str:
            print(f"Could not extract JSON from response")
            return persons, relationships, speaker
        
        try:
            data = json.loads(json_str)
            
            speaker = data.get('speaker_name')
            
            for p in data.get('persons', []):
                name = p.get('name', '')
                if name:
                    persons.append(ExtractedPerson(
                        name=name,
                        gender=p.get('gender'),
                        age=p.get('age'),
                        location=p.get('location'),
                        occupation=p.get('occupation'),
                        is_speaker=p.get('is_speaker', False)
                    ))
            
            for r in data.get('relationships', []):
                person1 = r.get('person1', '')
                person2 = r.get('person2', '')
                relation_term = r.get('relation_term', '')
                
                if person1 and person2 and relation_term:
                    relationships.append(ExtractedRelationship(
                        person1=person1,
                        person2=person2,
                        relation_term=relation_term,
                        normalized_term='',
                        relation_type='',
                        context=r.get('context', '')
                    ))
                    
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Attempted to parse: {json_str[:300]}...")
        
        return persons, relationships, speaker
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text, handling common LLM quirks."""
        if not text:
            return None
        
        # Method 1: Find JSON between braces
        # Find the first { and last }
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1 or end <= start:
            return None
        
        json_str = text[start:end + 1]
        
        # Clean up common issues
        # Replace null (string) with null (json)
        json_str = re.sub(r':\s*null\s*([,}])', r': null\1', json_str)
        
        # Remove trailing commas before } or ]
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Try to parse and fix incrementally
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # Try fixing common issues
            pass
        
        # Method 2: Try to find a complete JSON object using bracket matching
        depth = 0
        start_idx = None
        
        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start_idx = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start_idx is not None:
                    candidate = text[start_idx:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except:
                        pass
        
        # Return best effort
        return json_str
    
    def _enhance_persons(self, persons: list[ExtractedPerson]) -> list[ExtractedPerson]:
        """Enhance persons with inferred data."""
        for person in persons:
            if person.name:
                person.name = self.text_utils.clean_name(person.name)
                if not person.gender:
                    person.gender = self.text_utils.infer_gender_from_name(person.name)
        return persons
    
    def _normalize_relationships(self, relationships: list[ExtractedRelationship]) -> list[ExtractedRelationship]:
        """Normalize relationship terms."""
        for rel in relationships:
            if rel.relation_term:
                info = self.relationship_map.normalize(rel.relation_term)
                if info:
                    rel.normalized_term = info.term
                    rel.relation_type = info.relation_type
                else:
                    rel.normalized_term = rel.relation_term.lower()
                    rel.relation_type = "unknown"
        return relationships


def extract_from_text(text: str, model_id: str = "ollama/llama3") -> ExtractionResult:
    """Extract family information from text."""
    agent = ExtractionAgent(model_id=model_id)
    return agent.extract(text)
