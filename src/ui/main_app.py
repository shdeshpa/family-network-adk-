"""Main NiceGUI application with ADK agents."""

from pathlib import Path
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from nicegui import ui

from src.ui.audio_recorder import AudioRecorderUI
from src.ui.cytoscape_tree import CytoscapeTree
from src.ui.crm_editor import CRMEditor
from src.ui.crm_editor_v2 import CRMEditorV2
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.graph.enhanced_crm import EnhancedCRM
from src.graph.text_history import TextHistory
from src.agents.adk.orchestrator import FamilyOrchestrator
from src.agents.adk.query_agent import QueryAgent


executor = ThreadPoolExecutor(max_workers=2)


class FamilyNetworkApp:
    """Main application for Family Network."""

    def __init__(self):
        self.recordings_dir = Path("data/recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        self.person_store = PersonStore()
        self.family_graph = FamilyGraph()
        self.crm_store = CRMStore()
        self.enhanced_crm = EnhancedCRM()
        self.text_history = TextHistory()

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
        """Setup the main UI with tabs."""
        ui.label("🏠 Family Network System").classes("text-3xl font-bold mb-6")
        
        with ui.tabs().classes("w-full") as self.tabs:
            self.record_tab = ui.tab("🎤 Record")
            self.text_tab = ui.tab("📝 Text Input")
            self.tree_tab = ui.tab("🌳 Family Tree")
            self.crm_tab = ui.tab("📇 CRM")
            self.chat_tab = ui.tab("💬 Chat")
        
        with ui.tab_panels(self.tabs, value=self.record_tab).classes("w-full"):
            with ui.tab_panel(self.record_tab):
                self._setup_record_tab()
            with ui.tab_panel(self.text_tab):
                self._setup_text_tab()
            with ui.tab_panel(self.tree_tab):
                self._setup_tree_tab()
            with ui.tab_panel(self.crm_tab):
                self._setup_crm_tab()
            with ui.tab_panel(self.chat_tab):
                self._setup_chat_tab()
    
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
        
        self.tree_container = ui.column().classes("w-full")
        self._render_tree_view()
    
    def _render_tree_view(self):
        """Render the tree view."""
        if not hasattr(self, 'tree_container'):
            return
        try:
            self.tree_container.clear()
            with self.tree_container:
                tree = CytoscapeTree(
                    person_store=self.person_store,
                    family_graph=self.family_graph,
                    enhanced_crm=self.enhanced_crm
                )
                tree.render()
        except Exception as e:
            with self.tree_container:
                ui.label(f"Error rendering tree: {str(e)}").classes("text-red-500")
    
    def _refresh_tree_view(self):
        """Refresh the tree view."""
        try:
            self._render_tree_view()
            ui.notify("Tree refreshed", type="info")
        except Exception as e:
            ui.notify(f"Error refreshing tree: {str(e)}", type="negative")
    
    def _setup_crm_tab(self):
        """Setup CRM tab with V2 editor."""
        with ui.row().classes("w-full justify-between items-center mb-4"):
            ui.label("📇 Contact Management").classes("text-xl font-bold")
            with ui.row().classes("gap-2"):
                ui.button("V2 (New)", on_click=self._show_crm_v2).classes("text-xs bg-green-500 text-white")
                ui.button("V1 (Legacy)", on_click=self._show_crm_v1).classes("text-xs bg-gray-400 text-white")

        self.crm_container = ui.column().classes("w-full")
        self._show_crm_v2()

    def _show_crm_v2(self):
        """Show CRM V2 editor."""
        self.crm_container.clear()
        with self.crm_container:
            crm_editor = CRMEditorV2()
            crm_editor.render()

    def _show_crm_v1(self):
        """Show legacy CRM V1 editor."""
        self.crm_container.clear()
        with self.crm_container:
            crm_editor = CRMEditor()
            crm_editor.render()
    
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
            self._update_results("🎯 Processing...", self.results_container)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, self.orchestrator.process_audio, str(raw_path))
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
        self._update_results("🎯 Processing...", self.results_container)
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, self.orchestrator.process_audio, str(raw_path))
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
        
        self._update_results("🎯 Processing...", self.text_results_container)
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, self.orchestrator.process_text, text)
            
            # Update history with results
            if result.get("success"):
                extraction = result.get("extraction", {})
                self.text_history.update_status(
                    entry_id, 
                    "processed",
                    persons=len(extraction.get("persons", [])),
                    relationships=len(extraction.get("relationships", []))
                )
            else:
                self.text_history.update_status(entry_id, "failed", error=result.get("error", ""))
            
            self._display_result(result, self.text_results_container)
            self._load_text_history()

            # Don't auto-navigate - let user review results first
            # if result.get("success"):
            #     self._switch_to_tree()
                
        except Exception as e:
            self.text_history.update_status(entry_id, "failed", error=str(e))
            self._update_results(f"❌ {str(e)}", self.text_results_container)
            self._load_text_history()
    
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

                        # Errors/Warnings
                        errors = storage.get("errors", [])
                        if errors:
                            with ui.expansion("⚠️ Warnings/Errors", icon="warning").classes("mt-2 text-orange-600"):
                                for err in errors:
                                    ui.label(f"• {err}").classes("text-sm text-orange-700")

                # Action Buttons
                with ui.row().classes("gap-2 mt-4"):
                    ui.button("View Family Tree", on_click=lambda: self.tabs.set_value(self.tree_tab)).classes("bg-blue-500")
                    ui.button("View in CRM", on_click=lambda: self.tabs.set_value(self.crm_tab)).classes("bg-green-500")
            else:
                with ui.card().classes("w-full p-4 bg-red-50 border-l-4 border-red-500"):
                    ui.label(f"❌ Error: {result.get('error')}").classes("text-red-600 font-bold")
    
    def _update_results(self, msg: str, container):
        container.clear()
        with container:
            ui.label(msg)


def run_app():
    app = FamilyNetworkApp()
    app.setup()
    ui.run(title="Family Network", port=8080, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    run_app()
