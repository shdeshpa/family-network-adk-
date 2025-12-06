"""
Audio Orchestrator - Coordinates the audio processing pipeline.

Flow:
1. Audio → Whisper transcription
2. Text → Extraction Agent
3. Extraction → Supervisor Agent
4. Validated → Save to Graph
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from src.agents.adk.extraction_agent import ExtractionAgent, ExtractionResult
from src.agents.adk.supervisor_agent import SupervisorAgent, SupervisorResult
from src.graph.family.graph import FamilyGraph


@dataclass
class ProcessingStep:
    """Single step in processing pipeline."""
    name: str
    status: str = "pending"  # pending, running, completed, failed
    message: str = ""
    duration_ms: int = 0


@dataclass
class AudioProcessingResult:
    """Complete result from audio processing."""
    transcription: str = ""
    extraction: Optional[ExtractionResult] = None
    validation: Optional[SupervisorResult] = None
    steps: list[ProcessingStep] = field(default_factory=list)
    persons_added: int = 0
    relationships_added: int = 0
    success: bool = True
    error: Optional[str] = None


class AudioOrchestrator:
    """
    Orchestrates the audio → graph pipeline.
    
    Usage:
        orchestrator = AudioOrchestrator()
        result = orchestrator.process_audio(audio_path)
        # or
        result = orchestrator.process_text(transcription)
    """
    
    def __init__(
        self,
        model_id: str = "ollama/llama3",
        graph: FamilyGraph = None
    ):
        self.model_id = model_id
        self.graph = graph or FamilyGraph()
        self.extraction_agent = ExtractionAgent(model_id=model_id)
        self.supervisor_agent = SupervisorAgent()
    
    def process_text(self, text: str, save_to_graph: bool = False) -> AudioProcessingResult:
        """
        Process transcribed text through the pipeline.
        
        Args:
            text: Transcribed text
            save_to_graph: Whether to save results to graph
            
        Returns:
            AudioProcessingResult with all steps
        """
        import time
        
        result = AudioProcessingResult(transcription=text)
        
        # Step 1: Extraction
        step1 = ProcessingStep(name="Extraction Agent", status="running")
        result.steps.append(step1)
        
        start = time.time()
        try:
            extraction = self.extraction_agent.extract(text)
            step1.duration_ms = int((time.time() - start) * 1000)
            
            if extraction.success:
                step1.status = "completed"
                step1.message = f"Found {len(extraction.persons)} persons, {len(extraction.relationships)} relationships"
                result.extraction = extraction
            else:
                step1.status = "failed"
                step1.message = extraction.error or "Extraction failed"
                result.success = False
                result.error = step1.message
                return result
        except Exception as e:
            step1.status = "failed"
            step1.message = str(e)
            result.success = False
            result.error = str(e)
            return result
        
        # Step 2: Validation/Supervision
        step2 = ProcessingStep(name="Supervisor Agent", status="running")
        result.steps.append(step2)
        
        start = time.time()
        try:
            validation = self.supervisor_agent.validate(extraction)
            step2.duration_ms = int((time.time() - start) * 1000)
            
            if validation.success:
                step2.status = "completed"
                step2.message = f"Validated {len(validation.persons)} persons, {len(validation.relationships)} relationships"
                result.validation = validation
            else:
                step2.status = "failed"
                step2.message = validation.error or "Validation failed"
                result.success = False
                result.error = step2.message
                return result
        except Exception as e:
            step2.status = "failed"
            step2.message = str(e)
            result.success = False
            result.error = str(e)
            return result
        
        # Step 3: Save to graph (optional)
        if save_to_graph and validation.success:
            step3 = ProcessingStep(name="Save to Graph", status="running")
            result.steps.append(step3)
            
            start = time.time()
            try:
                persons_added, rels_added = self._save_to_graph(validation)
                step3.duration_ms = int((time.time() - start) * 1000)
                step3.status = "completed"
                step3.message = f"Added {persons_added} persons, {rels_added} relationships"
                result.persons_added = persons_added
                result.relationships_added = rels_added
            except Exception as e:
                step3.status = "failed"
                step3.message = str(e)
        
        return result
    
    def process_audio(self, audio_path: str, save_to_graph: bool = False) -> AudioProcessingResult:
        """
        Process audio file through the pipeline.
        
        Args:
            audio_path: Path to audio file
            save_to_graph: Whether to save results to graph
            
        Returns:
            AudioProcessingResult with all steps
        """
        import time
        
        result = AudioProcessingResult()
        
        # Step 0: Transcription
        step0 = ProcessingStep(name="Transcription (Whisper)", status="running")
        result.steps.append(step0)
        
        start = time.time()
        try:
            transcription = self._transcribe(audio_path)
            step0.duration_ms = int((time.time() - start) * 1000)
            
            if transcription:
                step0.status = "completed"
                step0.message = f"Transcribed {len(transcription)} characters"
                result.transcription = transcription
            else:
                step0.status = "failed"
                step0.message = "Transcription returned empty"
                result.success = False
                result.error = step0.message
                return result
        except Exception as e:
            step0.status = "failed"
            step0.message = str(e)
            result.success = False
            result.error = str(e)
            return result
        
        # Continue with text processing
        text_result = self.process_text(transcription, save_to_graph)
        
        # Merge results
        result.extraction = text_result.extraction
        result.validation = text_result.validation
        result.steps.extend(text_result.steps)
        result.persons_added = text_result.persons_added
        result.relationships_added = text_result.relationships_added
        result.success = text_result.success
        result.error = text_result.error
        
        return result
    
    def _transcribe(self, audio_path: str) -> str:
        """Transcribe audio using Whisper."""
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result.get("text", "")
        except ImportError:
            # Fallback: try OpenAI Whisper API
            raise ImportError("Whisper not installed. Run: pip install openai-whisper")
    
    def _save_to_graph(self, validation: SupervisorResult) -> tuple[int, int]:
        """Save validated results to graph."""
        persons_added = 0
        rels_added = 0
        
        # Add persons
        for person in validation.persons:
            existing = self.graph.get_person(person.name)
            if not existing:
                result = self.graph.add_person(
                    name=person.name,
                    gender=person.gender,
                    family_name=person.family_name or validation.family_name,
                    location=person.location,
                    marital_status=person.marital_status
                )
                if result:
                    persons_added += 1
            else:
                # Update existing person with new info
                self.graph.update_person(
                    person.name,
                    gender=person.gender or existing.gender,
                    family_name=person.family_name or validation.family_name or existing.family_name,
                    marital_status=person.marital_status or existing.marital_status
                )
        
        # Add relationships (skip reciprocals as they're auto-created)
        seen_rels = set()
        for rel in validation.relationships:
            if rel.is_reciprocal:
                continue
            
            key = (rel.person1.lower(), rel.person2.lower(), rel.relation_type)
            if key in seen_rels:
                continue
            seen_rels.add(key)
            
            success = False
            if rel.relation_type == "PARENT_OF":
                success = self.graph.add_parent_child(rel.person1, rel.person2)
            elif rel.relation_type == "SPOUSE_OF":
                success = self.graph.add_spouse(rel.person1, rel.person2)
            elif rel.relation_type == "SIBLING_OF":
                success = self.graph.add_sibling(rel.person1, rel.person2)
            
            if success:
                rels_added += 1
        
        return persons_added, rels_added


# Convenience function
def process_family_text(text: str, save: bool = False) -> AudioProcessingResult:
    """Process family text and optionally save to graph."""
    orchestrator = AudioOrchestrator()
    return orchestrator.process_text(text, save_to_graph=save)
