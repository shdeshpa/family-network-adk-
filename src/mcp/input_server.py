"""FastMCP server for text and audio input processing."""

from pathlib import Path
from typing import Optional
import asyncio

from fastmcp import FastMCP

from src.agents.adk.orchestrator import FamilyOrchestrator

# Create MCP server
mcp = FastMCP(
    "input-server",
    instructions="Process text or audio input to create or edit family members and relationships"
)

# Lazy-initialized orchestrator
_orchestrator: Optional[FamilyOrchestrator] = None


def get_orchestrator() -> FamilyOrchestrator:
    """Lazy initialization of orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FamilyOrchestrator(llm_provider="ollama/llama3")
    return _orchestrator


@mcp.tool()
def process_text_input(
    text: str,
    context_person_id: Optional[int] = None,
    context_person_name: Optional[str] = None
) -> dict:
    """
    Process text input to create new family members or edit existing ones.

    This tool uses the full extraction pipeline to:
    - Extract person entities and relationships from natural language
    - Detect and merge duplicates
    - Store in CRM database
    - Build family graph

    Args:
        text: Natural language text describing family members, relationships, or updates
        context_person_id: Optional ID of person being edited (for context)
        context_person_name: Optional name of person being edited (for context)

    Examples:
        # Create new person:
        process_text_input("I am John Smith from Seattle. Software engineer. Phone: 206-555-1234")

        # Add relationship:
        process_text_input("My wife is Jane Smith. She's a doctor in Seattle.")

        # Edit existing person (with context):
        process_text_input(
            "His Nakshatra is Rohini and he likes cricket",
            context_person_id=42,
            context_person_name="Amit Verma"
        )

    Returns:
        dict with:
            - success: bool
            - steps: list of agent steps executed
            - extraction: extracted entities
            - relation_expert: duplicate detection results
            - storage: CRM storage results
            - graph: graph building results
            - summary: human-readable summary
            - error: error message (if failed)
    """
    orchestrator = get_orchestrator()

    # Add context to text if editing existing person
    if context_person_name:
        text = f"About {context_person_name}: {text}"

    try:
        # Process through orchestrator (handles extraction, storage, graph)
        result = orchestrator.process_text(text)

        # Add context info to result
        if context_person_id:
            result["context"] = {
                "person_id": context_person_id,
                "person_name": context_person_name,
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
                "person_id": context_person_id,
                "person_name": context_person_name
            } if context_person_id else {"mode": "create"}
        }


@mcp.tool()
def process_audio_input(
    audio_file_path: str,
    context_person_id: Optional[int] = None,
    context_person_name: Optional[str] = None
) -> dict:
    """
    Process audio input to create new family members or edit existing ones.

    This tool uses the full pipeline to:
    - Transcribe audio to text (supports English, Marathi, Telugu, Hindi)
    - Extract person entities and relationships
    - Detect and merge duplicates
    - Store in CRM database
    - Build family graph

    Args:
        audio_file_path: Path to audio file (WebM or WAV format)
        context_person_id: Optional ID of person being edited (for context)
        context_person_name: Optional name of person being edited (for context)

    Examples:
        # Create new person via audio:
        process_audio_input("recordings/new_member.webm")

        # Edit existing person via audio:
        process_audio_input(
            "recordings/amit_update.webm",
            context_person_id=42,
            context_person_name="Amit Verma"
        )

    Returns:
        dict with:
            - success: bool
            - steps: list of agent steps executed
            - transcription: transcription results
            - extraction: extracted entities
            - relation_expert: duplicate detection results
            - storage: CRM storage results
            - graph: graph building results
            - summary: human-readable summary
            - error: error message (if failed)
    """
    orchestrator = get_orchestrator()

    # Validate audio file exists
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        return {
            "success": False,
            "error": f"Audio file not found: {audio_file_path}",
            "context": {
                "person_id": context_person_id,
                "person_name": context_person_name
            } if context_person_id else {"mode": "create"}
        }

    try:
        # Process through orchestrator (handles transcription, extraction, storage, graph)
        result = orchestrator.process_audio(str(audio_path))

        # If editing existing person, add context to the extracted text
        if context_person_name and result.get("success"):
            # Note: The transcription already happened, but we can add context for future reference
            result["context"] = {
                "person_id": context_person_id,
                "person_name": context_person_name,
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
                "person_id": context_person_id,
                "person_name": context_person_name
            } if context_person_id else {"mode": "create"}
        }


@mcp.tool()
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
                    },
                    {
                        "scenario": "Add relationship to existing person",
                        "input": "Amit Verma is my friend from college",
                        "context": "Specify who 'my' refers to via context"
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
            }
        },
        "workflow": {
            "steps": [
                "1. Input is transcribed (audio) or used directly (text)",
                "2. ExtractionAgent extracts persons and relationships",
                "3. RelationExpertAgent detects and merges duplicates",
                "4. StorageAgent stores in CRM database",
                "5. GraphAgent builds family relationship graph"
            ]
        }
    }


def run_server(host: str = "0.0.0.0", port: int = 8003):
    """Run the MCP server with HTTP transport."""
    # Use default HTTP REST API transport instead of SSE
    mcp.run(host=host, port=port)


if __name__ == "__main__":
    run_server()
