"""Modern CRM Table View - Flat sortable/filterable table for all persons."""

from nicegui import ui
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.models_v2 import PersonProfileV2
from typing import List, Optional


class CRMTableView:
    """Modern table view for CRM V2 data with sorting and filtering."""

    def __init__(self):
        self.store = CRMStoreV2()
        self.registry = FamilyRegistry()
        self.all_persons: List[PersonProfileV2] = []
        self.filtered_persons: List[PersonProfileV2] = []
        self.table = None

    def render(self):
        """Render the modern CRM table view."""
        with ui.column().classes("w-full h-full"):
            # Header with actions
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label("📇 Family Network CRM").classes("text-2xl font-bold")
                with ui.row().classes("gap-2"):
                    ui.button("🔄 Refresh", on_click=self._refresh).props("outline")
                    ui.button("+ Add Person", on_click=self._add_person_dialog).props("color=primary")

            # Filters row
            with ui.row().classes("w-full gap-4 mb-4"):
                self.search_input = ui.input(placeholder="🔍 Search by name...").classes("flex-1")
                self.search_input.on("keydown.enter", self._apply_filters)

                self.family_filter = ui.select(
                    label="Family",
                    options=["All"],
                    value="All"
                ).classes("w-48")
                self.family_filter.on("update:model-value", self._apply_filters)

                self.city_filter = ui.input(placeholder="Filter by city").classes("w-48")
                self.city_filter.on("keydown.enter", self._apply_filters)

                ui.button("Apply Filters", on_click=self._apply_filters).props("outline")
                ui.button("Clear", on_click=self._clear_filters).props("flat")

            # Statistics
            self.stats_row = ui.row().classes("w-full gap-8 mb-4 p-4 bg-blue-50 rounded")
            self._update_stats()

            # Main data table
            self.table_container = ui.column().classes("w-full")
            self._load_data()

    def _load_data(self):
        """Load all data and render table."""
        self.all_persons = self.store.get_all()
        self.filtered_persons = self.all_persons.copy()

        # Update family filter options
        families = self.registry.get_all()
        family_codes = ["All"] + [f.code for f in families if not f.is_archived]
        self.family_filter.options = family_codes

        self._render_table()
        self._update_stats()

    def _render_table(self):
        """Render the main data table."""
        self.table_container.clear()

        if not self.filtered_persons:
            with self.table_container:
                ui.label("No persons found. Add data using Text Input or Record tabs.").classes("text-gray-500 p-8")
            return

        # Build table data
        columns = [
            {"name": "name", "label": "Name", "field": "name", "sortable": True, "align": "left"},
            {"name": "family", "label": "Family", "field": "family", "sortable": True, "align": "left"},
            {"name": "phone", "label": "Phone", "field": "phone", "sortable": True, "align": "left"},
            {"name": "email", "label": "Email", "field": "email", "sortable": True, "align": "left"},
            {"name": "city", "label": "City", "field": "city", "sortable": True, "align": "left"},
            {"name": "age", "label": "Age", "field": "age", "sortable": True, "align": "center"},
            {"name": "activities", "label": "Activities", "field": "activities", "sortable": False, "align": "left"},
            {"name": "actions", "label": "Actions", "field": "actions", "sortable": False, "align": "center"},
        ]

        rows = []
        for p in self.filtered_persons:
            # Get activities summary
            activities = []
            if p.hobbies:
                activities.append(p.hobbies.split('\n')[0][:40])
            if p.religious_interests:
                activities.append(p.religious_interests.split('\n')[0][:40])
            activities_str = ", ".join(activities[:2]) if activities else "-"

            rows.append({
                "id": p.id,
                "name": p.full_name,
                "family": p.family_code or "Unassigned",
                "phone": p.phone or "-",
                "email": p.email or "-",
                "city": p.city or "-",
                "age": p.approximate_age or "-",
                "activities": activities_str,
                "person_obj": p  # Store object for actions
            })

        with self.table_container:
            self.table = ui.table(
                columns=columns,
                rows=rows,
                row_key="id",
                pagination={"rowsPerPage": 25, "sortBy": "name", "descending": False}
            ).classes("w-full")

            # Add action buttons in a custom slot
            self.table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense size="sm" icon="visibility" @click="$parent.$emit('view', props.row)" />
                    <q-btn flat dense size="sm" icon="edit" @click="$parent.$emit('edit', props.row)" />
                </q-td>
            ''')

            # Handle action button clicks
            self.table.on('view', lambda e: self._view_person(e.args['id']))
            self.table.on('edit', lambda e: self._edit_person(e.args['id']))

    def _apply_filters(self):
        """Apply search and filter criteria."""
        search_text = self.search_input.value.lower() if self.search_input.value else ""
        family_code = self.family_filter.value if self.family_filter.value != "All" else None
        city_text = self.city_filter.value.lower() if self.city_filter.value else ""

        self.filtered_persons = []
        for p in self.all_persons:
            # Search filter
            if search_text:
                if search_text not in p.full_name.lower():
                    continue

            # Family filter
            if family_code:
                if p.family_code != family_code:
                    continue

            # City filter
            if city_text:
                if not p.city or city_text not in p.city.lower():
                    continue

            self.filtered_persons.append(p)

        self._render_table()
        self._update_stats()

    def _clear_filters(self):
        """Clear all filters."""
        self.search_input.value = ""
        self.family_filter.value = "All"
        self.city_filter.value = ""
        self.filtered_persons = self.all_persons.copy()
        self._render_table()
        self._update_stats()

    def _update_stats(self):
        """Update statistics display."""
        self.stats_row.clear()
        with self.stats_row:
            families = self.registry.get_all()
            ui.label(f"👨‍👩‍👧‍👦 {len([f for f in families if not f.is_archived])} Families").classes("font-bold")
            ui.label(f"👤 {len(self.all_persons)} Total Persons").classes("font-bold")
            ui.label(f"📊 {len(self.filtered_persons)} Shown").classes("font-bold text-blue-600")

    def _refresh(self):
        """Refresh all data."""
        self._load_data()
        ui.notify("✅ Refreshed", type="positive")

    def _view_person(self, person_id: int):
        """View person details."""
        person = self.store.get_person(person_id)
        if not person:
            return

        with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[600px] max-h-[80vh] overflow-auto"):
            ui.label(f"👤 {person.full_name}").classes("text-2xl font-bold mb-4")

            with ui.column().classes("w-full gap-3"):
                # Basic
                with ui.card().classes("p-4"):
                    ui.label("Basic Information").classes("font-bold text-lg mb-2")
                    with ui.grid(columns=2).classes("w-full gap-2"):
                        self._info_field("Gender", person.gender or "-")
                        self._info_field("Age", str(person.approximate_age) if person.approximate_age else "-")
                        self._info_field("Birth Year", str(person.birth_year) if person.birth_year else "-")
                        self._info_field("Occupation", person.occupation or "-")

                # Contact
                with ui.card().classes("p-4"):
                    ui.label("Contact Information").classes("font-bold text-lg mb-2")
                    with ui.grid(columns=2).classes("w-full gap-2"):
                        self._info_field("Phone", person.phone or "-")
                        self._info_field("Email", person.email or "-")

                # Location
                with ui.card().classes("p-4"):
                    ui.label("Location").classes("font-bold text-lg mb-2")
                    with ui.grid(columns=2).classes("w-full gap-2"):
                        self._info_field("City", person.city or "-")
                        self._info_field("State", person.state or "-")
                        self._info_field("Country", person.country or "-")
                        self._info_field("Family Code", person.family_code or "Unassigned")

                # Cultural
                if person.gothra or person.nakshatra:
                    with ui.card().classes("p-4"):
                        ui.label("Cultural Information").classes("font-bold text-lg mb-2")
                        with ui.grid(columns=2).classes("w-full gap-2"):
                            if person.gothra:
                                self._info_field("Gothra", person.gothra)
                            if person.nakshatra:
                                self._info_field("Nakshatra", person.nakshatra)

                # Activities & Interests
                has_interests = any([person.religious_interests, person.spiritual_interests,
                                    person.social_interests, person.hobbies])
                if has_interests:
                    with ui.card().classes("p-4 bg-blue-50"):
                        ui.label("🌟 Activities & Interests").classes("font-bold text-lg mb-2")
                        if person.religious_interests:
                            ui.label("Religious:").classes("font-bold text-sm text-gray-700")
                            ui.label(person.religious_interests).classes("text-sm mb-2 whitespace-pre-wrap")
                        if person.spiritual_interests:
                            ui.label("Spiritual:").classes("font-bold text-sm text-gray-700")
                            ui.label(person.spiritual_interests).classes("text-sm mb-2 whitespace-pre-wrap")
                        if person.social_interests:
                            ui.label("Social:").classes("font-bold text-sm text-gray-700")
                            ui.label(person.social_interests).classes("text-sm mb-2 whitespace-pre-wrap")
                        if person.hobbies:
                            ui.label("Hobbies:").classes("font-bold text-sm text-gray-700")
                            ui.label(person.hobbies).classes("text-sm whitespace-pre-wrap")

                # Notes
                if person.notes:
                    with ui.card().classes("p-4"):
                        ui.label("Notes").classes("font-bold text-lg mb-2")
                        ui.label(person.notes).classes("text-sm whitespace-pre-wrap")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Close", on_click=dialog.close).props("flat")
                ui.button("Edit", on_click=lambda: (dialog.close(), self._edit_person(person.id))).props("color=primary")

        dialog.open()

    def _info_field(self, label: str, value: str):
        """Render an info field."""
        with ui.column().classes("gap-1"):
            ui.label(label).classes("text-xs font-bold text-gray-500 uppercase")
            ui.label(value).classes("text-sm")

    def _edit_person(self, person_id: int):
        """Edit person (simplified - opens CRM V2 edit)."""
        person = self.store.get_person(person_id)
        if person:
            # Import here to avoid circular dependency
            from src.ui.crm_editor_v2 import CRMEditorV2
            editor = CRMEditorV2()
            editor._edit_person(person)

    def _add_person_dialog(self):
        """Show add person dialog."""
        ui.notify("Add Person - Coming soon!", type="info")
