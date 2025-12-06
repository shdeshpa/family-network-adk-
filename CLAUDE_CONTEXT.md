# Family Network ADK - Project Context

> Use this file when starting a Claude Code session:
> ```bash
> claude "Read CLAUDE_CONTEXT.md first, then help me with [task]"
> ```

---

## Project Overview

**Family Network System** - An agentic AI application for capturing and managing family relationship data through voice/text input.

**Tech Stack:**
- Python 3.11+
- Google ADK (Agent Development Kit) - Multi-agent orchestration
- FastMCP - Tool protocol for agent-tool communication
- GraphLite - Graph database for relationships
- SQLite - CRM data (profiles, donations)
- NiceGUI - Current UI (migrating to React.js + D3.js)
- Whisper - Audio transcription

**Location:** `/Users/polyglotsol/Documents/FALL2025AgentBootcamp/family-network-adk`

---

## Architecture
```
┌─────────────────────────────────────────────────────────────────────────┐
│                              UI LAYER                                    │
│         NiceGUI (current) → React.js + D3.js (planned)                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                  │
│                    /api/chat  /api/process  /api/graph                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ADK ORCHESTRATOR AGENT                              │
│                                                                          │
│   Mediates between three specialized agents:                            │
│                                                                          │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐            │
│   │ INTERACTIVE │ ───► │TRANSCRIPTION│ ───► │  STORAGE    │            │
│   │   AGENT     │      │   AGENT     │      │   AGENT     │            │
│   │             │      │             │      │             │            │
│   │ • WebRTC    │      │ • Whisper   │      │ • GraphLite │            │
│   │ • Text input│      │ • Language  │      │ • CRM SQL   │            │
│   │ • Confirms  │      │ • Extract   │      │ • Qdrant    │            │
│   └─────────────┘      └─────────────┘      └─────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FASTMCP TOOL SERVERS                              │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ audio_server │  │  nlp_server  │  │ graph_server │  │ crm_server  │ │
│  │ (existing)   │  │ (existing)   │  │ (existing)   │  │ (NEW)       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA STORES                                     │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Audio Files │  │   GraphLite  │  │ SQLite (CRM) │  │   Qdrant    │ │
│  │  data/rec/   │  │  (Relations) │  │ data/crm/    │  │  (future)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Completed Modules ✅

### CRM V2 Data Layer
| File | Purpose |
|------|---------|
| `src/graph/models_v2.py` | Data classes: Family, PersonProfileV2, Donation |
| `src/graph/family_registry.py` | Family code generation (SHARMA-HYD-001 format) |
| `src/graph/crm_store_v2.py` | SQLite CRUD for profiles and donations |
| `src/mcp/servers/crm_server.py` | FastMCP tools wrapping CRM operations |

### CRM V2 Tests
| File | Run Command |
|------|-------------|
| `tests/test_crm_v2.py` | `PYTHONPATH=. uv run python tests/test_crm_v2.py` |
| `tests/test_crm_mcp_server.py` | `PYTHONPATH=. uv run python tests/test_crm_mcp_server.py` |

### Existing (from previous work)
| Component | Location |
|-----------|----------|
| GraphLite wrapper | `src/graph/family/` |
| NLP MCP Server | `src/mcp/servers/nlp_server.py` |
| Graph MCP Server | `src/mcp/servers/graph_server.py` |
| FastAPI Backend | `src/api/main.py` |
| NiceGUI App | `src/ui/main_app.py` |
| Audio Processing | `src/audio/` |
| Basic ADK Agents | `src/agents/adk/` |

---

## Pending Work 🚧

### Priority 1: ADK Agent Integration
- [✅] Create `src/agents/adk/storage_agent.py` - Uses crm_server tools
- [✅] Update `src/agents/adk/orchestrator.py` - Route to storage agent
- [✅] Wire Interactive → Transcription → Storage flow
- [ ] Debug and improve family grouping logic in storage agent

### Priority 2: CRM UI
- [ ] Create `src/ui/crm_editor_v2.py` - NiceGUI editor with:
  - Family filter/grouping
  - All V2 fields (occupation, birth_year, interests)
  - Inline donation management
- [ ] Update `src/ui/main_app.py` - Use new CRM editor

### Priority 3: Visualization
- [ ] React.js + D3.js family tree component
- [ ] Embed in NiceGUI or standalone

### Priority 4: Vector Search (Future)
- [ ] Qdrant integration for semantic search on interests
- [ ] Embeddings for family profiles

---

## Key Design Decisions

### Family Identifier Format
- **System key:** UUID (for internal references)
- **User-friendly code:** `SURNAME-CITY-SEQUENCE` (e.g., SHARMA-HYD-001)
- Generated in `FamilyRegistry.create_family()`

### Database Strategy
- Single SQLite database: `data/crm/crm_v2.db`
- Tables: `families`, `profiles`, `donations`
- Both `FamilyRegistry` and `CRMStoreV2` share same DB file

### Interest Fields
- Four categories: religious, spiritual, social, hobbies
- Free-text (newline-separated) - ready for future vector embeddings
- Stored in `profiles` table as TEXT columns

### Agent-Tool Separation
- **Agents** make decisions (which tool to call, in what order)
- **MCP Tools** execute operations (no business logic)
- **Data Layer** handles persistence (no MCP awareness)

---

## MCP Tools Reference

### CRM Server (`src/mcp/servers/crm_server.py`)

**Family Tools:**
- `create_family(surname, city, description)` → Creates family with auto-code
- `preview_family_code(surname, city)` → Preview code without creating
- `get_family(code|family_id|uuid)` → Retrieve family
- `list_families(surname?, city?)` → Search families
- `archive_family(family_id)` → Soft delete

**Person Tools:**
- `add_person(first_name, ...)` → Create profile
- `get_person(person_id)` → Retrieve profile
- `update_person(person_id, ...)` → Update fields
- `search_persons(query?, family_code?, city?, ...)` → Search
- `list_persons(family_code?)` → List all
- `delete_person(person_id)` → Hard delete
- `archive_person(person_id)` → Soft delete
- `get_family_codes()` → Distinct codes for dropdowns

**Donation Tools:**
- `add_donation(person_id, amount, ...)` → Record donation
- `get_donations(person_id)` → List person's donations
- `get_donation_summary(person_id)` → Totals by currency
- `search_donations(cause?, deity?)` → Search across all
- `update_donation(donation_id, ...)` → Update fields
- `delete_donation(donation_id)` → Delete

---

## Commands Reference
```bash
# Run NiceGUI app
uv run python run_ui.py

# Run FastAPI backend
uv run python run_api.py

# Run tests
PYTHONPATH=. uv run python tests/test_crm_v2.py
PYTHONPATH=. uv run python tests/test_crm_mcp_server.py

# Run all tests
PYTHONPATH=. uv run pytest tests/ -v

# Clean CRM database (fresh start)
rm -f data/crm/crm_v2.db
```

---

## File Structure
```
family-network-adk/
├── src/
│   ├── agents/
│   │   └── adk/
│   │       ├── orchestrator.py      # Main orchestrator
│   │       ├── extraction_agent.py  # Entity extraction
│   │       ├── supervisor_agent.py  # Validation
│   │       ├── query_agent.py       # Chat queries
│   │       └── storage_agent.py     # TODO: CRM storage
│   ├── api/
│   │   └── main.py                  # FastAPI routes
│   ├── audio/
│   │   ├── converter.py
│   │   └── processor.py
│   ├── graph/
│   │   ├── models_v2.py             # ✅ NEW: Data classes
│   │   ├── family_registry.py       # ✅ NEW: Family codes
│   │   ├── crm_store_v2.py          # ✅ NEW: CRM storage
│   │   ├── family_graph.py          # GraphLite wrapper
│   │   └── family/                  # Graph operations
│   ├── mcp/
│   │   ├── client.py                # MCP client
│   │   └── servers/
│   │       ├── nlp_server.py        # NLP tools
│   │       ├── graph_server.py      # Graph tools
│   │       └── crm_server.py        # ✅ NEW: CRM tools
│   ├── transcription/
│   │   └── whisper_service.py
│   └── ui/
│       ├── main_app.py              # NiceGUI main app
│       ├── crm_editor.py            # Old CRM editor
│       └── crm_editor_v2.py         # TODO: New editor
├── tests/
│   ├── test_crm_v2.py               # ✅ NEW: Data layer tests
│   └── test_crm_mcp_server.py       # ✅ NEW: MCP tools tests
├── data/
│   ├── crm/
│   │   └── crm_v2.db                # SQLite database
│   ├── graphlite_db/                # GraphLite data
│   └── recordings/                  # Audio files
├── pyproject.toml
├── CLAUDE_CONTEXT.md                # This file
└── README.md
```

---

## Next Session Starter

Copy this to start your next Claude Code session:
```
Read CLAUDE_CONTEXT.md in the project root. Then help me with:
[YOUR TASK HERE]

The project is at: /Users/polyglotsol/Documents/FALL2025AgentBootcamp/family-network-adk
```

Example tasks:
- "Create the storage_agent.py that uses crm_server MCP tools"
- "Build crm_editor_v2.py with family grouping and donation inline editing"
- "Add D3.js family tree visualization"
- "Wire up the full agent pipeline: Interactive → Transcription → Storage"
