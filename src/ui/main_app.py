"""
Main NiceGUI application with ADK agents.

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from pathlib import Path
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from nicegui import ui

from src.ui.audio_recorder import AudioRecorderUI
from src.ui.d3_tree_view import D3TreeView
from src.ui.crm_editor import CRMEditor
from src.ui.crm_table_view import CRMTableView
from src.ui.person_detail_view import PersonDetailView
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.graph.enhanced_crm import EnhancedCRM
from src.graph.text_history import TextHistory
from src.graph.family_registry import FamilyRegistry
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.temple_store import TempleStore
from src.graph.app_settings import AppSettings
from src.agents.adk.orchestrator import FamilyOrchestrator
from src.agents.adk.query_agent import QueryAgent
from src.mcp.input_client import InputMCPClient


executor = ThreadPoolExecutor(max_workers=2)


class FamilyNetworkApp:
    """Main application for Family Network."""

    def __init__(self):
        self.recordings_dir = Path("data/recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # MCP server URL
        self.mcp_server_url = "http://localhost:8003"

        # Legacy stores
        self.person_store = PersonStore()
        self.family_graph = FamilyGraph()
        self.crm_store = CRMStore()
        self.enhanced_crm = EnhancedCRM()
        self.text_history = TextHistory()

        # CRM V2 stores
        self.family_registry = FamilyRegistry()
        self.crm_store_v2 = CRMStoreV2()
        self.temple_store = TempleStore()
        self.app_settings = AppSettings()

        # Temple context - PRIMARY context for the entire app
        # Load saved home temple from settings
        saved_temple_id = self.app_settings.get_home_temple_id()
        self.selected_temple_id = saved_temple_id
        self.selected_temple_name = None
        if saved_temple_id:
            temple = self.temple_store.get_temple(saved_temple_id)
            if temple:
                self.selected_temple_name = temple.name

        # Lazy-load these to avoid startup crashes
        self._orchestrator = None
        self._query_agent = None

    @property
    def orchestrator(self):
        """Lazy-load orchestrator only when needed."""
        if self._orchestrator is None:
            try:
                self._orchestrator = FamilyOrchestrator(llm_provider='ollama/llama3')
            except Exception as e:
                ui.notify(f"Failed to initialize orchestrator: {str(e)}", type="negative")
                raise
        return self._orchestrator

    @property
    def query_agent(self):
        """Lazy-load query agent only when needed."""
        if self._query_agent is None:
            try:
                self._query_agent = QueryAgent(provider='ollama')
            except Exception as e:
                ui.notify(f"Failed to initialize query agent: {str(e)}", type="negative")
                raise
        return self._query_agent
    
    def setup(self):
        """Setup the main UI."""
        # Add temple background CSS with faded overlay
        ui.add_head_html('''
        <style>
            body {
                background-image: url('/static/backgrounds/temple_street.jpg');
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                background-repeat: no-repeat;
            }

            body::before {
                content: "";
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(255, 255, 255, 0.85);
                z-index: -1;
            }

            .q-page {
                background-color: transparent !important;
            }
        </style>
        ''')

        # Header with temple info
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("🏠 Family Network System").classes("text-3xl font-bold")

            # Temple info display (static text with full description)
            self.temple_display_container = ui.row().classes("ml-8")
            self._render_temple_display()

        # Tabs (TEMPLES first, then others)
        with ui.tabs().classes("w-full") as self.tabs:
            self.temples_tab = ui.tab("TEMPLES")
            self.crm_tab = ui.tab("  Devotee Information")
            self.tree_tab = ui.tab("  FAMILY TREE")
            self.chat_tab = ui.tab("  CHAT")

        # Tab panels
        with ui.tab_panels(self.tabs, value=self.temples_tab).classes("w-full"):
            with ui.tab_panel(self.temples_tab):
                self._setup_temples_tab()
            with ui.tab_panel(self.crm_tab):
                self._setup_crm_tab()
            with ui.tab_panel(self.tree_tab):
                self._setup_tree_tab()
            with ui.tab_panel(self.chat_tab):
                self._setup_chat_tab()

    def _render_temple_display(self):
        """Render the static temple display in the header."""
        self.temple_display_container.clear()
        with self.temple_display_container:
            if self.selected_temple_id:
                # Show full temple info: "Home Temple: Name, City, State"
                temple = self.temple_store.get_temple(self.selected_temple_id)
                if temple:
                    display_text = f"Home Temple: {temple.name}, {temple.city}, {temple.state}"
                    ui.label(display_text).classes("text-lg text-gray-700 font-medium")

    def _render_temple_selector(self):
        """Render the temple context selector in the header."""
        self.temple_context_container.clear()
        with self.temple_context_container:
            if self.selected_temple_id:
                # Show current temple with dropdown
                temples = self.temple_store.get_all_temples()
                temple_options = {t.id: f"{t.name} ({t.city})" for t in temples}

                ui.label("Home Temple:").classes("text-sm text-gray-600")
                ui.select(
                    options=temple_options,
                    value=self.selected_temple_id,
                    on_change=lambda e: self._change_temple(e.value)
                ).classes("w-64")
            else:
                # Show warning and select button
                ui.label("⚠️ No Home Temple Selected").classes("text-red-600 font-bold")
                ui.button("Select Temple", on_click=self._show_temple_selector_dialog).classes("bg-orange-600")

    def _change_temple(self, temple_id: int):
        """Change the selected temple."""
        temple = self.temple_store.get_temple(temple_id)
        if temple:
            self._set_home_temple(temple.id, temple.name)

    def _show_temple_selector_dialog(self):
        """Show dialog to select a temple as home temple."""
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label("Select Home Temple").classes("text-2xl font-bold mb-4")
            ui.label("Choose your primary temple context. This will filter data across all screens.").classes("text-sm text-gray-600 mb-4")

            temples = self.temple_store.get_all_temples()

            if not temples:
                ui.label("No temples found. Please add a temple first.").classes("text-gray-500 italic")
                ui.button("Go to Temples Tab", on_click=lambda: [dialog.close(), self.tabs.set_value(self.temples_tab)]).classes("bg-orange-600 mt-4")
            else:
                # Show temple list
                for temple in temples:
                    with ui.card().classes("w-full mb-2 p-3 cursor-pointer hover:bg-gray-100"):
                        with ui.row().classes("w-full items-center justify-between"):
                            with ui.column().classes("flex-1"):
                                ui.label(temple.name).classes("font-bold text-lg")
                                ui.label(f"{temple.deity} | {temple.city}, {temple.state}").classes("text-sm text-gray-600")
                            ui.button("Select as Home", on_click=lambda t=temple: self._set_home_temple(t.id, t.name, dialog)).classes("bg-orange-600 text-xs")

            ui.button("Cancel", on_click=dialog.close).classes("bg-gray-500 mt-4")

        dialog.open()

    def _set_home_temple(self, temple_id: int, temple_name: str, dialog=None):
        """Set the selected temple as home temple context."""
        self.selected_temple_id = temple_id
        self.selected_temple_name = temple_name

        # Save to settings for persistence
        self.app_settings.set_home_temple_id(temple_id)

        # Update the temple display in header
        self._render_temple_display()

        ui.notify(f"Home temple set to: {temple_name}", type="positive")

        if dialog:
            dialog.close()

    def _setup_record_tab(self):
        ui.label("Speak about your family members.").classes("mb-4 text-gray-600")
        with ui.row().classes("w-full gap-4"):
            with ui.column():
                self.recorder = AudioRecorderUI(on_audio_received=self._process_audio)
            with ui.card().classes("flex-1 p-4"):
                ui.label("Results").classes("text-lg font-bold mb-2")
                self.results_container = ui.column().classes("w-full")
                with self.results_container:
                    ui.label("No recording yet")
        ui.button("🔄 Process Last Recording", on_click=self._process_last_recording).classes("mt-4 bg-blue-500")
    
    def _setup_text_tab(self):
        """Setup text input tab with history."""
        with ui.column().classes("w-full"):
            # Input section
            ui.label("Enter text describing your family:").classes("text-lg mb-2")
            
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-1"):
                    self.text_input = ui.textarea(
                        label="Family Description",
                        placeholder="Example: My name is Ramesh from Hyderabad. My wife Priya and I have two children..."
                    ).classes("w-full").props("rows=4")
                    
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("🚀 Process", on_click=self._process_custom_text).classes("bg-green-500")
                        ui.button("🗑️ Clear", on_click=lambda: self.text_input.set_value("")).classes("bg-red-300")
                
                with ui.column().classes("flex-1"):
                    ui.label("Results").classes("font-bold mb-2")
                    self.text_results_container = ui.column().classes("w-full")
                    with self.text_results_container:
                        ui.label("Enter text and click Process").classes("text-gray-500")
            
            ui.separator().classes("my-4")
            
            # History section
            with ui.row().classes("justify-between items-center mb-2"):
                ui.label("📜 Text Input History").classes("text-lg font-bold")
                with ui.row().classes("gap-2"):
                    ui.button("🔄 Refresh", on_click=self._load_text_history).classes("text-sm bg-gray-400")
                    ui.button("🗑️ Clear All", on_click=self._clear_text_history).classes("text-sm bg-red-400")
            
            self.history_container = ui.column().classes("w-full")
            self._load_text_history()
    
    def _load_text_history(self):
        """Load and display text history."""
        self.history_container.clear()
        
        entries = self.text_history.get_all(limit=20)
        
        with self.history_container:
            if not entries:
                ui.label("No history yet").classes("text-gray-500")
                return
            
            # Table header
            with ui.row().classes("w-full bg-gray-100 p-2 font-bold text-sm gap-2"):
                ui.label("Date/Time").classes("w-40")
                ui.label("Text").classes("flex-1")
                ui.label("Status").classes("w-24")
                ui.label("Results").classes("w-32")
                ui.label("Actions").classes("w-32")
            
            # Table rows
            for entry in entries:
                status_color = {
                    "processed": "text-green-600",
                    "pending": "text-yellow-600",
                    "failed": "text-red-600"
                }.get(entry.status, "text-gray-600")
                
                # Format datetime
                dt_str = entry.created_at[:16].replace("T", " ") if entry.created_at else "-"
                
                # Truncate text
                text_preview = entry.text[:80] + "..." if len(entry.text) > 80 else entry.text
                
                with ui.row().classes("w-full p-2 text-sm gap-2 border-b hover:bg-gray-50 items-center"):
                    ui.label(dt_str).classes("w-40")
                    ui.label(text_preview).classes("flex-1 truncate")
                    ui.label(entry.status.upper()).classes(f"w-24 {status_color} font-bold")
                    ui.label(f"👥{entry.persons_found} 🔗{entry.relationships_found}").classes("w-32")
                    
                    with ui.row().classes("w-32 gap-1"):
                        ui.button(
                            "🔄", 
                            on_click=lambda eid=entry.id: self._reprocess_entry(eid)
                        ).props("flat dense").tooltip("Reprocess")
                        ui.button(
                            "📋", 
                            on_click=lambda txt=entry.text: self._copy_to_input(txt)
                        ).props("flat dense").tooltip("Copy to input")
                        ui.button(
                            "Delete", 
                            on_click=lambda eid=entry.id: self._delete_entry(eid)
                        ).props("flat dense").classes("text-red-500 text-xs").tooltip("Delete")
    
    def _copy_to_input(self, text: str):
        """Copy text to input area."""
        self.text_input.set_value(text)
        ui.notify("Copied to input", type="info")
    
    async def _reprocess_entry(self, entry_id: int):
        """Reprocess a history entry."""
        entry = self.text_history.get_entry(entry_id)
        if not entry:
            return
        
        self.text_input.set_value(entry.text)
        await self._process_custom_text()
    
    def _delete_entry(self, entry_id: int):
        """Delete a history entry."""
        self.text_history.delete_entry(entry_id)
        ui.notify("Deleted", type="info")
        self._load_text_history()
    
    def _clear_text_history(self):
        """Clear all history."""
        with ui.dialog() as dialog, ui.card():
            ui.label("Clear all history?").classes("font-bold")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close)
                def do_clear():
                    self.text_history.clear_all()
                    ui.notify("History cleared", type="positive")
                    dialog.close()
                    self._load_text_history()
                ui.button("🗑️ Clear All", on_click=do_clear).classes("bg-red-500")
        dialog.open()
    
    def _setup_tree_tab(self):
        """Setup interactive tree view."""
        with ui.row().classes("w-full justify-between items-center mb-4"):
            ui.label("🌳 Family Tree").classes("text-xl font-bold")
            ui.button("🔄 Refresh Tree", on_click=self._refresh_tree_view).classes("bg-blue-500")

        ui.label("Click on any person to add more details").classes("text-sm text-gray-600 mb-2")

        self.tree_container = ui.column().classes("w-full")
        self._render_tree_view()

        # Hidden button to trigger person detail dialog from JavaScript
        self.person_detail_trigger = ui.button("", on_click=lambda: self._show_person_detail_dialog()).style("display: none")

        # Set up JavaScript handler for node clicks using HTML instead of run_javascript
        ui.add_body_html('''
            <script>
                window.selectedPersonId = null;
                window.selectedPersonName = null;
                window.onD3NodeClick = function(personId, personName) {
                    console.log('Node clicked:', personId, personName);
                    window.selectedPersonId = personId;
                    window.selectedPersonName = personName;
                    // Trigger the hidden button to open dialog
                    document.querySelectorAll('button').forEach(btn => {
                        if (btn.textContent === '' && btn.style.display === 'none') {
                            btn.click();
                        }
                    });
                };
            </script>
        ''')
    
    def _render_tree_view(self):
        """Render the tree view using CRM V2 data."""
        if not hasattr(self, 'tree_container'):
            return
        try:
            self.tree_container.clear()
            with self.tree_container:
                tree = D3TreeView(
                    crm_store=self.crm_store_v2,
                    family_registry=self.family_registry,
                    person_store=self.person_store,
                    family_graph=self.family_graph,
                    on_view_in_crm=self._open_person_in_crm
                )
                tree.render()
        except Exception as e:
            self.tree_container.clear()
            with self.tree_container:
                ui.label(f"Error rendering tree: {str(e)}").classes("text-red-500")

    def _refresh_tree_view(self):
        """Refresh the tree view without resetting context."""
        # Use page reload to refresh data
        # Home temple context is now persisted in app_settings.json
        # so it will be automatically restored on page reload
        ui.navigate.reload()

    def _open_person_in_crm(self, person_id: int):
        """Navigate to CRM tab and open PersonDetailView for editing."""
        # Navigate to CRM tab
        self.tabs.set_value(self.crm_tab)

        # Open PersonDetailView
        person = self.crm_store_v2.get_person(person_id)
        if person:
            self._open_person_detail(person_id)
            ui.notify(f"Opening editor for {person.full_name}", type="info")
        else:
            ui.notify(f"Person with ID {person_id} not found", type="negative")

    async def _show_person_detail_dialog(self):
        """Show dialog to add details to a selected person."""
        # Get person ID and name from JavaScript
        result = await ui.run_javascript('({id: window.selectedPersonId, name: window.selectedPersonName})')

        if not result or not result.get('id'):
            ui.notify("No person selected", type="warning")
            return

        person_id = result['id']
        person_name = result['name']

        # Get person details from CRM
        person = self.crm_store_v2.get_by_id(person_id)
        if not person:
            ui.notify(f"Person with ID {person_id} not found", type="negative")
            return

        # Create dialog
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label(f"Add Details for {person_name}").classes("text-xl font-bold mb-4")

            # Show current details
            with ui.expansion("Current Details", icon="info").classes("w-full mb-4"):
                ui.label(f"Name: {person.full_name}").classes("mb-1")
                if person.gender:
                    ui.label(f"Gender: {person.gender}").classes("mb-1")
                if person.phone:
                    ui.label(f"Phone: {person.phone}").classes("mb-1")
                if person.email:
                    ui.label(f"Email: {person.email}").classes("mb-1")

            ui.label("Speak or type additional information about this person:").classes("mb-2")

            # Audio recorder
            dialog_audio_container = ui.column().classes("w-full mb-4")
            with dialog_audio_container:
                person_audio_recorder = AudioRecorderUI(
                    on_audio_received=lambda audio_bytes: self._process_person_audio(
                        audio_bytes, person_id, person_name, dialog
                    )
                )

            # Text input alternative
            ui.label("Or type details:").classes("mt-4 mb-2")
            person_text_input = ui.textarea(
                placeholder=f"Example: {person_name} loves gardening and lives in Seattle..."
            ).classes("w-full").props("rows=3")

            # Results container
            person_results = ui.column().classes("w-full mt-4")

            # Buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "💾 Submit Text",
                    on_click=lambda: self._process_person_text(
                        person_text_input.value, person_id, person_name, dialog, person_results
                    )
                ).classes("bg-blue-500")

        dialog.open()

    async def _process_person_audio(self, audio_bytes: bytes, person_id: int, person_name: str, dialog):
        """Process audio recording for a specific person."""
        try:
            ui.notify(f"Processing audio for {person_name}...", type="info")

            # Save audio file
            raw_path = self.recordings_dir / f"person_{person_id}_update.webm"
            raw_path.write_bytes(audio_bytes)

            # Use MCP client to process audio with person context
            async with InputMCPClient(self.mcp_server_url) as mcp_client:
                result = await mcp_client.process_audio_input(
                    audio_file_path=str(raw_path.absolute()),
                    context_person_id=person_id,
                    context_person_name=person_name
                )

            if result.get('success'):
                ui.notify(f"Details added for {person_name}!", type="positive")
                dialog.close()
                self._refresh_tree_view()
            else:
                error_msg = result.get('error', 'Unknown error')
                ui.notify(f"Error: {error_msg}", type="negative")

        except Exception as e:
            ui.notify(f"Error processing audio: {str(e)}", type="negative")

    async def _process_person_text(self, text: str, person_id: int, person_name: str, dialog, results_container):
        """Process text input for a specific person."""
        if not text or not text.strip():
            ui.notify("Please enter some text", type="warning")
            return

        try:
            results_container.clear()
            with results_container:
                ui.label("Processing via MCP...").classes("text-blue-500")

            # Use MCP client to process text with person context
            async with InputMCPClient(self.mcp_server_url) as mcp_client:
                result = await mcp_client.process_text_input(
                    text=text,
                    context_person_id=person_id,
                    context_person_name=person_name
                )

            results_container.clear()
            with results_container:
                if result.get('success'):
                    ui.label("✅ Details added successfully!").classes("text-green-600 font-bold")
                    ui.notify(f"Details added for {person_name}!", type="positive")
                    await asyncio.sleep(1)
                    dialog.close()
                    self._refresh_tree_view()
                else:
                    error_msg = result.get('error', 'Unknown error')
                    ui.label(f"❌ Error: {error_msg}").classes("text-red-600")

        except Exception as e:
            results_container.clear()
            with results_container:
                ui.label(f"❌ Error: {str(e)}").classes("text-red-600")
    
    def _setup_crm_tab(self):
        """Setup CRM tab with modern table view."""
        # Create container for CRM content (can switch between table view and person detail view)
        self.crm_container = ui.column().classes("w-full h-full")
        with self.crm_container:
            self._render_crm_table()

    def _render_crm_table(self):
        """Render the CRM table view."""
        # Store reference to CRM table view with edit callback
        self.crm_table = CRMTableView(on_edit_person=self._open_person_detail)
        self.crm_table.render()

    def _open_person_detail(self, person_id: int):
        """Open PersonDetailView for editing a person."""
        # Clear CRM container and show PersonDetailView
        self.crm_container.clear()
        with self.crm_container:
            person_detail = PersonDetailView(
                person_id=person_id,
                on_back=self._back_to_crm_table,
                on_save=self._on_person_saved,
                temple_id=self.selected_temple_id  # Pass temple context
            )
            person_detail.render()

    def _back_to_crm_table(self):
        """Return to CRM table view."""
        self.crm_container.clear()
        with self.crm_container:
            self._render_crm_table()

    def _on_person_saved(self):
        """Callback after person is saved - refresh the table."""
        # No need to do anything special, table will be refreshed when we go back
        pass
    
    def _setup_chat_tab(self):
        ui.label("💬 Ask about your family").classes("text-xl font-bold mb-4")
        self.chat_container = ui.column().classes("w-full h-80 overflow-auto p-4 bg-gray-50 rounded")
        with self.chat_container:
            ui.label("Ask me anything about your family!").classes("text-gray-500")
        
        with ui.row().classes("w-full gap-2 mt-4"):
            self.chat_input = ui.input(placeholder="e.g., Who lives in California?").classes("flex-1").on("keydown.enter", self._send_chat)
            ui.button("Send", on_click=self._send_chat).classes("bg-blue-500")
        
        ui.label("Try:").classes("mt-4 text-sm text-gray-600")
        with ui.row().classes("gap-2 flex-wrap"):
            for q in ["Who is in the family?", "List all members", "Who has children?"]:
                ui.button(q, on_click=lambda q=q: self._quick_question(q)).classes("text-xs bg-gray-200")
    
    async def _process_audio(self, audio_bytes: bytes):
        self._update_results("💾 Saving...", self.results_container)
        try:
            raw_path = self.recordings_dir / "latest_raw.webm"
            raw_path.write_bytes(audio_bytes)
            self._update_results("🎯 Processing via MCP...", self.results_container)

            # Use MCP client to process audio
            async with InputMCPClient(self.mcp_server_url) as mcp_client:
                result = await mcp_client.process_audio_input(
                    audio_file_path=str(raw_path.absolute())
                )

            self._display_result(result, self.results_container)
            # Don't auto-navigate - let user review results first
            # if result.get("success"):
            #     self._switch_to_tree()
        except Exception as e:
            self._update_results(f"❌ {str(e)}", self.results_container)
    
    async def _process_last_recording(self):
        raw_path = self.recordings_dir / "latest_raw.webm"
        if not raw_path.exists():
            self._update_results("❌ No recording", self.results_container)
            return
        self._update_results("🎯 Processing via MCP...", self.results_container)
        try:
            # Use MCP client to process audio
            async with InputMCPClient(self.mcp_server_url) as mcp_client:
                result = await mcp_client.process_audio_input(
                    audio_file_path=str(raw_path.absolute())
                )

            self._display_result(result, self.results_container)
            # Don't auto-navigate - let user review results first
            # if result.get("success"):
            #     self._switch_to_tree()
        except Exception as e:
            self._update_results(f"❌ {str(e)}", self.results_container)
    
    async def _process_custom_text(self):
        """Process custom text and save to history."""
        text = self.text_input.value
        if not text:
            self._update_results("❌ Enter text!", self.text_results_container)
            return

        # Save to history
        entry_id = self.text_history.add_entry(text)

        self._update_results("🎯 Processing via MCP...", self.text_results_container)

        try:
            # Use MCP client to process text
            async with InputMCPClient(self.mcp_server_url) as mcp_client:
                result = await mcp_client.process_text_input(text=text)

            # Update history with results
            if result.get("success"):
                extraction = result.get("extraction", {})
                self.text_history.update_status(
                    entry_id,
                    "processed",
                    persons=len(extraction.get("persons", [])),
                    relationships=len(extraction.get("relationships", []))
                )

                # Check for warnings from RelationExpert or Storage
                warnings = []
                if "relation_expert" in result:
                    merges = result["relation_expert"].get("auto_merged", 0)
                    if merges > 0:
                        warnings.append(f"Merged {merges} duplicate(s) with existing records")

                if "storage" in result:
                    storage_errors = result["storage"].get("errors", [])
                    if storage_errors:
                        # Log technical details but show user-friendly message
                        print(f"[UI] Storage warnings: {storage_errors}")
                        warnings.append("Some data may need review (check CRM tab)")

                # Show result with warnings if any
                self._display_result(result, self.text_results_container)
                if warnings:
                    ui.notify("\n".join(warnings), type="warning", position="top")

            else:
                self.text_history.update_status(entry_id, "failed", error=result.get("error", ""))
                # Show user-friendly error message
                self._update_results(
                    "❌ Processing failed. Please check your input and try again.",
                    self.text_results_container
                )
                # Log technical details
                print(f"[UI] Processing error: {result.get('error', 'Unknown error')}")

            self._load_text_history()

            # Don't auto-navigate - let user review results first
            # if result.get("success"):
            #     self._switch_to_tree()

        except Exception as e:
            # Log technical error
            print(f"[UI] Exception during text processing: {str(e)}")
            import traceback
            traceback.print_exc()

            # Show user-friendly message
            self.text_history.update_status(entry_id, "failed", error="Processing error")
            self._update_results(
                "❌ An error occurred while processing. Please try again or contact support if the issue persists.",
                self.text_results_container
            )
            self._load_text_history()
    
    def _on_tab_change(self, new_tab):
        """Handle tab changes - refresh tree view when navigating to it."""
        if new_tab == self.tree_tab:
            print("[FamilyNetworkApp] Navigated to Family Tree tab - refreshing...")
            self._render_tree_view()

    def _view_family_tree(self):
        """Navigate to Family Tree and refresh the view."""
        self._render_tree_view()  # Refresh first
        self.tabs.set_value(self.tree_tab)  # Then navigate
        ui.notify("✅ Family Tree updated!", type="positive")

    def _switch_to_tree(self):
        self.tabs.set_value(self.tree_tab)
        ui.notify("✅ Updated! View tree below.", type="positive")

    async def _send_chat(self):
        q = self.chat_input.value
        if not q:
            return
        self.chat_input.value = ""
        with self.chat_container:
            ui.label(f"You: {q}").classes("font-bold text-blue-600")
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, self.query_agent.query, q)
            with self.chat_container:
                ui.label(f"🤖: {result.get('answer', 'No answer')}").classes("mb-4")
        except Exception as e:
            with self.chat_container:
                ui.label(f"❌ {str(e)}").classes("text-red-500")
    
    def _quick_question(self, q: str):
        self.chat_input.value = q
        asyncio.create_task(self._send_chat())
    
    def _display_result(self, result: dict, container):
        container.clear()
        with container:
            if result.get("success"):
                # Header
                with ui.card().classes("w-full p-4 bg-green-50 border-l-4 border-green-500"):
                    ui.label("✅ Processing Complete!").classes("text-green-700 font-bold text-lg")

                # Processing Steps
                steps = result.get("steps", [])
                if steps:
                    with ui.card().classes("w-full p-4 mt-2"):
                        ui.label("🔄 Agent Processing Steps").classes("font-bold mb-2")
                        for i, step in enumerate(steps, 1):
                            agent_name = step.get("agent", "unknown")
                            status = step.get("status", "unknown")
                            status_icon = {"running": "⏳", "done": "✅", "failed": "❌"}.get(status, "•")
                            ui.label(f"{i}. {status_icon} {agent_name.upper()}: {status}").classes("text-sm")

                # Extraction Details
                ext = result.get("extraction", {})
                if ext:
                    with ui.card().classes("w-full p-4 mt-2"):
                        ui.label("👥 Persons Extracted").classes("font-bold mb-2")
                        persons = ext.get("persons", [])
                        if persons:
                            for person in persons:
                                with ui.row().classes("w-full items-center gap-2 p-2 bg-gray-50 rounded mb-1"):
                                    ui.label(f"• {person.get('name', 'Unknown')}").classes("font-semibold")
                                    if person.get("gender"):
                                        ui.badge(person["gender"]).classes("bg-blue-500")
                                    if person.get("age"):
                                        ui.badge(f"Age: {person['age']}").classes("bg-purple-500")
                                    if person.get("location"):
                                        ui.badge(f"📍 {person['location']}").classes("bg-green-500")
                                    if person.get("occupation"):
                                        ui.badge(f"💼 {person['occupation']}").classes("bg-orange-500")
                                    if person.get("is_speaker"):
                                        ui.badge("SPEAKER").classes("bg-red-500")
                        else:
                            ui.label("No persons extracted").classes("text-gray-500")

                # Relationships Details
                if ext:
                    with ui.card().classes("w-full p-4 mt-2"):
                        ui.label("🔗 Relationships Extracted").classes("font-bold mb-2")
                        relationships = ext.get("relationships", [])
                        if relationships:
                            for rel in relationships:
                                p1 = rel.get("person1", "?")
                                p2 = rel.get("person2", "?")
                                rel_type = rel.get("relation_term", "related to")
                                with ui.row().classes("w-full items-center gap-2 p-2 bg-blue-50 rounded mb-1"):
                                    ui.label(f"• {p1}").classes("font-semibold")
                                    ui.label("→").classes("text-gray-400")
                                    ui.badge(rel_type).classes("bg-blue-600")
                                    ui.label("→").classes("text-gray-400")
                                    ui.label(f"{p2}").classes("font-semibold")
                        else:
                            ui.label("No relationships extracted").classes("text-gray-500")

                # 🔍 AGENT TRAJECTORIES - Full ReAct pattern display
                agent_trajectories = result.get("agent_trajectories", [])
                if agent_trajectories:
                    from src.ui.components.agent_trajectory_view import render_agent_trajectories
                    render_agent_trajectories(agent_trajectories)

                # Storage Summary
                storage = result.get("storage", {})
                if storage:
                    with ui.card().classes("w-full p-4 mt-2"):
                        ui.label("💾 Storage Summary").classes("font-bold mb-2")
                        ui.label(storage.get('summary', 'No details')).classes("text-sm")

                        # Families created
                        families = storage.get("families_created", 0)
                        persons = storage.get("persons_created", 0)
                        if families > 0:
                            ui.label(f"✅ Created {families} family/families").classes("text-green-600 text-sm mt-1")
                        if persons > 0:
                            ui.label(f"✅ Added {persons} person(s)").classes("text-green-600 text-sm")

                        # Duplicates Skipped
                        duplicates = storage.get("duplicates_skipped", [])
                        if duplicates:
                            with ui.expansion("⚠️ Duplicates Detected (Not Stored)", icon="content_copy").classes("mt-2 text-yellow-600"):
                                for dup in duplicates:
                                    with ui.row().classes("w-full items-start gap-2 p-2 bg-yellow-50 rounded mb-2"):
                                        ui.icon("person").classes("text-yellow-600")
                                        with ui.column().classes("flex-1"):
                                            ui.label(f"{dup['name']}").classes("font-semibold text-sm")
                                            ui.label(f"Reason: {dup['reason']}").classes("text-xs text-gray-600")

                        # Errors/Warnings
                        errors = storage.get("errors", [])
                        if errors:
                            with ui.expansion("⚠️ Warnings/Errors", icon="warning").classes("mt-2 text-orange-600"):
                                for err in errors:
                                    ui.label(f"• {err}").classes("text-sm text-orange-700")

                # Agent Reasoning Trails (Collapsible)
                with ui.expansion("🧠 Agent Reasoning Trails (ReAct Pattern)", icon="psychology").classes("mt-4 w-full"):
                    with ui.card().classes("w-full p-4"):
                        ui.label("Agent Processing Chain").classes("font-bold mb-3 text-blue-700")

                        # Show processing steps
                        steps = result.get("steps", [])
                        for i, step in enumerate(steps, 1):
                            agent_name = step.get("agent", "unknown").upper()
                            status = step.get("status", "unknown")
                            status_icon = {"running": "⏳", "done": "✅", "failed": "❌"}.get(status, "•")
                            status_color = {"running": "text-yellow-600", "done": "text-green-600", "failed": "text-red-600"}.get(status, "text-gray-600")

                            with ui.column().classes("w-full mb-3 p-3 bg-gray-50 rounded"):
                                ui.label(f"{i}. {agent_name}").classes("font-semibold text-sm mb-1")
                                ui.label(f"{status_icon} Status: {status}").classes(f"text-xs {status_color}")

                        # Show extraction details if available
                        ext = result.get("extraction", {})
                        if ext:
                            ui.separator().classes("my-3")
                            ui.label("Extraction Agent Details").classes("font-semibold text-sm mb-2")
                            with ui.column().classes("text-xs text-gray-700 space-y-1"):
                                ui.label(f"• Extracted {len(ext.get('persons', []))} person(s)")
                                ui.label(f"• Found {len(ext.get('relationships', []))} relationship(s)")
                                langs = ext.get("languages_detected", [])
                                if langs:
                                    ui.label(f"• Languages: {', '.join(langs)}")

                        # Show relation expert details if available
                        rel_expert = result.get("relation_expert", {})
                        if rel_expert:
                            ui.separator().classes("my-3")
                            ui.label("Relation Expert Details").classes("font-semibold text-sm mb-2")
                            with ui.column().classes("text-xs text-gray-700 space-y-1"):
                                ui.label(f"• Auto-merged: {rel_expert.get('auto_merged', 0)} duplicate(s)")
                                ui.label(f"• Needs clarification: {rel_expert.get('needs_clarification', 0)}")
                                ui.label(f"• Total merges: {rel_expert.get('merges', 0)}")

                        # 🔍 AGENT TRAJECTORIES - Full ReAct pattern display
                        agent_trajectories = result.get("agent_trajectories", [])
                        if agent_trajectories:
                            ui.separator().classes("my-3")
                            from src.ui.components.agent_trajectory_view import render_agent_trajectories
                            render_agent_trajectories(agent_trajectories)

                # Action Buttons
                with ui.row().classes("gap-2 mt-4"):
                    ui.button("View Family Tree", on_click=self._view_family_tree).classes("bg-blue-500")
                    ui.button("View in CRM", on_click=lambda: self.tabs.set_value(self.crm_tab)).classes("bg-green-500")
            else:
                with ui.card().classes("w-full p-4 bg-red-50 border-l-4 border-red-500"):
                    ui.label(f"❌ Error: {result.get('error')}").classes("text-red-600 font-bold")
    
    def _update_results(self, msg: str, container):
        container.clear()
        with container:
            ui.label(msg)

    def _setup_temples_tab(self):
        """Setup Temples tab with table-based view and drill-down navigation."""
        # Breadcrumb navigation container
        self.temples_breadcrumb = ui.row().classes("w-full mb-2")

        # Main temples container
        self.temples_container = ui.column().classes("w-full")

        # Start with list view
        self.current_temple_id = None
        self._show_temples_list()

    def _show_temples_list(self):
        """Show temples list view."""
        # Update breadcrumb
        self.temples_breadcrumb.clear()
        with self.temples_breadcrumb:
            ui.label("TEMPLES").classes("text-lg font-bold text-orange-600")

        # Update main container
        self.temples_container.clear()
        with self.temples_container:
            ui.label("Hindu Temples & Spiritual Centers").classes("text-2xl font-bold mb-4")

            with ui.row().classes("w-full mb-4 gap-2"):
                ui.button("+ Add Temple", on_click=lambda: ui.notify("Add temple feature coming soon!")).classes("bg-orange-600")
                ui.button("🔄 Refresh", on_click=lambda: self._show_temples_list()).classes("bg-gray-600")

            temples = self.temple_store.get_all_temples()

            if not temples:
                ui.label("No temples found. Click '+ Add Temple' to add your first temple.").classes("text-gray-500 italic")
                return

            ui.label(f"Total temples: {len(temples)}").classes("text-sm text-gray-600 mb-2")

            with ui.element("table").classes("w-full border-collapse"):
                with ui.element("thead").classes("bg-gray-100"):
                    with ui.element("tr"):
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("Name")
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("Deity")
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("City")
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("State")
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("Type")
                        with ui.element("th").classes("p-2 text-left border"):
                            ui.label("Actions")

                with ui.element("tbody"):
                    for temple in temples[:20]:
                        with ui.element("tr").classes("hover:bg-gray-50"):
                            with ui.element("td").classes("p-2 border"):
                                ui.label(temple.name)
                            with ui.element("td").classes("p-2 border"):
                                ui.label(temple.deity or "-")
                            with ui.element("td").classes("p-2 border"):
                                ui.label(temple.city or "-")
                            with ui.element("td").classes("p-2 border"):
                                ui.label(temple.state or "-")
                            with ui.element("td").classes("p-2 border"):
                                ui.label(temple.temple_type or "-")
                            with ui.element("td").classes("p-2 border"):
                                with ui.row().classes("gap-1"):
                                    ui.button("View", on_click=lambda t=temple: self._show_temple_detail(t.id)).classes("bg-blue-500 text-white text-xs px-2 py-1")
                                    ui.button("Set as Home", on_click=lambda t=temple: self._set_home_temple(t.id, t.name)).classes("bg-green-600 text-white text-xs px-2 py-1")

    def _show_temple_detail(self, temple_id: int):
        """Show temple detail view with sub-tabs."""
        temple = self.temple_store.get_temple(temple_id)
        if not temple:
            ui.notify("Temple not found", type="negative")
            return

        self.current_temple_id = temple_id

        # Update breadcrumb
        self.temples_breadcrumb.clear()
        with self.temples_breadcrumb:
            ui.button("TEMPLES", on_click=lambda: self._show_temples_list()).props("flat color=primary").classes("text-blue-600")
            ui.label("/").classes("mx-2")
            ui.label(temple.name).classes("text-lg font-bold text-orange-600")

        # Update main container
        self.temples_container.clear()
        with self.temples_container:
            ui.label(f"{temple.name}").classes("text-2xl font-bold mb-4")

            # Sub-tabs for detail view
            with ui.tabs().classes("w-full") as detail_tabs:
                overview_tab = ui.tab("📋 Overview")
                followers_tab = ui.tab("👥 Followers")
                donations_tab = ui.tab("💰 Donations")
                voice_tab = ui.tab("🎤 Voice")
                text_tab = ui.tab("✏️ Text Input")

            with ui.tab_panels(detail_tabs, value=overview_tab).classes("w-full"):
                with ui.tab_panel(overview_tab):
                    self._show_temple_overview(temple)

                with ui.tab_panel(followers_tab):
                    self._show_temple_followers(temple_id)

                with ui.tab_panel(donations_tab):
                    self._show_temple_donations(temple_id)

                with ui.tab_panel(voice_tab):
                    self._setup_record_tab()

                with ui.tab_panel(text_tab):
                    self._setup_text_tab()

    def _show_temple_overview(self, temple):
        """Show temple overview information."""
        with ui.card().classes("w-full p-4"):
            with ui.row().classes("w-full gap-8"):
                # Left column
                with ui.column().classes("flex-1"):
                    ui.label("Basic Information").classes("text-lg font-bold mb-2")
                    ui.label(f"Deity: {temple.deity}").classes("mb-1")
                    ui.label(f"Type: {temple.temple_type}").classes("mb-1")
                    if temple.established_year:
                        ui.label(f"Established: {temple.established_year}").classes("mb-1")

                    ui.label("Location").classes("text-lg font-bold mt-4 mb-2")
                    if temple.address:
                        ui.label(f"Address: {temple.address}").classes("mb-1")
                    ui.label(f"City: {temple.city}").classes("mb-1")
                    ui.label(f"State: {temple.state}").classes("mb-1")
                    ui.label(f"Country: {temple.country}").classes("mb-1")
                    if temple.pincode:
                        ui.label(f"Pincode: {temple.pincode}").classes("mb-1")

                # Right column
                with ui.column().classes("flex-1"):
                    ui.label("Contact").classes("text-lg font-bold mb-2")
                    if temple.phone:
                        ui.label(f"Phone: {temple.phone}").classes("mb-1")
                    if temple.email:
                        ui.label(f"Email: {temple.email}").classes("mb-1")
                    if temple.website:
                        ui.label(f"Website: {temple.website}").classes("mb-1")

                    if temple.timings:
                        ui.label("Timings").classes("text-lg font-bold mt-4 mb-2")
                        ui.label(temple.timings).classes("mb-1")

            if temple.description:
                ui.label("Description").classes("text-lg font-bold mt-4 mb-2")
                ui.label(temple.description).classes("text-gray-700")

            if temple.facilities:
                ui.label("Facilities").classes("text-lg font-bold mt-4 mb-2")
                ui.label(temple.facilities).classes("text-gray-700")

    def _show_temple_followers(self, temple_id: int):
        """Show temple followers in tabular format."""
        followers = self.temple_store.get_temple_followers(temple_id)

        ui.label(f"Total Followers: {len(followers)}").classes("text-sm text-gray-600 mb-2")

        ui.button("+ Add Follower", on_click=lambda: ui.notify("Add follower feature coming soon!")).classes("bg-green-600 mb-4")

        if not followers:
            ui.label("No followers yet.").classes("text-gray-500 italic")
            return

        with ui.element("table").classes("w-full border-collapse"):
            with ui.element("thead").classes("bg-gray-100"):
                with ui.element("tr"):
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Name")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Relationship")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Since Year")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Frequency")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Role")

            with ui.element("tbody"):
                for follower in followers[:15]:
                    with ui.element("tr").classes("hover:bg-gray-50"):
                        with ui.element("td").classes("p-2 border"):
                            ui.label(follower.get("person_name", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(follower.get("relationship_type", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(str(follower.get("since_year", "-")))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(follower.get("frequency", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(follower.get("role", "-"))

    def _show_temple_donations(self, temple_id: int):
        """Show temple donations in tabular format with search."""
        ui.label("Donations & Receipts").classes("text-xl font-bold mb-4")

        with ui.row().classes("w-full mb-4 gap-2"):
            search_input = ui.input("Search by name, phone, email...").classes("flex-1")
            ui.button("🔍 Search", on_click=lambda: ui.notify("Search feature coming soon!")).classes("bg-blue-600")
            ui.button("+ Create Receipt", on_click=lambda: self._show_create_receipt_dialog(temple_id)).classes("bg-green-600")

        donations_data = self.temple_store.get_temple_donations(temple_id)
        donations_list = donations_data.get("donations", []) if isinstance(donations_data, dict) else []

        ui.label(f"Total Donations: {len(donations_list)}").classes("text-sm text-gray-600 mb-2")

        if not donations_list:
            ui.label("No donations recorded yet.").classes("text-gray-500 italic")
            return

        with ui.element("table").classes("w-full border-collapse"):
            with ui.element("thead").classes("bg-gray-100"):
                with ui.element("tr"):
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Devotee")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Amount")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Date")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Cause")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Payment")
                    with ui.element("th").classes("p-2 text-left border"):
                        ui.label("Receipt #")

            with ui.element("tbody"):
                for donation in donations_list[:15]:
                    with ui.element("tr").classes("hover:bg-gray-50"):
                        with ui.element("td").classes("p-2 border"):
                            ui.label(donation.get("person_name", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(f"{donation.get('currency', 'USD')} {donation.get('amount', 0):.2f}")
                        with ui.element("td").classes("p-2 border"):
                            ui.label(donation.get("donation_date", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(donation.get("cause", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(donation.get("payment_method", "-"))
                        with ui.element("td").classes("p-2 border"):
                            ui.label(donation.get("receipt_number", "-"))


    def _show_create_receipt_dialog(self, temple_id: int):
        """Show dialog to create a donation receipt."""
        from src.graph.models_v2 import Donation, PAYMENT_METHODS, COMMON_CAUSES, COMMON_DEITIES
        from datetime import datetime

        with ui.dialog() as dialog, ui.card().classes("w-[800px]"):
            ui.label("Create Donation Receipt").classes("text-2xl font-bold mb-4")

            # Devotee selection section
            ui.label("1. Select Devotee").classes("text-lg font-bold mb-2")
            devotee_container = ui.column().classes("w-full mb-4")

            selected_person_id = {"value": None}
            selected_person_name = {"value": None}

            def refresh_devotee_selection():
                devotee_container.clear()
                with devotee_container:
                    if selected_person_id["value"]:
                        ui.label(f"✓ Selected: {selected_person_name['value']}").classes("text-green-600 font-bold mb-2")
                        ui.button("Change Devotee", on_click=lambda: show_devotee_picker()).classes("bg-blue-500")
                    else:
                        with ui.row().classes("w-full gap-4 items-center"):
                            ui.button("Select Existing Devotee", on_click=lambda: show_devotee_picker()).classes("bg-blue-600")
                            ui.label("OR").classes("text-gray-500 font-bold")
                            ui.button("Create New Devotee", on_click=lambda: show_new_devotee_form()).classes("bg-green-600")

            def show_devotee_picker():
                """Show dialog to pick from existing persons."""
                with ui.dialog() as picker_dialog, ui.card().classes("w-[600px]"):
                    ui.label("Select Devotee").classes("text-xl font-bold mb-4")

                    # Search input
                    search_input = ui.input("Search by name, phone, email...").classes("w-full mb-4")

                    # Results container
                    results_container = ui.column().classes("w-full max-h-96 overflow-y-auto")

                    def search_persons():
                        results_container.clear()
                        search_term = search_input.value.lower() if search_input.value else ""

                        persons = self.crm_store_v2.get_all()

                        if search_term:
                            persons = [p for p in persons if (
                                search_term in p.full_name.lower() or
                                search_term in p.phone.lower() or
                                search_term in p.email.lower()
                            )]

                        with results_container:
                            if not persons:
                                ui.label("No devotees found.").classes("text-gray-500 italic")
                            else:
                                for person in persons[:20]:
                                    with ui.card().classes("w-full mb-2 p-3 cursor-pointer hover:bg-gray-100"):
                                        with ui.row().classes("w-full items-center"):
                                            with ui.column().classes("flex-1"):
                                                ui.label(person.full_name).classes("font-bold")
                                                if person.phone or person.email:
                                                    ui.label(f"{person.phone} | {person.email}").classes("text-sm text-gray-600")
                                                if person.family_code:
                                                    ui.label(f"Family: {person.family_code}").classes("text-xs text-blue-600")
                                            ui.button("Select", on_click=lambda p=person: select_person(p)).classes("bg-green-600 text-xs")

                    def select_person(person):
                        selected_person_id["value"] = person.id
                        selected_person_name["value"] = person.full_name
                        picker_dialog.close()
                        refresh_devotee_selection()

                    search_input.on("input", search_persons)
                    search_persons()  # Initial load

                    ui.button("Cancel", on_click=picker_dialog.close).classes("bg-gray-500 mt-4")

                picker_dialog.open()

            def show_new_devotee_form():
                """Show dialog to create new person."""
                with ui.dialog() as new_person_dialog, ui.card().classes("w-[600px]"):
                    ui.label("Create New Devotee").classes("text-xl font-bold mb-4")

                    # Basic fields
                    first_name_input = ui.input("First Name *").classes("w-full mb-2")
                    last_name_input = ui.input("Last Name").classes("w-full mb-2")
                    phone_input = ui.input("Phone").classes("w-full mb-2")
                    email_input = ui.input("Email").classes("w-full mb-2")
                    city_input = ui.input("City").classes("w-full mb-2")

                    # Family selection
                    ui.label("Family (Optional)").classes("font-bold mb-2")
                    family_select = ui.select(
                        options={0: "No Family"} | {f.id: f"{f.code} - {f.surname}" for f in self.family_registry.get_all()},
                        value=0
                    ).classes("w-full mb-4")

                    def create_person():
                        if not first_name_input.value:
                            ui.notify("First name is required!", type="negative")
                            return

                        from src.graph.models_v2 import PersonProfileV2

                        family_id = family_select.value if family_select.value != 0 else None
                        family_obj = self.family_registry.get_by_id(family_id) if family_id else None

                        person = PersonProfileV2(
                            first_name=first_name_input.value,
                            last_name=last_name_input.value,
                            phone=phone_input.value,
                            email=email_input.value,
                            city=city_input.value,
                            family_id=family_id,
                            family_uuid=family_obj.uuid if family_obj else "",
                            family_code=family_obj.code if family_obj else ""
                        )

                        person_id = self.crm_store_v2.add_person(person)
                        selected_person_id["value"] = person_id
                        selected_person_name["value"] = person.full_name

                        ui.notify(f"Created devotee: {person.full_name}", type="positive")
                        new_person_dialog.close()
                        refresh_devotee_selection()

                    ui.button("Create Devotee", on_click=create_person).classes("bg-green-600 mt-4")
                    ui.button("Cancel", on_click=new_person_dialog.close).classes("bg-gray-500 mt-2")

                new_person_dialog.open()

            refresh_devotee_selection()

            ui.separator().classes("my-4")

            # Donation details
            ui.label("2. Donation Details").classes("text-lg font-bold mb-2")

            with ui.row().classes("w-full gap-4"):
                amount_input = ui.number("Amount *", value=0.0, format="%.2f", min=0).classes("flex-1")
                currency_select = ui.select(
                    options={"USD": "US Dollar ($)", "INR": "Indian Rupee (₹)"},
                    value="USD",
                    label="Currency"
                ).classes("flex-1")

            donation_date_input = ui.input("Donation Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d")).classes("w-full mb-2")

            cause_input = ui.select(
                options={c: c for c in COMMON_CAUSES},
                label="Cause",
                value=COMMON_CAUSES[0] if COMMON_CAUSES else ""
            ).classes("w-full mb-2")

            deity_input = ui.select(
                options={d: d for d in COMMON_DEITIES},
                label="Deity",
                value=COMMON_DEITIES[0] if COMMON_DEITIES else ""
            ).classes("w-full mb-2")

            payment_method_select = ui.select(
                options=PAYMENT_METHODS,
                label="Payment Method",
                value=""
            ).classes("w-full mb-2")

            notes_input = ui.textarea("Notes (Optional)").classes("w-full mb-4")

            ui.separator().classes("my-4")

            # Action buttons
            def save_donation():
                if not selected_person_id["value"]:
                    ui.notify("Please select a devotee!", type="negative")
                    return

                if not amount_input.value or amount_input.value <= 0:
                    ui.notify("Please enter a valid donation amount!", type="negative")
                    return

                donation = Donation(
                    person_id=selected_person_id["value"],
                    temple_id=temple_id,
                    amount=amount_input.value,
                    currency=currency_select.value,
                    donation_date=donation_date_input.value,
                    cause=cause_input.value,
                    deity=deity_input.value,
                    payment_method=payment_method_select.value,
                    notes=notes_input.value
                )

                donation_id = self.temple_store.add_donation(donation)
                ui.notify(f"Donation receipt created successfully! (ID: {donation_id})", type="positive")
                dialog.close()
                # Refresh the donations view
                self._show_temple_detail(temple_id)

            with ui.row().classes("w-full gap-2"):
                ui.button("Save Receipt", on_click=save_donation).classes("bg-green-600 flex-1")
                ui.button("Cancel", on_click=dialog.close).classes("bg-gray-500 flex-1")

        dialog.open()


def run_app():
    # Add static files support
    from pathlib import Path
    from nicegui import app
    app.add_static_files('/static', str(Path(__file__).parent.parent.parent / 'static'))

    app_instance = FamilyNetworkApp()
    app_instance.setup()
    ui.run(title="Family Network", port=8080, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    run_app()
