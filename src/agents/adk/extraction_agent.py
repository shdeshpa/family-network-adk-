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
import uuid

from src.agents.adk.utils.text_utils import TextUtils
from src.agents.adk.utils.relationship_map import RelationshipMap
from src.agents.adk.utils.agent_trajectory import TrajectoryLogger, StepType


@dataclass
class ExtractedPerson:
    """Person extracted from text."""
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    interests: Optional[str] = None  # Activities, hobbies, volunteer work
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


EXTRACTION_PROMPT = """Extract family and social network information from the text below. Output ONLY a JSON object, no other text.

The text may mix English with Hindi/Marathi/Tamil/Telugu. Recognize ALL relationship terms:

FAMILY RELATIONSHIPS (BE VERY CAREFUL - Extract the EXACT term used!):
- wife, husband, son, daughter, brother, sister, father, mother, grandfather, grandmother, uncle, aunt, cousin
- Marathi: bhau (brother), bayko (wife), navra (husband), mulga (son), mulgi (daughter)
- Hindi: bhai (brother), behen (sister), pati (husband), patni (wife)

CRITICAL RELATIONSHIP EXTRACTION RULES:
1. Use the EXACT relationship term mentioned in the text
2. "sister" means SISTER (sibling), NOT wife/spouse
3. "brother" means BROTHER (sibling), NOT husband/spouse
4. "wife"/"husband" are SPOUSE relationships, completely different from siblings
5. If text says "X is sister of Y", extract relation_term as "sister"
6. If text says "X is wife of Y", extract relation_term as "wife"
7. NEVER confuse siblings (brother/sister) with spouses (wife/husband)

NON-FAMILY RELATIONSHIPS (IMPORTANT - Extract these too!):
- friend, colleague, coworker, boss, manager, employee
- mentor, mentee, teacher, student
- fan (fan of someone), follower, admirer
- neighbor, roommate, classmate

Extract ALL available information for each person:
- Name (required)
- Gender (M/F)
- Age or birth year
- Location (city, state, country)
- Occupation/profession
- Phone number (any format)
- Email address
- Interests/Activities: hobbies, volunteer work, temple visits, religious activities, social activities
- Whether they are the speaker (is_speaker: true/false)

JSON format (output ONLY this, nothing else):
{
  "speaker_name": "Name",
  "persons": [
    {
      "name": "Full Name",
      "gender": "M or F",
      "age": 45,
      "location": "City, State",
      "occupation": "Job Title",
      "phone": "123-456-7890",
      "email": "email@example.com",
      "interests": "Temple volunteer, yoga, community service",
      "is_speaker": true
    }
  ],
  "relationships": [
    {"person1": "Name1", "person2": "Name2", "relation_term": "sister"},
    {"person1": "Name3", "person2": "Name4", "relation_term": "colleague"},
    {"person1": "Name5", "person2": "Name6", "relation_term": "fan of"}
  ]
}

CRITICAL: Extract ALL relationships mentioned in the text, including:
- Family relationships (spouse, children, parents, siblings) - USE EXACT TERMS
- Professional relationships (colleague, boss, coworker)
- Social relationships (friend, neighbor, classmate)
- Fan/follower relationships (fan of, admirer of)

IMPORTANT: Extract phone numbers, emails, and activities if mentioned in the text.

VALIDATION: Before outputting, verify that:
- "sister" is used for female siblings, NOT for wives
- "brother" is used for male siblings, NOT for husbands
- "wife" is used for female spouses, NOT for sisters
- "husband" is used for male spouses, NOT for brothers"""


class ExtractionAgent:
    """Agent that extracts family information from text."""
    
    def __init__(self, model_id: str = "ollama/llama3", session_id: Optional[str] = None):
        self.model_id = model_id
        self.relationship_map = RelationshipMap()
        self.text_utils = TextUtils()
        self.session_id = session_id or str(uuid.uuid4())

    def extract(self, text: str) -> ExtractionResult:
        """Extract persons and relationships from text with ReAct pattern logging."""
        # Create trajectory for this extraction
        trajectory = TrajectoryLogger.create_trajectory("ExtractionAgent", self.session_id)

        # OBSERVATION: Record what we received
        trajectory.observe(
            f"Received text input of {len(text)} characters",
            {"text_preview": text[:200] if text else "", "text_length": len(text) if text else 0}
        )

        if not text or not text.strip():
            trajectory.reflect("Text is empty or whitespace only")
            trajectory.error("Cannot extract from empty text")
            trajectory.complete({"success": False, "error": "Empty text"})
            return ExtractionResult(
                persons=[], relationships=[],
                languages_detected=['english'],
                raw_text=text, success=False, error="Empty text"
            )

        # REFLECTION: Analyze the input
        languages = self.text_utils.detect_language_hints(text)
        trajectory.reflect(
            f"Detected languages: {', '.join(languages)}",
            {"languages": languages}
        )

        try:
            # REASONING: Plan the extraction
            trajectory.reason(
                f"Planning extraction using {self.model_id} LLM",
                {"model": self.model_id, "strategy": "JSON extraction with relationship validation"}
            )

            # ACTION: Call LLM for extraction
            trajectory.act(
                f"Calling LLM to extract persons and relationships",
                {"model": self.model_id}
            )
            llm_result = self._call_llm_sync(text)

            # RESULT: Record LLM response
            trajectory.result(
                f"Received LLM response of {len(llm_result)} characters",
                {"response_preview": llm_result[:300] if llm_result else ""}
            )

            # ACTION: Parse LLM response
            trajectory.act("Parsing JSON response from LLM")
            persons, relationships, speaker = self._parse_llm_response(llm_result)

            # RESULT: Record parsing results
            trajectory.result(
                f"Extracted {len(persons)} persons and {len(relationships)} relationships",
                {
                    "person_count": len(persons),
                    "relationship_count": len(relationships),
                    "speaker": speaker,
                    "persons": [p.name for p in persons],
                    "relationships": [{"person1": r.person1, "person2": r.person2, "term": r.relation_term} for r in relationships]
                }
            )

            # REFLECTION: Validate extraction quality
            validation_notes = []
            for rel in relationships:
                if rel.relation_term.lower() in ['sister', 'brother'] and 'wife' in rel.context.lower():
                    validation_notes.append(f"WARNING: Possible confusion between sibling and spouse for {rel.person1}-{rel.person2}")

            if validation_notes:
                trajectory.reflect(
                    "Validation concerns detected: " + "; ".join(validation_notes),
                    {"validation_warnings": validation_notes}
                )
            else:
                trajectory.reflect("Extraction quality looks good - no validation concerns")

            # ACTION: Enhance persons with inferred data
            trajectory.act("Enhancing person data (inferring gender, cleaning names)")
            persons = self._enhance_persons(persons)

            # ACTION: Normalize relationship terms
            trajectory.act("Normalizing relationship terms using RelationshipMap")
            relationships = self._normalize_relationships(relationships)

            # RESULT: Record final normalized relationships
            normalized_info = [
                {
                    "person1": r.person1,
                    "person2": r.person2,
                    "original_term": r.relation_term,
                    "normalized_term": r.normalized_term,
                    "type": r.relation_type
                }
                for r in relationships
            ]
            trajectory.result(
                f"Normalized {len(relationships)} relationships",
                {"normalized_relationships": normalized_info}
            )

            # Complete trajectory
            final_result = {
                "success": True,
                "persons_extracted": len(persons),
                "relationships_extracted": len(relationships),
                "languages": languages
            }
            trajectory.complete(final_result)

            return ExtractionResult(
                persons=persons,
                relationships=relationships,
                languages_detected=languages,
                speaker_name=speaker,
                raw_text=text,
                success=True
            )
        except Exception as e:
            # ERROR: Record the error
            trajectory.error(
                f"Extraction failed: {str(e)}",
                {"exception_type": type(e).__name__, "exception_message": str(e)}
            )
            trajectory.complete({"success": False, "error": str(e)})

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
                        phone=p.get('phone'),
                        email=p.get('email'),
                        interests=p.get('interests'),
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
        # Fix missing values: "age": , -> "age": null,
        json_str = re.sub(r':\s*,', ': null,', json_str)

        # Fix missing values before closing brace: "age": } -> "age": null}
        json_str = re.sub(r':\s*}', ': null}', json_str)

        # Fix missing values before closing bracket: "age": ] -> "age": null]
        json_str = re.sub(r':\s*]', ': null]', json_str)

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


def extract_from_text(text: str, model_id: str = "ollama/llama3", session_id: Optional[str] = None) -> ExtractionResult:
    """Extract family information from text."""
    agent = ExtractionAgent(model_id=model_id, session_id=session_id)
    return agent.extract(text)
