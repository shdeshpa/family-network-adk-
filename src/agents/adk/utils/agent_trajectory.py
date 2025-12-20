"""
Agent Trajectory Logger - ReAct Pattern Implementation.

Logs agent reasoning (Reflection), planning (Reasoning), and actions (Act)
for debugging and transparency.

Author: Shrinivas Deshpande
Date: December 19, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class StepType(Enum):
    """Types of agent trajectory steps."""
    OBSERVATION = "observation"  # What the agent observes
    REFLECTION = "reflection"    # Agent's thought about observation
    REASONING = "reasoning"      # Agent's plan/reasoning
    ACTION = "action"            # Agent's action
    RESULT = "result"            # Result of action
    ERROR = "error"              # Error encountered


@dataclass
class TrajectoryStep:
    """Single step in agent trajectory."""
    step_type: StepType
    agent_name: str
    timestamp: datetime
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_type": self.step_type.value,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "metadata": self.metadata
        }


@dataclass
class AgentTrajectory:
    """Complete trajectory for an agent execution."""
    session_id: str
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    steps: List[TrajectoryStep] = field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None

    def add_step(self, step_type: StepType, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a step to the trajectory."""
        step = TrajectoryStep(
            step_type=step_type,
            agent_name=self.agent_name,
            timestamp=datetime.now(),
            content=content,
            metadata=metadata or {}
        )
        self.steps.append(step)

    def observe(self, observation: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an observation."""
        self.add_step(StepType.OBSERVATION, observation, metadata)

    def reflect(self, reflection: str, metadata: Optional[Dict[str, Any]] = None):
        """Record a reflection/thought."""
        self.add_step(StepType.REFLECTION, reflection, metadata)

    def reason(self, reasoning: str, metadata: Optional[Dict[str, Any]] = None):
        """Record reasoning/planning."""
        self.add_step(StepType.REASONING, reasoning, metadata)

    def act(self, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an action."""
        self.add_step(StepType.ACTION, action, metadata)

    def result(self, result: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an action result."""
        self.add_step(StepType.RESULT, result, metadata)

    def error(self, error_msg: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an error."""
        self.success = False
        self.error_message = error_msg
        self.add_step(StepType.ERROR, error_msg, metadata)

    def complete(self, final_result: Optional[Dict[str, Any]] = None):
        """Mark trajectory as complete."""
        self.end_time = datetime.now()
        self.final_result = final_result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "steps": [step.to_dict() for step in self.steps],
            "final_result": self.final_result,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": int((self.end_time - self.start_time).total_seconds() * 1000) if self.end_time else None
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class TrajectoryLogger:
    """Global trajectory logger for all agents."""

    _trajectories: Dict[str, List[AgentTrajectory]] = {}
    _current_session: Optional[str] = None

    @classmethod
    def start_session(cls, session_id: str):
        """Start a new logging session."""
        cls._current_session = session_id
        if session_id not in cls._trajectories:
            cls._trajectories[session_id] = []

    @classmethod
    def create_trajectory(cls, agent_name: str, session_id: Optional[str] = None) -> AgentTrajectory:
        """Create a new trajectory for an agent."""
        session_id = session_id or cls._current_session or "default"
        if session_id not in cls._trajectories:
            cls._trajectories[session_id] = []

        trajectory = AgentTrajectory(
            session_id=session_id,
            agent_name=agent_name,
            start_time=datetime.now()
        )
        cls._trajectories[session_id].append(trajectory)
        return trajectory

    @classmethod
    def get_session_trajectories(cls, session_id: str) -> List[AgentTrajectory]:
        """Get all trajectories for a session."""
        return cls._trajectories.get(session_id, [])

    @classmethod
    def get_latest_trajectory(cls, session_id: Optional[str] = None) -> Optional[AgentTrajectory]:
        """Get the most recent trajectory."""
        session_id = session_id or cls._current_session or "default"
        trajectories = cls._trajectories.get(session_id, [])
        return trajectories[-1] if trajectories else None

    @classmethod
    def clear_session(cls, session_id: str):
        """Clear all trajectories for a session."""
        if session_id in cls._trajectories:
            del cls._trajectories[session_id]

    @classmethod
    def get_all_sessions(cls) -> List[str]:
        """Get all session IDs."""
        return list(cls._trajectories.keys())

    @classmethod
    def to_dict(cls, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert trajectories to dictionary."""
        if session_id:
            return {
                "session_id": session_id,
                "trajectories": [t.to_dict() for t in cls._trajectories.get(session_id, [])]
            }
        else:
            return {
                session_id: [t.to_dict() for t in trajectories]
                for session_id, trajectories in cls._trajectories.items()
            }
