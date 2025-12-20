# Agent Trajectory Display Implementation Plan

## Problem Statement
User wants to see full agent trajectories with ReAct pattern (Reasoning → Action → Observation) displayed in the UI, similar to Google ADK documentation style. Currently:
- ❌ Trajectories are created but NOT collected by orchestrator
- ❌ Trajectories are NOT passed through MCP API to UI
- ❌ UI has no proper component for rendering agent trajectories

## System Architecture

### Current Trajectory System (`agent_trajectory.py`)
```python
- TrajectoryLogger (global logger)
  - create_trajectory(agent_name, session_id) → AgentTrajectory
  - get_session_trajectories(session_id) → List[AgentTrajectory]

- AgentTrajectory
  - observe(observation)    # OBSERVATION step
  - reflect(reflection)     # REFLECTION step
  - reason(reasoning)       # REASONING step
  - act(action)             # ACTION step
  - result(result)          # RESULT step
  - error(error_msg)        # ERROR step
  - complete(final_result)
  - to_dict() → JSON-serializable dict
```

### Agent Flow
```
User Input → Orchestrator
  ├─> 1. ExtractionAgent (has trajectory!) ✅
  ├─> 2. RelationExpertAgent (needs trajectory) ❌
  ├─> 3. StorageAgent (needs trajectory) ❌
  ├─> 4. GraphAgent (needs trajectory) ❌
  └─> Collect ALL trajectories → Return to UI
```

## Implementation Steps

### STEP 1: Modify Orchestrator to Collect Trajectories

**File**: `src/agents/adk/orchestrator.py`

**Changes needed**:
1. Import TrajectoryLogger and uuid
2. Generate session_id for each request
3. Pass session_id to all agents
4. Collect trajectories at end using `TrajectoryLogger.get_session_trajectories(session_id)`
5. Return trajectories in result dict

**Code changes**:
```python
# At top of file
import uuid
from src.agents.adk.utils.agent_trajectory import TrajectoryLogger

# In __init__
def __init__(self, llm_provider: str = "ollama/llama3"):
    # existing code...
    self.llm_provider = llm_provider  # Store for passing to agents

# In _process_text_async (around line 49)
async def _process_text_async(self, text: str) -> dict:
    # Generate session ID for this request
    session_id = str(uuid.uuid4())
    TrajectoryLogger.start_session(session_id)

    result = {
        "success": False,
        "steps": [],
        "session_id": session_id  # NEW: Include session ID
    }

    # Step 1: Extract (pass session_id)
    extraction = ExtractionAgent(
        model_id=self.llm_provider,
        session_id=session_id  # NEW: Pass session_id
    ).extract(text)

    # ... other agents need session_id too ...

    # FINAL STEP: Collect all trajectories
    trajectories = TrajectoryLogger.get_session_trajectories(session_id)
    result["agent_trajectories"] = [t.to_dict() for t in trajectories]

    return result
```

### STEP 2: Update All Agents to Accept session_id

**Files to modify**:
- `src/agents/adk/relation_expert_agent.py`
- `src/agents/adk/storage_agent.py`
- `src/agents/adk/graph_agent.py`

**Pattern** (example for RelationExpertAgent):
```python
class RelationExpertAgent:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())

    async def process(self, extraction: dict) -> Result:
        # Create trajectory
        trajectory = TrajectoryLogger.create_trajectory(
            "RelationExpertAgent",
            self.session_id
        )

        trajectory.observe(f"Received {len(extraction['persons'])} persons")
        trajectory.reason("Planning duplicate detection strategy")
        trajectory.act("Detecting duplicates using fuzzy matching")
        # ... rest of logic ...
        trajectory.result(f"Found {len(merges)} potential duplicates")
        trajectory.complete({"success": True, "merges": merges})
```

### STEP 3: Create UI Component for Agent Trajectories

**File**: Create new `src/ui/components/agent_trajectory_view.py`

**Component features**:
- Timeline view with vertical line
- Expandable sections per agent
- Color-coded step types:
  - 🔵 OBSERVATION (blue)
  - 🟡 REFLECTION (yellow)
  - 🟣 REASONING (purple)
  - 🟢 ACTION (green)
  - ✅ RESULT (green checkmark)
  - ❌ ERROR (red)
- JSON syntax highlighting for metadata
- Duration display
- Agent handoff visualization

**Pseudo-code**:
```python
from nicegui import ui
import json

class AgentTrajectoryView:
    def __init__(self, trajectories: list):
        self.trajectories = trajectories

    def render(self):
        """Render all agent trajectories with ReAct pattern."""
        with ui.card().classes("w-full p-4 bg-gray-50"):
            ui.label("🔍 Agent Execution Trajectory").classes(
                "text-xl font-bold text-gray-800 mb-4"
            )

            for traj in self.trajectories:
                self._render_agent_trajectory(traj)

    def _render_agent_trajectory(self, traj: dict):
        """Render single agent's trajectory."""
        agent_name = traj['agent_name']
        duration = traj.get('duration_ms', 0)

        with ui.expansion(
            f"🤖 {agent_name} ({duration}ms)",
            icon="psychology"
        ).classes("w-full mb-2 border-l-4 border-blue-500"):
            # Timeline container
            with ui.column().classes("w-full pl-4 border-l-2 border-gray-300"):
                for step in traj['steps']:
                    self._render_step(step)

    def _render_step(self, step: dict):
        """Render individual trajectory step with ReAct pattern."""
        step_type = step['step_type']
        content = step['content']
        metadata = step.get('metadata', {})

        # Color and icon based on step type
        colors = {
            'observation': 'bg-blue-50 border-blue-400',
            'reflection': 'bg-yellow-50 border-yellow-400',
            'reasoning': 'bg-purple-50 border-purple-400',
            'action': 'bg-green-50 border-green-400',
            'result': 'bg-green-100 border-green-500',
            'error': 'bg-red-50 border-red-400',
        }

        icons = {
            'observation': '👁️',
            'reflection': '💭',
            'reasoning': '🧠',
            'action': '⚡',
            'result': '✅',
            'error': '❌',
        }

        color = colors.get(step_type, 'bg-gray-50 border-gray-400')
        icon = icons.get(step_type, '•')

        with ui.card().classes(f"w-full p-3 mb-2 {color} border-l-4"):
            # Step header
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(icon).classes("text-lg")
                ui.label(step_type.upper()).classes(
                    "font-bold text-xs text-gray-600"
                )

            # Step content
            ui.label(content).classes("text-sm text-gray-800 mt-1")

            # Metadata (if present)
            if metadata:
                with ui.expansion(
                    "View metadata",
                    icon="data_object"
                ).classes("mt-2"):
                    ui.code(
                        json.dumps(metadata, indent=2)
                    ).classes("text-xs")
```

### STEP 4: Integrate Trajectory View in PersonDetailView

**File**: `src/ui/person_detail_view.py`

**Changes** (in `_process_text_update` and `_process_audio_update`):
```python
# Replace current "detailed_reasoning" card with:
agent_trajectories = result.get("agent_trajectories", [])
if agent_trajectories:
    from src.ui.components.agent_trajectory_view import AgentTrajectoryView
    trajectory_view = AgentTrajectoryView(agent_trajectories)
    trajectory_view.render()
```

### STEP 5: Integrate Trajectory View in MainApp

**File**: `src/ui/main_app.py`

**Changes** (in TEXT INPUT and Recording result display):
```python
# Around line 709-717, replace detailed_reasoning with:
agent_trajectories = result.get("agent_trajectories", [])
if agent_trajectories:
    from src.ui.components.agent_trajectory_view import AgentTrajectoryView
    trajectory_view = AgentTrajectoryView(agent_trajectories)
    trajectory_view.render()
```

## Testing Plan

1. **Unit Test**: Verify trajectory collection
   ```python
   # Test that orchestrator collects trajectories
   orchestrator = FamilyOrchestrator()
   result = orchestrator.process_text("John is married to Mary")
   assert "agent_trajectories" in result
   assert len(result["agent_trajectories"]) >= 1  # At least ExtractionAgent
   ```

2. **Integration Test**: Verify UI displays trajectories
   - Run UI server
   - Enter text in Edit Person page
   - Verify agent trajectory component renders
   - Check that all step types are color-coded correctly
   - Verify JSON metadata is expandable

3. **Visual Inspection**:
   - Timeline should have vertical line connecting steps
   - Each agent should be in separate expandable section
   - Step types should have distinct colors and icons
   - Metadata should be syntax-highlighted JSON

## Success Criteria

✅ All agents create and log trajectories
✅ Orchestrator collects all trajectories using TrajectoryLogger
✅ MCP API passes trajectories through to UI
✅ UI renders trajectories with:
   - Proper ReAct pattern visualization
   - Color-coded step types
   - Expandable metadata
   - Timeline visualization
   - Agent handoff clarity

## Reference Documentation

- Google ADK Agent Trajectories: https://google-adk-docs (pattern reference)
- ReAct Pattern: Reasoning → Acting → Observing cycle
- NiceGUI Documentation: https://nicegui.io/documentation
