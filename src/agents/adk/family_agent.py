"""Family Agent - synchronous wrapper for UI compatibility."""

from typing import Optional
from dataclasses import dataclass, field
import concurrent.futures

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.models.lite_llm import LiteLlm
from google.genai import types


@dataclass
class ProcessingResult:
    success: bool
    response: str
    error: str = ""


# Import tools
from src.mcp.servers.nlp_server import (
    normalize_relation, infer_gender, detect_language, extract_family_name
)
from src.mcp.servers.graph_server import (
    add_person, add_spouse, add_parent_child, add_sibling,
    get_person, get_all_persons, get_all_relationships, verify_storage
)


def _run_agent_sync(text: str) -> ProcessingResult:
    """Run agent in isolated context."""
    import asyncio
    
    try:
        model = LiteLlm(model="ollama/llama3")
        
        nlp_tools = [detect_language, normalize_relation, infer_gender, extract_family_name]
        graph_tools = [add_person, add_spouse, add_parent_child, add_sibling,
                       get_person, get_all_persons, get_all_relationships, verify_storage]
        
        agent = Agent(
            name="family_agent",
            model=model,
            instruction="""You are a family data processor. Extract people and relationships from text.

AVAILABLE TOOLS (use ONLY these):
- detect_language(text)
- infer_gender(name)
- extract_family_name(name)
- add_person(name, gender, location)
- add_spouse(person1, person2)
- add_parent_child(parent, child)
- add_sibling(person1, person2)
- get_person(name)
- get_all_persons()
- get_all_relationships()
- verify_storage()

IMPORTANT: Call tools ONE AT A TIME. Do NOT call any tools not listed above.

Steps:
1. Call detect_language with the text
2. For each person: infer_gender, then add_person
3. For relationships: use add_spouse, add_parent_child, or add_sibling
4. Finally call verify_storage to confirm

Use STRING values only. Do not nest tool calls.""",
            tools=nlp_tools + graph_tools
        )
        
        runner = InMemoryRunner(agent=agent, app_name="family")
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session = loop.run_until_complete(
                runner.session_service.create_session(app_name="family", user_id="user")
            )
            
            message = types.Content(role="user", parts=[types.Part(text=f"Process: {text}")])
            
            response_parts = []
            for event in runner.run(user_id="user", session_id=session.id, new_message=message):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_parts.append(part.text)
            
            return ProcessingResult(success=True, response="\n".join(response_parts))
        finally:
            loop.close()
            
    except Exception as e:
        return ProcessingResult(success=False, response="", error=str(e))


def process_family_text(text: str) -> ProcessingResult:
    """Process text using thread pool to avoid event loop conflicts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_agent_sync, text)
        try:
            return future.result(timeout=120)
        except concurrent.futures.TimeoutError:
            return ProcessingResult(success=False, response="", error="Timeout after 120s")
