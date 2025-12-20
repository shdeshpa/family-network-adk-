"""Person Detail View - Single person editing with relationships, donations, and activities."""

from nicegui import ui
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.models_v2 import PersonProfileV2
from src.models import Person
from src.ui.audio_recorder import AudioRecorderUI
from src.mcp.input_client import InputMCPClient
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path
import pytz
import asyncio


class PersonDetailView:
    """View for editing a single person with tabs for relationships, donations, and activities."""

    def __init__(
        self,
        person_id: int,
        on_back: Optional[Callable] = None,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize person detail view.

        Args:
            person_id: ID of person to view/edit
            on_back: Callback when user clicks back/cancel
            on_save: Callback after successful save
        """
        self.person_id = person_id
        self.on_back = on_back
        self.on_save = on_save

        # Initialize stores
        self.store = CRMStoreV2()
        self.registry = FamilyRegistry()
        self.person_store = PersonStore()
        self.family_graph = FamilyGraph()

        # Initialize MCP client and recordings directory
        self.mcp_client = InputMCPClient(base_url="http://localhost:8003")
        self.recordings_dir = Path("data/recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Load person
        self.person = self.store.get_person(person_id)
        if not self.person:
            raise ValueError(f"Person with ID {person_id} not found")

        # UI components (will be initialized in render)
        self.first_name_input = None
        self.last_name_input = None
        self.gender_select = None
        self.birth_year_input = None
        self.occupation_input = None
        self.phone_input = None
        self.email_input = None
        self.city_input = None
        self.state_input = None
        self.country_input = None
        self.gothra_input = None
        self.nakshatra_input = None
        self.religious_interests_input = None
        self.spiritual_interests_input = None
        self.social_interests_input = None
        self.hobbies_input = None
        self.notes_input = None

    def render(self):
        """Render the person detail view."""
        with ui.column().classes("w-full h-full p-4"):
            # Header with close button
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label(f"✏️ Edit: {self.person.full_name}").classes("text-2xl font-bold")

                # Action buttons in header
                with ui.row().classes("gap-2"):
                    ui.button("💾 Save Changes", on_click=self._save_changes).props("color=primary")
                    if self.on_back:
                        ui.button(icon="close", on_click=self.on_back).props("flat").tooltip("Close")

            # Main content area with person details and tabs
            with ui.column().classes("w-full"):
                # Quick Update section - positioned right after header, before detailed form
                self._render_quick_update_section()

                # Person details section (structured form fields)
                self._render_person_details()

                # Tabs for relationships, donations, activities
                with ui.tabs().classes("w-full mt-6") as tabs:
                    relationships_tab = ui.tab("👨‍👩‍👧‍👦 Relationships")
                    donations_tab = ui.tab("💰 Donations")
                    activities_tab = ui.tab("🎯 Volunteer Activities")

                with ui.tab_panels(tabs, value=relationships_tab).classes("w-full"):
                    with ui.tab_panel(relationships_tab):
                        self._render_relationships_tab()

                    with ui.tab_panel(donations_tab):
                        self._render_donations_tab()

                    with ui.tab_panel(activities_tab):
                        self._render_activities_tab()

    def _render_person_details(self):
        """Render editable person details section."""
        with ui.card().classes("w-full p-6 mb-4"):
            ui.label("Personal Information").classes("text-xl font-bold mb-4")

            with ui.column().classes("w-full gap-4"):
                # Basic Information
                ui.label("Basic Details").classes("font-bold text-sm text-gray-700 uppercase")
                with ui.row().classes("w-full gap-2"):
                    self.first_name_input = ui.input(
                        "First Name *",
                        value=self.person.first_name
                    ).props("outlined dense").classes("flex-1")

                    self.last_name_input = ui.input(
                        "Last Name *",
                        value=self.person.last_name
                    ).props("outlined dense").classes("flex-1")

                with ui.row().classes("w-full gap-2"):
                    self.gender_select = ui.select(
                        label="Gender",
                        options={"M": "Male", "F": "Female", "O": "Other", "": "Unspecified"},
                        value=self.person.gender or ""
                    ).props("outlined dense").classes("flex-1")

                    self.birth_year_input = ui.number(
                        "Birth Year",
                        value=self.person.birth_year,
                        format="%.0f"
                    ).props("outlined dense").classes("flex-1")

                self.occupation_input = ui.input(
                    "Occupation",
                    value=self.person.occupation or ""
                ).props("outlined dense").classes("w-full")

                # Contact Information
                ui.label("Contact Information").classes("font-bold text-sm text-gray-700 uppercase mt-4")
                with ui.row().classes("w-full gap-2"):
                    self.phone_input = ui.input(
                        "Phone",
                        value=self.person.phone or ""
                    ).props("outlined dense").classes("flex-1")

                    self.email_input = ui.input(
                        "Email",
                        value=self.person.email or ""
                    ).props("outlined dense type=email").classes("flex-1")

                # Location
                ui.label("Location").classes("font-bold text-sm text-gray-700 uppercase mt-4")
                with ui.row().classes("w-full gap-2"):
                    self.city_input = ui.input(
                        "City",
                        value=self.person.city or ""
                    ).props("outlined dense").classes("flex-1")

                    self.state_input = ui.input(
                        "State",
                        value=self.person.state or ""
                    ).props("outlined dense").classes("flex-1")

                self.country_input = ui.input(
                    "Country",
                    value=self.person.country or ""
                ).props("outlined dense").classes("w-full")

                # Cultural Information
                ui.label("Cultural Information").classes("font-bold text-sm text-gray-700 uppercase mt-4")
                with ui.row().classes("w-full gap-2"):
                    self.gothra_input = ui.input(
                        "Gothra",
                        value=self.person.gothra or ""
                    ).props("outlined dense").classes("flex-1")

                    self.nakshatra_input = ui.input(
                        "Nakshatra",
                        value=self.person.nakshatra or ""
                    ).props("outlined dense").classes("flex-1")

                # Interests & Activities
                ui.label("Interests & Activities").classes("font-bold text-sm text-gray-700 uppercase mt-4")
                self.religious_interests_input = ui.textarea(
                    "Religious Interests",
                    value=self.person.religious_interests or ""
                ).props("outlined rows=2").classes("w-full")

                self.spiritual_interests_input = ui.textarea(
                    "Spiritual Interests",
                    value=self.person.spiritual_interests or ""
                ).props("outlined rows=2").classes("w-full")

                self.social_interests_input = ui.textarea(
                    "Social Interests",
                    value=self.person.social_interests or ""
                ).props("outlined rows=2").classes("w-full")

                self.hobbies_input = ui.textarea(
                    "Hobbies",
                    value=self.person.hobbies or ""
                ).props("outlined rows=2").classes("w-full")

                # Notes
                ui.label("Notes").classes("font-bold text-sm text-gray-700 uppercase mt-4")
                self.notes_input = ui.textarea(
                    "Additional Notes",
                    value=self.person.notes or ""
                ).props("outlined rows=3").classes("w-full")

    def _render_relationships_tab(self):
        """Render relationships tab content."""
        with ui.column().classes("w-full p-4"):
            ui.label("👨‍👩‍👧‍👦 Family Relationships").classes("text-xl font-bold mb-4")

            # Get relationships from GraphLite
            graphlite_persons = self.person_store.find_by_name(self.person.full_name)

            if not graphlite_persons:
                with ui.card().classes("p-6 bg-gray-50"):
                    ui.label("No relationships found in family graph.").classes("text-gray-500")
                    ui.label("Relationships are built when processing family data through the extraction pipeline.").classes("text-sm text-gray-400 mt-2")
                return

            graphlite_person = graphlite_persons[0]
            relationships = self.family_graph.get_person_relationships(graphlite_person.id)

            if not relationships:
                with ui.card().classes("p-6 bg-gray-50"):
                    ui.label("No relationships recorded yet.").classes("text-gray-500")
                return

            # Display relationships grouped by type
            rel_groups = {}
            for rel in relationships:
                rel_type = rel.relationship_type
                if rel_type not in rel_groups:
                    rel_groups[rel_type] = []
                rel_groups[rel_type].append(rel)

            for rel_type, rels in rel_groups.items():
                with ui.card().classes("p-4 mb-3"):
                    ui.label(f"{rel_type.upper()}").classes("font-bold text-sm text-gray-700 mb-2")
                    for rel in rels:
                        # Get related person details
                        related_person = self.person_store.get_person(rel.person_b_id)
                        if related_person:
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("person").classes("text-gray-500")
                                ui.label(related_person.name).classes("text-base")
                                if related_person.location:
                                    ui.label(f"({related_person.location})").classes("text-sm text-gray-500")

    def _render_donations_tab(self):
        """Render donations tab content."""
        with ui.column().classes("w-full p-4"):
            ui.label("💰 Donations History").classes("text-xl font-bold mb-4")

            with ui.card().classes("p-6 bg-blue-50"):
                ui.label("Coming Soon").classes("text-lg font-bold")
                ui.label("Donation tracking will be added in a future update.").classes("text-sm text-gray-600 mt-2")
                ui.label("Features planned:").classes("text-sm font-bold text-gray-700 mt-4")
                ui.label("  • Track monetary donations").classes("text-sm text-gray-600 ml-4")
                ui.label("  • Record item donations").classes("text-sm text-gray-600 ml-4")
                ui.label("  • View donation history").classes("text-sm text-gray-600 ml-4")
                ui.label("  • Generate tax receipts").classes("text-sm text-gray-600 ml-4")

    def _render_activities_tab(self):
        """Render volunteer activities tab content."""
        with ui.column().classes("w-full p-4"):
            ui.label("🎯 Volunteer Activities").classes("text-xl font-bold mb-4")

            with ui.card().classes("p-6 bg-green-50"):
                ui.label("Coming Soon").classes("text-lg font-bold")
                ui.label("Volunteer activity tracking will be added in a future update.").classes("text-sm text-gray-600 mt-2")
                ui.label("Features planned:").classes("text-sm font-bold text-gray-700 mt-4")
                ui.label("  • Log volunteer hours").classes("text-sm text-gray-600 ml-4")
                ui.label("  • Track event participation").classes("text-sm text-gray-600 ml-4")
                ui.label("  • Record skills and expertise").classes("text-sm text-gray-600 ml-4")
                ui.label("  • Generate volunteer reports").classes("text-sm text-gray-600 ml-4")

    def _render_quick_update_section(self):
        """Render compact quick update section with text and audio input."""
        with ui.card().classes("w-full p-4 mb-4 bg-blue-50"):
            with ui.row().classes("w-full items-center gap-4 mb-3"):
                ui.label("✨ Quick Update").classes("text-lg font-bold")
                ui.label(f"Add unstructured information about {self.person.full_name}").classes("text-sm text-gray-600")

            # Text and audio inputs side by side
            with ui.row().classes("w-full gap-4"):
                # Text input column
                with ui.column().classes("flex-1"):
                    ui.label("📝 Type or 🎤 Speak").classes("font-bold text-sm mb-2")
                    self.update_text_input = ui.textarea(
                        placeholder="Type any information... (e.g., 'Lives in Mumbai', 'Phone: +91-98-1234-5678')"
                    ).classes("w-full").props("rows=3 outlined dense")

                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("🚀 Process Text", on_click=self._process_text_update).props("color=primary size=sm")
                        ui.button("Clear", on_click=lambda: self.update_text_input.set_value("")).props("flat size=sm")

                # Audio input column
                with ui.column().classes("flex-1"):
                    ui.label("🎤 Audio Recording").classes("font-bold text-sm mb-2")
                    ui.label("Supports: English, Marathi, Telugu, Hindi").classes("text-xs text-gray-500 mb-1")
                    self.update_recorder = AudioRecorderUI(on_audio_received=self._process_audio_update)

            # Compact results section
            with ui.row().classes("w-full mt-3"):
                self.update_results = ui.column().classes("w-full")
                with self.update_results:
                    ui.label("💡 Enter text or record audio for unstructured updates").classes("text-sm text-gray-500 italic")

    async def _process_text_update(self):
        """Process text input through MCP with person context."""
        text = self.update_text_input.value
        if not text or not text.strip():
            ui.notify("Please enter some text", type="warning")
            return

        self.update_results.clear()
        with self.update_results:
            ui.label("Processing...").classes("text-blue-600")

        try:
            # Call MCP API with context (using async context manager)
            async with InputMCPClient(base_url=self.mcp_client.base_url) as client:
                result = await client.process_text_input(
                    text=text,
                    context_person_id=self.person_id,
                    context_person_name=self.person.full_name
                )

            self.update_results.clear()
            with self.update_results:
                if result.get("success"):
                    ui.label("✅ Successfully updated!").classes("text-green-600 font-bold")

                    # Show summary if available
                    if result.get("summary"):
                        ui.label(result["summary"]).classes("text-sm mt-2")

                    # 🔍 AGENT TRAJECTORIES - Full ReAct pattern display
                    agent_trajectories = result.get("agent_trajectories", [])
                    if agent_trajectories:
                        from src.ui.components.agent_trajectory_view import render_agent_trajectories
                        render_agent_trajectories(agent_trajectories)

                    # Reload person data
                    self.person = self.store.get_person(self.person_id)
                    ui.notify("Person information updated via agents", type="positive")

                    # Clear input
                    self.update_text_input.set_value("")
                else:
                    error_msg = result.get("error", "Unknown error")
                    ui.label(f"❌ Error: {error_msg}").classes("text-red-600")

        except Exception as e:
            self.update_results.clear()
            with self.update_results:
                ui.label(f"❌ Error: {str(e)}").classes("text-red-600")
            ui.notify(f"Error processing text: {str(e)}", type="negative")

    async def _process_audio_update(self, audio_bytes: bytes):
        """Process audio input through MCP with person context."""
        self.update_results.clear()
        with self.update_results:
            ui.label("Processing audio...").classes("text-blue-600")

        try:
            # Save audio file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = self.recordings_dir / f"update_{self.person_id}_{timestamp}.webm"
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            # Call MCP API with context (using async context manager)
            async with InputMCPClient(base_url=self.mcp_client.base_url) as client:
                result = await client.process_audio_input(
                    audio_file_path=str(audio_path),
                    context_person_id=self.person_id,
                    context_person_name=self.person.full_name
                )

            self.update_results.clear()
            with self.update_results:
                if result.get("success"):
                    ui.label("✅ Successfully updated!").classes("text-green-600 font-bold")

                    # Show transcription
                    if result.get("transcription"):
                        trans = result["transcription"]
                        if trans.get("text"):
                            with ui.expansion("📝 Transcription", icon="mic").classes("w-full mt-2"):
                                ui.label(trans["text"]).classes("text-sm")

                    # Show summary
                    if result.get("summary"):
                        ui.label(result["summary"]).classes("text-sm mt-2")

                    # 🔍 AGENT TRAJECTORIES - Full ReAct pattern display
                    agent_trajectories = result.get("agent_trajectories", [])
                    if agent_trajectories:
                        from src.ui.components.agent_trajectory_view import render_agent_trajectories
                        render_agent_trajectories(agent_trajectories)

                    # Reload person data
                    self.person = self.store.get_person(self.person_id)
                    ui.notify("Person information updated via agents", type="positive")
                else:
                    error_msg = result.get("error", "Unknown error")
                    ui.label(f"❌ Error: {error_msg}").classes("text-red-600")

        except Exception as e:
            self.update_results.clear()
            with self.update_results:
                ui.label(f"❌ Error: {str(e)}").classes("text-red-600")
            ui.notify(f"Error processing audio: {str(e)}", type="negative")

    def _save_changes(self):
        """Save the edited person details."""
        # Validation
        if not self.first_name_input.value or not self.last_name_input.value:
            ui.notify("❌ First name and last name are required", type="negative")
            return

        try:
            # Step 1: Update CRM
            success = self.store.update_person(
                self.person.id,
                first_name=self.first_name_input.value,
                last_name=self.last_name_input.value,
                gender=self.gender_select.value if self.gender_select.value else None,
                birth_year=int(self.birth_year_input.value) if self.birth_year_input.value else None,
                occupation=self.occupation_input.value,
                phone=self.phone_input.value,
                email=self.email_input.value,
                city=self.city_input.value,
                state=self.state_input.value,
                country=self.country_input.value,
                gothra=self.gothra_input.value,
                nakshatra=self.nakshatra_input.value,
                religious_interests=self.religious_interests_input.value,
                spiritual_interests=self.spiritual_interests_input.value,
                social_interests=self.social_interests_input.value,
                hobbies=self.hobbies_input.value,
                notes=self.notes_input.value
            )

            if success:
                # Step 2: Sync with GraphLite
                graphlite_updated = False
                old_name = self.person.full_name
                new_name = f"{self.first_name_input.value} {self.last_name_input.value}"

                # Find person in GraphLite by old name
                graphlite_persons = self.person_store.find_by_name(old_name)
                if graphlite_persons:
                    # Update the first match
                    gp = graphlite_persons[0]

                    # Build interests list
                    interests_list = []
                    if self.hobbies_input.value:
                        interests_list.extend([h.strip() for h in self.hobbies_input.value.split(',') if h.strip()])
                    if self.religious_interests_input.value:
                        interests_list.extend([r.strip() for r in self.religious_interests_input.value.split(',') if r.strip()])

                    # Update GraphLite person
                    gp.name = new_name
                    gp.location = self.city_input.value or ""
                    gp.gender = self.gender_select.value if self.gender_select.value else None
                    gp.interests = interests_list[:10]  # Limit to 10

                    # Save changes to GraphLite
                    self.person_store.update_person(gp)
                    graphlite_updated = True

                if graphlite_updated:
                    ui.notify(f"✅ Updated {new_name} in CRM and GraphLite", type="positive")
                else:
                    ui.notify(f"✅ Updated {new_name} in CRM (not found in GraphLite)", type="positive")

                # Reload person data
                self.person = self.store.get_person(self.person.id)

                # Call on_save callback if provided
                if self.on_save:
                    self.on_save()
            else:
                ui.notify("❌ Failed to update person", type="negative")
        except Exception as e:
            ui.notify(f"❌ Error: {str(e)}", type="negative")
