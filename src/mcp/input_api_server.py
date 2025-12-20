"""FastAPI HTTP server for text and audio input processing."""

from pathlib import Path
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.agents.adk.orchestrator import FamilyOrchestrator
from src.mcp.fuzzy_matcher import FuzzyPersonMatcher, PronounResolver

# Create FastAPI app
app = FastAPI(title="Family Network Input API", version="1.0.0")

# Lazy-initialized orchestrator
_orchestrator: Optional[FamilyOrchestrator] = None


def get_orchestrator() -> FamilyOrchestrator:
    """Lazy initialization of orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FamilyOrchestrator(llm_provider="ollama/llama3")
    return _orchestrator


# Request/Response models
class TextInputRequest(BaseModel):
    text: str
    context_person_id: Optional[int] = None
    context_person_name: Optional[str] = None


class AudioInputRequest(BaseModel):
    audio_file_path: str
    context_person_id: Optional[int] = None
    context_person_name: Optional[str] = None


class FuzzyMatchRequest(BaseModel):
    query: str
    phone_hint: Optional[str] = None
    context_person_id: Optional[int] = None
    similarity_threshold: Optional[float] = 0.75


class PronounResolveRequest(BaseModel):
    pronoun: str
    context_person_id: Optional[int] = None
    recent_names: Optional[list[str]] = None


@app.post("/tools/process_text_input")
def process_text_input(request: TextInputRequest) -> dict:
    """
    Process text input to create new family members or edit existing ones.

    This tool uses the full extraction pipeline to:
    - Extract person entities and relationships from natural language
    - Detect and merge duplicates
    - Store in CRM database
    - Build family graph

    Args:
        request: TextInputRequest with text and optional context

    Returns:
        dict with processing results
    """
    orchestrator = get_orchestrator()

    # Add context to text if editing existing person
    text = request.text
    if request.context_person_name:
        text = f"About {request.context_person_name}: {text}"

    try:
        # Process through orchestrator (handles extraction, storage, graph)
        result = orchestrator.process_text(text)

        # Add context info to result
        if request.context_person_id:
            result["context"] = {
                "person_id": request.context_person_id,
                "person_name": request.context_person_name,
                "mode": "edit"
            }
        else:
            result["context"] = {
                "mode": "create"
            }

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Text processing failed: {str(e)}",
            "context": {
                "person_id": request.context_person_id,
                "person_name": request.context_person_name
            } if request.context_person_id else {"mode": "create"}
        }


@app.post("/tools/process_audio_input")
def process_audio_input(request: AudioInputRequest) -> dict:
    """
    Process audio input to create new family members or edit existing ones.

    This tool uses the full pipeline to:
    - Transcribe audio to text (supports English, Marathi, Telugu, Hindi)
    - Extract person entities and relationships
    - Detect and merge duplicates
    - Store in CRM database
    - Build family graph

    Args:
        request: AudioInputRequest with audio file path and optional context

    Returns:
        dict with processing results
    """
    orchestrator = get_orchestrator()

    # Validate audio file exists
    audio_path = Path(request.audio_file_path)
    if not audio_path.exists():
        return {
            "success": False,
            "error": f"Audio file not found: {request.audio_file_path}",
            "context": {
                "person_id": request.context_person_id,
                "person_name": request.context_person_name
            } if request.context_person_id else {"mode": "create"}
        }

    try:
        # Process through orchestrator (handles transcription, extraction, storage, graph)
        result = orchestrator.process_audio(str(audio_path))

        # If editing existing person, add context to the extracted text
        if request.context_person_name and result.get("success"):
            result["context"] = {
                "person_id": request.context_person_id,
                "person_name": request.context_person_name,
                "mode": "edit"
            }
        else:
            result["context"] = {
                "mode": "create"
            }

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Audio processing failed: {str(e)}",
            "context": {
                "person_id": request.context_person_id,
                "person_name": request.context_person_name
            } if request.context_person_id else {"mode": "create"}
        }


@app.post("/tools/fuzzy_match_person")
def fuzzy_match_person(request: FuzzyMatchRequest) -> dict:
    """
    Find person(s) matching a query with fuzzy name matching.

    Handles spelling variations (Alka vs Alaka), honorific removal,
    and provides detailed reasoning for debugging.

    Args:
        request: FuzzyMatchRequest with query name and optional hints

    Returns:
        dict with best match, all matches, and reasoning
    """
    try:
        matcher = FuzzyPersonMatcher(
            similarity_threshold=request.similarity_threshold
        )

        result = matcher.find_person(
            query=request.query,
            phone_hint=request.phone_hint,
            context_person_id=request.context_person_id
        )

        # Convert to dict for JSON response
        response = {
            "success": result.success,
            "query": result.query,
            "best_match": {
                "person_id": result.best_match.person_id,
                "full_name": result.best_match.full_name,
                "phone": result.best_match.phone,
                "email": result.best_match.email,
                "city": result.best_match.city,
                "similarity_score": result.best_match.similarity_score,
                "match_reason": result.best_match.match_reason,
                "confidence": result.best_match.confidence
            } if result.best_match else None,
            "all_matches": [
                {
                    "person_id": m.person_id,
                    "full_name": m.full_name,
                    "phone": m.phone,
                    "email": m.email,
                    "city": m.city,
                    "similarity_score": m.similarity_score,
                    "match_reason": m.match_reason,
                    "confidence": m.confidence
                }
                for m in result.all_matches
            ],
            "reasoning": result.reasoning,
            "needs_disambiguation": result.needs_disambiguation,
            "error": result.error
        }

        return response

    except Exception as e:
        return {
            "success": False,
            "query": request.query,
            "best_match": None,
            "all_matches": [],
            "reasoning": [f"Error during fuzzy matching: {str(e)}"],
            "needs_disambiguation": False,
            "error": str(e)
        }


@app.post("/tools/resolve_pronoun")
def resolve_pronoun(request: PronounResolveRequest) -> dict:
    """
    Resolve a pronoun (he/she/they) to an actual person.

    Uses context and gender matching to determine the referent.

    Args:
        request: PronounResolveRequest with pronoun and context

    Returns:
        dict with resolved person and reasoning
    """
    try:
        resolver = PronounResolver()

        result = resolver.resolve(
            pronoun=request.pronoun,
            context_person_id=request.context_person_id,
            recent_names=request.recent_names
        )

        # Convert to dict
        response = {
            "success": result.success,
            "pronoun": result.query,
            "resolved_person": {
                "person_id": result.best_match.person_id,
                "full_name": result.best_match.full_name,
                "phone": result.best_match.phone,
                "email": result.best_match.email,
                "city": result.best_match.city,
                "confidence": result.best_match.confidence
            } if result.best_match else None,
            "reasoning": result.reasoning,
            "error": result.error
        }

        return response

    except Exception as e:
        return {
            "success": False,
            "pronoun": request.pronoun,
            "resolved_person": None,
            "reasoning": [f"Error during pronoun resolution: {str(e)}"],
            "error": str(e)
        }


@app.post("/tools/get_input_help")
def get_input_help() -> dict:
    """
    Get help and examples for using text and audio input tools.

    Returns:
        dict with usage examples and guidelines
    """
    return {
        "success": True,
        "tools": {
            "process_text_input": {
                "description": "Process natural language text to create or edit family members",
                "examples": [
                    {
                        "scenario": "Create new person",
                        "input": "I am Rajkumar Rao, film actor from Mumbai. Phone: +91-98-1234-5678"
                    },
                    {
                        "scenario": "Add family relationship",
                        "input": "My wife is Priya Rao. She's a teacher. We have a son Aarav."
                    },
                    {
                        "scenario": "Edit person details",
                        "input": "His Nakshatra is Rohini. He likes cricket and meditation.",
                        "context": "Provide context_person_id and context_person_name"
                    }
                ],
                "supported_data": [
                    "Names, locations, occupations",
                    "Phone numbers, emails",
                    "Gothra, Nakshatra (Hindu religious data)",
                    "Religious interests, hobbies",
                    "Relationships (family, friends, colleagues)"
                ]
            },
            "process_audio_input": {
                "description": "Process audio recordings to create or edit family members",
                "supported_formats": ["WebM", "WAV"],
                "supported_languages": ["English", "Marathi", "Telugu", "Hindi"],
                "examples": [
                    {
                        "scenario": "Create from audio",
                        "input": "recordings/new_person.webm"
                    },
                    {
                        "scenario": "Edit via audio",
                        "input": "recordings/update.webm",
                        "context": "Provide context_person_id and context_person_name"
                    }
                ]
            },
            "fuzzy_match_person": {
                "description": "Find person(s) with fuzzy name matching - handles spelling variations",
                "features": [
                    "Handles spelling variations (Alka vs Alaka)",
                    "Removes honorifics (Srikanth Garu -> Srikanth)",
                    "Phone number matching boost",
                    "Detailed reasoning for debugging"
                ],
                "examples": [
                    {
                        "scenario": "Find with spelling variation",
                        "query": "Alka Lahoti",
                        "note": "Will match 'Alaka Lahoti' in database"
                    },
                    {
                        "scenario": "Find with phone boost",
                        "query": "Gauri",
                        "phone_hint": "+91-98-7654-3210",
                        "note": "Very high confidence if phone matches"
                    }
                ],
                "parameters": {
                    "query": "Name to search for (required)",
                    "phone_hint": "Optional phone number to boost confidence",
                    "context_person_id": "Optional person ID for context",
                    "similarity_threshold": "Minimum similarity (0.0-1.0, default: 0.75)"
                },
                "returns": {
                    "best_match": "Top matching person with confidence level",
                    "all_matches": "Top 5 matches with similarity scores",
                    "reasoning": "Step-by-step matching logic",
                    "needs_disambiguation": "True if multiple strong matches exist"
                }
            },
            "resolve_pronoun": {
                "description": "Resolve pronouns (he/she/they) to actual person IDs",
                "features": [
                    "Gender-based matching",
                    "Context-aware resolution",
                    "Recently mentioned names support"
                ],
                "examples": [
                    {
                        "scenario": "Resolve 'she' with context",
                        "pronoun": "she",
                        "context_person_id": 123,
                        "note": "Resolves to context person if gender matches"
                    },
                    {
                        "scenario": "Resolve 'he' from recent names",
                        "pronoun": "he",
                        "recent_names": ["Amit Shah", "Priya Sharma"],
                        "note": "Matches first male person from recent names"
                    }
                ],
                "parameters": {
                    "pronoun": "Pronoun to resolve (he/she/him/her/they)",
                    "context_person_id": "Person being edited/discussed",
                    "recent_names": "List of recently mentioned names"
                },
                "returns": {
                    "resolved_person": "Person the pronoun refers to",
                    "reasoning": "How the pronoun was resolved",
                    "error": "Error message if resolution failed"
                }
            }
        },
        "workflow": {
            "steps": [
                "1. Input is transcribed (audio) or used directly (text)",
                "2. ExtractionAgent extracts persons and relationships",
                "3. RelationExpertAgent detects and merges duplicates (uses fuzzy matching)",
                "4. StorageAgent stores in CRM database",
                "5. GraphAgent builds family relationship graph"
            ]
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def run_server(host: str = "0.0.0.0", port: int = 8003):
    """Run the HTTP API server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
