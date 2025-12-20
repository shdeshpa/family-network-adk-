"""
Agent Trajectory View Component - ReAct Pattern Visualization.

Displays agent execution trajectories with color-coded steps, expandable metadata,
and timeline visualization for debugging and transparency.

Author: Shrinivas Deshpande
Date: December 19, 2025
"""

from nicegui import ui
import json
from typing import List, Dict, Any


class AgentTrajectoryView:
    """Component for rendering agent execution trajectories with ReAct pattern."""

    # Step type configuration
    STEP_CONFIGS = {
        'observation': {
            'icon': '👁️',
            'color': 'bg-blue-50 border-blue-400',
            'label_color': 'text-blue-700',
            'label': 'OBSERVATION'
        },
        'reflection': {
            'icon': '💭',
            'color': 'bg-yellow-50 border-yellow-400',
            'label_color': 'text-yellow-700',
            'label': 'REFLECTION'
        },
        'reasoning': {
            'icon': '🧠',
            'color': 'bg-purple-50 border-purple-400',
            'label_color': 'text-purple-700',
            'label': 'REASONING'
        },
        'action': {
            'icon': '⚡',
            'color': 'bg-green-50 border-green-400',
            'label_color': 'text-green-700',
            'label': 'ACTION'
        },
        'result': {
            'icon': '✅',
            'color': 'bg-green-100 border-green-500',
            'label_color': 'text-green-800',
            'label': 'RESULT'
        },
        'error': {
            'icon': '❌',
            'color': 'bg-red-50 border-red-400',
            'label_color': 'text-red-700',
            'label': 'ERROR'
        },
    }

    def __init__(self, trajectories: List[Dict[str, Any]]):
        """
        Initialize trajectory view.

        Args:
            trajectories: List of trajectory dicts from TrajectoryLogger.to_dict()
        """
        self.trajectories = trajectories or []

    def render(self):
        """Render all agent trajectories with ReAct pattern."""
        if not self.trajectories:
            return

        with ui.card().classes("w-full p-4 mt-4 bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-300 shadow-lg"):
            # Header
            with ui.row().classes("w-full items-center gap-3 mb-4"):
                ui.label("🔍").classes("text-3xl")
                ui.label("Agent Execution Trajectory").classes(
                    "text-xl font-bold text-gray-800"
                )
                ui.label(f"({len(self.trajectories)} agents)").classes(
                    "text-sm text-gray-600"
                )

            # Render each agent's trajectory
            for idx, traj in enumerate(self.trajectories):
                self._render_agent_trajectory(traj, idx)

    def _render_agent_trajectory(self, traj: Dict[str, Any], index: int):
        """Render single agent's trajectory with timeline."""
        agent_name = traj.get('agent_name', f'Agent {index + 1}')
        duration = traj.get('duration_ms')
        success = traj.get('success', True)
        steps = traj.get('steps', [])

        # Agent header color
        header_color = 'bg-green-100' if success else 'bg-red-100'
        border_color = 'border-green-500' if success else 'border-red-500'
        status_icon = '✅' if success else '❌'

        with ui.expansion(
            f"{status_icon} {agent_name}",
            icon="psychology"
        ).classes(f"w-full mb-3 {header_color} border-l-4 {border_color} shadow"):
            # Agent metadata
            with ui.row().classes("w-full gap-4 mb-2 text-sm text-gray-600"):
                if duration is not None:
                    ui.label(f"⏱️ Duration: {duration}ms").classes("font-mono")
                ui.label(f"📊 Steps: {len(steps)}")
                if not success and traj.get('error_message'):
                    ui.label(f"Error: {traj['error_message']}").classes("text-red-600 font-bold")

            # Timeline container with left border
            with ui.column().classes("w-full pl-6 border-l-4 border-gray-300 ml-2"):
                # Render each step
                for step_idx, step in enumerate(steps):
                    self._render_step(step, step_idx, len(steps))

                # Final result if present
                if traj.get('final_result'):
                    self._render_final_result(traj['final_result'])

    def _render_step(self, step: Dict[str, Any], index: int, total: int):
        """Render individual trajectory step with ReAct pattern."""
        step_type = step.get('step_type', 'observation')
        content = step.get('content', '')
        metadata = step.get('metadata', {})
        timestamp = step.get('timestamp', '')

        # Get step configuration
        config = self.STEP_CONFIGS.get(step_type, self.STEP_CONFIGS['observation'])

        with ui.card().classes(f"w-full p-3 mb-2 {config['color']} border-l-4"):
            # Step header
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(config['icon']).classes("text-lg")
                ui.label(config['label']).classes(
                    f"font-bold text-xs {config['label_color']}"
                )
                if timestamp:
                    # Extract just the time portion
                    time_str = timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp
                    ui.label(f"({time_str})").classes("text-xs text-gray-500 font-mono")

            # Step content
            ui.label(content).classes("text-sm text-gray-800 mt-1 whitespace-pre-wrap")

            # Metadata (if present)
            if metadata:
                with ui.expansion(
                    f"View metadata ({len(metadata)} fields)",
                    icon="data_object"
                ).classes("mt-2 w-full"):
                    # Format metadata as JSON
                    with ui.card().classes("w-full p-2 bg-gray-800"):
                        ui.code(
                            json.dumps(metadata, indent=2)
                        ).classes("text-xs text-green-400")

    def _render_final_result(self, final_result: Dict[str, Any]):
        """Render final result of agent execution."""
        with ui.card().classes("w-full p-4 mt-3 bg-gray-100 border-2 border-gray-400"):
            ui.label("🎯 Final Result").classes("font-bold text-sm text-gray-700 mb-2")
            with ui.card().classes("w-full p-2 bg-gray-800"):
                ui.code(
                    json.dumps(final_result, indent=2)
                ).classes("text-xs text-blue-300")


def render_agent_trajectories(trajectories: List[Dict[str, Any]]):
    """
    Convenience function to render agent trajectories.

    Usage:
        from src.ui.components.agent_trajectory_view import render_agent_trajectories

        # In your UI code:
        agent_trajectories = result.get("agent_trajectories", [])
        if agent_trajectories:
            render_agent_trajectories(agent_trajectories)

    Args:
        trajectories: List of trajectory dicts from orchestrator result
    """
    view = AgentTrajectoryView(trajectories)
    view.render()
