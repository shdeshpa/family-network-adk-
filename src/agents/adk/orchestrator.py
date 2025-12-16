"""
Orchestrator Agent - coordinates all agents.

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from pathlib import Path
from typing import Optional
import asyncio

from src.agents.adk.transcription_agent import TranscriptionAgent
from src.agents.adk.extraction_agent import ExtractionAgent
from src.agents.adk.relation_expert_agent import RelationExpertAgent
from src.agents.adk.graph_agent import GraphAgent
from src.agents.adk.storage_agent import StorageAgent


class FamilyOrchestrator:
    """Coordinates agents: Transcription → Extraction → RelationExpert → Storage → Graph."""

    def __init__(self, llm_provider: str = "ollama/llama3"):
        """
        Initialize orchestrator.

        Args:
            llm_provider: Model ID (e.g., "ollama/llama3", "groq/mixtral", "openai/gpt-4")
        """
        self.transcription_agent = TranscriptionAgent()
        self.extraction_agent = ExtractionAgent(model_id=llm_provider)
        self.relation_expert_agent = RelationExpertAgent()
        self.storage_agent = StorageAgent()
        self.graph_agent = GraphAgent()
    
    def process_text(self, text: str) -> dict:
        """
        Process text through extraction, storage, and graph building.

        This is the synchronous entry point. Use process_text_async() if
        you're already in an async context.
        """
        return asyncio.run(self._process_text_async(text))

    async def process_text_async(self, text: str) -> dict:
        """Async version for use within event loops."""
        return await self._process_text_async(text)

    async def _process_text_async(self, text: str) -> dict:
        """Async implementation of text processing."""
        result = {
            "success": False,
            "steps": []
        }

        # Step 1: Extract entities
        result["steps"].append({"agent": "extraction", "status": "running"})

        extraction = self.extraction_agent.extract(text)

        if not extraction.success:
            result["steps"][-1]["status"] = "failed"
            result["error"] = extraction.error or "Extraction failed"
            return result

        result["steps"][-1]["status"] = "done"
        # Store extraction as dict for compatibility
        result["extraction"] = {
            "success": extraction.success,
            "persons": [vars(p) for p in extraction.persons],
            "relationships": [vars(r) for r in extraction.relationships],
            "speaker_name": extraction.speaker_name,
            "languages_detected": extraction.languages_detected
        }

        # Step 2: RelationExpert - Duplicate detection and resolution
        result["steps"].append({"agent": "relation_expert", "status": "running"})

        # Convert extraction result to dict for relation expert
        extraction_dict = {
            "success": extraction.success,
            "persons": [
                {
                    "name": p.name,
                    "gender": p.gender,
                    "age": p.age,
                    "location": p.location,
                    "occupation": p.occupation,
                    "phone": p.phone,
                    "email": p.email,
                    "interests": p.interests,
                    "is_speaker": p.is_speaker,
                    "raw_mentions": p.raw_mentions
                }
                for p in extraction.persons
            ],
            "relationships": [
                {
                    "person1": r.person1,
                    "person2": r.person2,
                    "relation_term": r.relation_term,
                    "relation_type": r.relation_type
                }
                for r in extraction.relationships
            ]
        }

        relation_expert_result = await self.relation_expert_agent.process(extraction_dict)

        result["steps"][-1]["status"] = "done"
        result["relation_expert"] = {
            "success": relation_expert_result.success,
            "merges": len(relation_expert_result.merges),
            "auto_merged": len([m for m in relation_expert_result.merges if m.get('action') == 'auto_merge']),
            "needs_clarification": len([m for m in relation_expert_result.merges if m.get('action') == 'needs_clarification']),
            "summary": relation_expert_result.summary
        }

        # Use cleaned data from relation expert for storage
        extraction_dict_cleaned = {
            "success": True,
            "persons": relation_expert_result.persons,
            "relationships": relation_expert_result.relationships
        }

        # Step 3: Store in CRM V2
        result["steps"].append({"agent": "storage", "status": "running"})

        # Use cleaned data from relation expert
        storage_result = await self.storage_agent.store(extraction_dict_cleaned)

        result["steps"][-1]["status"] = "done" if storage_result.success else "failed"
        result["storage"] = {
            "success": storage_result.success,
            "families_created": len(storage_result.families_created),
            "persons_created": len(storage_result.persons_created),
            "duplicates_skipped": [
                {
                    "name": d.name,
                    "existing_id": d.existing_id,
                    "existing_name": d.existing_name,
                    "reason": d.reason
                } for d in storage_result.duplicates_skipped
            ],
            "errors": storage_result.errors,
            "summary": storage_result.summary
        }

        # Step 4: Build graph (legacy - still maintain for compatibility)
        result["steps"].append({"agent": "graph", "status": "running"})

        graph_result = self.graph_agent.build_from_extraction(extraction_dict_cleaned)

        result["steps"][-1]["status"] = "done"
        result["graph"] = graph_result

        result["success"] = True
        result["summary"] = (
            f"Extracted {len(extraction.persons)} people, {len(extraction.relationships)} relationships. "
            f"RelationExpert: {relation_expert_result.summary}. "
            f"Storage: {storage_result.summary}. "
            f"Graph: {len(graph_result.get('persons_created', []))} persons."
        )

        return result
    
    def process_audio(self, audio_path: str) -> dict:
        """Process audio through full pipeline."""
        result = {
            "success": False,
            "steps": []
        }

        # Step 1: Transcribe
        result["steps"].append({"agent": "transcription", "status": "running"})

        trans = self.transcription_agent.process(audio_path)

        if not trans.get("success"):
            result["steps"][-1]["status"] = "failed"
            result["error"] = trans.get("error")
            return result

        result["steps"][-1]["status"] = "done"
        result["transcription"] = trans

        text = trans.get("english_text") or trans.get("text", "")

        # Continue with text processing (includes extraction, storage, graph)
        text_result = self.process_text(text)

        result["steps"].extend(text_result.get("steps", []))
        result["extraction"] = text_result.get("extraction")
        result["storage"] = text_result.get("storage")
        result["graph"] = text_result.get("graph")
        result["success"] = text_result.get("success")
        result["summary"] = text_result.get("summary")

        return result