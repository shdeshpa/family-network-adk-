# Agent Handoff Flow

## Complete Pipeline Architecture

This document describes the complete agent handoff flow in the Family Network ADK system, from user input to final storage.

```
┌──────────────┐
│     USER     │ (Audio/Text Input)
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATOR AGENT                              │
│                  (src/agents/adk/orchestrator.py)                        │
│  Coordinates all agents and manages the complete data processing pipeline│
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
       ┌───────────────────┴────────────────────┐
       │                                        │
       │ STEP 1: TRANSCRIPTION (if audio)      │
       │                                        │
       ▼                                        │
┌──────────────────┐                           │
│ Transcription    │ (Optional, only for audio)│
│     Agent        │                           │
└──────┬───────────┘                           │
       │ Transcribed Text                      │
       └───────────────────┬───────────────────┘
                           │
       ┌───────────────────┴────────────────────┐
       │ STEP 2: EXTRACTION                     │
       │                                        │
       ▼                                        │
┌──────────────────────────────────┐           │
│   EXTRACTION AGENT                │           │
│ (src/agents/adk/extraction_agent.py)        │
│                                              │
│ Extracts:                                    │
│ - Persons (name, gender, age, location...)   │
│ - Relationships (spouse, child, parent...)   │
│ - Speaker identification                     │
│ - Languages detected                         │
└──────┬───────────────────────────────────────┘
       │
       │ ExtractionResult {
       │   persons: [ExtractedPerson, ...],
       │   relationships: [ExtractedRelationship, ...],
       │   speaker_name: str,
       │   languages_detected: [str, ...]
       │ }
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  *** NEW AGENT: RELATIONEXPERT AGENT ***                 │
│                (src/agents/adk/relation_expert_agent.py)                 │
│                                                                           │
│ Purpose: Duplicate Detection & Resolution                                │
│                                                                           │
│ Process:                                                                  │
│ 1. Receives extracted persons and relationships                          │
│ 2. For each extracted person:                                            │
│    a. Check against existing CRM V2 database                             │
│    b. Calculate name similarity (using SequenceMatcher)                  │
│    c. Find duplicate candidates (similarity > 85%)                       │
│                                                                           │
│ 3. For high-confidence matches (similarity > 95%):                       │
│    → AUTO-MERGE: Update existing person with new data                    │
│                                                                           │
│ 4. For lower-confidence or multiple candidates:                          │
│    → NEEDS_CLARIFICATION: Use MCP tools to ask user                      │
│       (Currently defaults to CREATE_NEW)                                 │
│                                                                           │
│ 5. Update relationship names if persons were merged                      │
│                                                                           │
│ MCP Tools Available:                                                      │
│ - find_similar_persons(name, threshold)                                  │
│ - get_person_details(person_id)                                          │
│ - ask_duplicate_decision(extracted_name, extracted_data, candidates)     │
│ - merge_person_data(new_data, existing_id, strategy)                     │
│ - get_duplicate_statistics()                                             │
└──────┬──────────────────────────────────────────────────────────────────┘
       │
       │ RelationExpertResult {
       │   success: bool,
       │   persons: [cleaned person data with merges],
       │   relationships: [updated relationships],
       │   merges: [
       │     {action: "auto_merge"/"needs_clarification",
       │      extracted_name, existing_id, confidence}
       │   ],
       │   summary: str
       │ }
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          STORAGE AGENT                                   │
│                  (src/agents/adk/storage_agent.py)                       │
│                                                                           │
│ Purpose: Multi-storage orchestration                                     │
│                                                                           │
│ TOOL 1: Store in GraphLite (graph relationships)                         │
│ - PersonStore: Store persons with location, occupation                   │
│ - FamilyGraph: Store relationships (spouse, parent_child, sibling)       │
│                                                                           │
│ TOOL 2: Store in CRM V2 (structured data)                                │
│ - FamilyRegistry: Create/get family codes                                │
│ - CRMStoreV2: Store person profiles, donations, events, notes            │
│   - Automatically creates families based on surnames + cities            │
│   - Stores relationships in relationships table                          │
│                                                                           │
│ TOOL 3: (Future) Store in Qdrant (text blocks for semantic search)       │
│                                                                           │
│ Note: Uses CLEANED data from RelationExpertAgent (duplicates resolved)   │
└──────┬──────────────────────────────────────────────────────────────────┘
       │
       │ StorageResult {
       │   success: bool,
       │   families_created: [family_codes],
       │   persons_created: [person_ids],
       │   errors: [error messages],
       │   summary: str
       │ }
       │
       ▼
┌──────────────────┐
│   GRAPH AGENT    │ (Legacy - graph visualization)
│                  │
│ Purpose: Build graph representation for visualization
│ (Mostly replaced by GraphLite integration)
└──────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FINAL RESULT                                   │
│                                                                           │
│ Orchestrator returns:                                                    │
│ {                                                                         │
│   success: true,                                                          │
│   steps: [                                                                │
│     {agent: "extraction", status: "done"},                                │
│     {agent: "relation_expert", status: "done"},                           │
│     {agent: "storage", status: "done"},                                   │
│     {agent: "graph", status: "done"}                                      │
│   ],                                                                      │
│   extraction: {...},                                                      │
│   relation_expert: {                                                      │
│     merges: 2,                                                            │
│     auto_merged: 1,                                                       │
│     needs_clarification: 1,                                               │
│     summary: "Processed 3 persons: 1 auto-merged, 3 total"                │
│   },                                                                      │
│   storage: {...},                                                         │
│   graph: {...},                                                           │
│   summary: "Extracted 3 people, 2 relationships. RelationExpert:         │
│             Processed 3 persons: 1 auto-merged, 3 total. Storage: ..."   │
│ }                                                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

## Agent Details

### 1. ExtractionAgent
**File**: `src/agents/adk/extraction_agent.py`

**Input**: Raw text (from user or transcription)

**Output**:
```python
ExtractionResult(
    persons=[ExtractedPerson(name, gender, age, location, phone, email, ...)],
    relationships=[ExtractedRelationship(person1, person2, relation_type)],
    speaker_name=str,
    languages_detected=[str]
)
```

**Responsibilities**:
- Parse natural language text
- Identify persons and their attributes
- Identify relationships between persons
- Support multilingual input (English, Hindi, Marathi, Tamil, Telugu)

---

### 2. RelationExpertAgent ⭐ NEW
**File**: `src/agents/adk/relation_expert_agent.py`

**MCP Server**: `src/mcp/servers/relation_expert_server.py`

**Input**: Extraction result (persons + relationships)

**Output**:
```python
RelationExpertResult(
    success=True,
    persons=[cleaned/merged person data],
    relationships=[updated relationships],
    merges=[{action, extracted_name, existing_id, confidence}],
    errors=[],
    summary="Processed X persons: Y auto-merged, Z total"
)
```

**Responsibilities**:
- **Duplicate Detection**: Compare extracted persons against existing CRM V2 database
- **Name Similarity**: Use SequenceMatcher for fuzzy name matching
- **Auto-Merge**: High-confidence matches (>95% similarity) auto-merge with existing
- **Clarification**: Lower-confidence matches ask user via MCP tools
- **Data Cleaning**: Return deduplicated person list to Storage Agent

**MCP Tools**:
1. `find_similar_persons(name, threshold)` - Find potential duplicates
2. `get_person_details(person_id)` - Get full details of existing person
3. `ask_duplicate_decision(...)` - Ask user to resolve duplicate
4. `merge_person_data(...)` - Merge new data with existing
5. `get_duplicate_statistics()` - Get DB-wide duplicate stats

---

### 3. StorageAgent
**File**: `src/agents/adk/storage_agent.py`

**Input**: Cleaned data from RelationExpertAgent

**Output**:
```python
StorageResult(
    success=True,
    families_created=[family_codes],
    persons_created=[person_ids],
    errors=[],
    summary="Created X families, stored Y persons in CRM V2 and GraphLite"
)
```

**Responsibilities**:
- **TOOL 1**: Store in GraphLite (PersonStore + FamilyGraph)
- **TOOL 2**: Store in CRM V2 (FamilyRegistry + CRMStoreV2)
- **TOOL 3**: (Future) Store in Qdrant for semantic search
- Handle family creation automatically
- Store all relationship types

---

### 4. GraphAgent (Legacy)
**File**: `src/agents/adk/graph_agent.py`

**Purpose**: Build graph representation (mostly replaced by GraphLite integration)

---

## Data Flow Example

### Example Input:
```
"Hi, I'm John Smith from Seattle. My wife Sarah and I have two children,
Tom and Lisa. My phone is 555-1234."
```

### Step 1: Extraction
```python
ExtractionResult(
    persons=[
        ExtractedPerson(name="John Smith", location="Seattle", phone="555-1234", is_speaker=True),
        ExtractedPerson(name="Sarah Smith"),
        ExtractedPerson(name="Tom Smith"),
        ExtractedPerson(name="Lisa Smith")
    ],
    relationships=[
        ExtractedRelationship(person1="John Smith", person2="Sarah Smith", relation_type="spouse"),
        ExtractedRelationship(person1="John Smith", person2="Tom Smith", relation_type="parent_child"),
        ExtractedRelationship(person1="John Smith", person2="Lisa Smith", relation_type="parent_child")
    ]
)
```

### Step 2: RelationExpert (Duplicate Detection)

**Scenario A**: No duplicates found
```python
RelationExpertResult(
    persons=[all 4 persons as-is],
    merges=[],
    summary="Processed 4 persons: 0 auto-merged, 4 total"
)
```

**Scenario B**: John Smith already exists (95% match)
```python
RelationExpertResult(
    persons=[
        {name: "John Smith", existing_id: 82, ...},  # Merged with existing
        ExtractedPerson(name="Sarah Smith"),
        ExtractedPerson(name="Tom Smith"),
        ExtractedPerson(name="Lisa Smith")
    ],
    merges=[
        {action: "auto_merge", extracted_name: "John Smith", existing_id: 82, confidence: 0.97}
    ],
    summary="Processed 4 persons: 1 auto-merged, 4 total"
)
```

### Step 3: Storage
- Creates family "SMITH-SEA-001"
- Stores all 4 persons in CRM V2
- Stores all 4 persons in GraphLite PersonStore
- Creates 3 relationships in GraphLite FamilyGraph
- Updates John's profile if he was merged

---

## Key Features

### Duplicate Prevention
- **85% similarity threshold** for duplicate detection
- **95% threshold** for auto-merge
- **User clarification** for ambiguous cases (via MCP tools)
- **Name normalization** before comparison

### Multi-Storage Architecture
- **GraphLite**: Fast graph queries, relationship traversal
- **CRM V2**: Full-featured CRM with donations, events, notes
- **Qdrant** (future): Semantic search across text blocks

### Agent Communication
- **Async processing** throughout pipeline
- **Structured data** passed between agents
- **Error handling** at each step
- **Comprehensive logging** for debugging

---

## Configuration

### Orchestrator Initialization
```python
from src.agents.adk.orchestrator import FamilyOrchestrator

orchestrator = FamilyOrchestrator(llm_provider="ollama/llama3")
```

### Processing Text
```python
result = await orchestrator.process_text_async("Your family text here")
```

### Processing Audio
```python
result = orchestrator.process_audio("/path/to/audio.mp3")
```

---

## Error Handling

Each agent returns a success flag and error messages:

```python
if result["success"]:
    print(result["summary"])
else:
    print(f"Error: {result.get('error')}")
    for step in result["steps"]:
        if step["status"] == "failed":
            print(f"Failed at: {step['agent']}")
```

---

## Future Enhancements

1. **MCP User Interaction**: Implement actual user prompts for duplicate resolution
2. **Qdrant Integration**: Add semantic search for text blocks
3. **Advanced Merging**: ML-based duplicate detection
4. **Relationship Inference**: Infer missing relationships from context
5. **Batch Processing**: Process multiple inputs in parallel

---

**Author**: Shrinivas Deshpande
**Date**: December 7, 2025
**Copyright**: © 2025 Shrinivas Deshpande. All rights reserved.
