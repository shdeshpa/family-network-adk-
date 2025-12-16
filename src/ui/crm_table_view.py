"""Modern CRM Table View - Flat sortable/filterable table for all persons."""

from nicegui import ui
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.models_v2 import PersonProfileV2
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.models import Person
from typing import List, Optional
from datetime import datetime
import pytz


class CRMTableView:
    """Modern table view for CRM V2 data with sorting and filtering."""

    def __init__(self):
        self.store = CRMStoreV2()
        self.registry = FamilyRegistry()
        self.person_store = PersonStore()  # GraphLite person store
        self.family_graph = FamilyGraph()  # GraphLite relationship graph
        self.all_persons: List[PersonProfileV2] = []
        self.filtered_persons: List[PersonProfileV2] = []
        self.table = None
        self.timezone = pytz.timezone('America/Los_Angeles')  # PST/PDT

    def _format_timestamp_pst(self, iso_timestamp: str) -> str:
        """Convert ISO timestamp to PST formatted string."""
        if not iso_timestamp:
            return "-"
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))

            # If datetime is naive (no timezone), assume it's already in local/PST time
            if dt.tzinfo is None:
                dt = self.timezone.localize(dt)
            else:
                # If it has timezone info, convert to PST
                dt = dt.astimezone(self.timezone)

            # Format as: "Dec 6, 2025 3:45 PM PST"
            return dt.strftime("%b %d, %Y %I:%M %p %Z")
        except Exception:
            return iso_timestamp  # Return original if parsing fails

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
            {"name": "updated_at", "label": "Last Modified", "field": "updated_at", "sortable": True, "align": "left"},
            {"name": "family", "label": "Family", "field": "family", "sortable": True, "align": "left"},
            {"name": "name", "label": "Name", "field": "name", "sortable": True, "align": "left"},
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
                "updated_at": self._format_timestamp_pst(p.updated_at),
                "updated_at_raw": p.updated_at,  # For sorting
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
                pagination={"rowsPerPage": 25, "sortBy": "updated_at", "descending": True}
            ).classes("w-full")

            # Add action buttons in a custom slot
            self.table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense size="sm" icon="visibility" @click="$parent.$emit('view', props.row)" />
                    <q-btn flat dense size="sm" icon="edit" @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense size="sm" icon="delete" color="negative" @click="$parent.$emit('delete', props.row)" />
                </q-td>
            ''')

            # Handle action button clicks
            self.table.on('view', lambda e: self._view_person(e.args['id']))
            self.table.on('edit', lambda e: self._edit_person(e.args['id']))
            self.table.on('delete', lambda e: self._delete_person(e.args['id']))

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
        """Edit person details in a dialog."""
        person = self.store.get_person(person_id)
        if not person:
            return

        with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[600px] max-h-[80vh] overflow-auto"):
            ui.label(f"✏️ Edit {person.first_name} {person.last_name}").classes("text-xl font-bold mb-4")

            with ui.column().classes("w-full gap-3"):
                # Basic Information
                ui.label("Basic Information").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    first_name = ui.input("First Name", value=person.first_name).props("outlined dense").classes("flex-1")
                    last_name = ui.input("Last Name", value=person.last_name).props("outlined dense").classes("flex-1")

                with ui.row().classes("w-full gap-2"):
                    gender = ui.select(
                        label="Gender",
                        options={"M": "Male", "F": "Female", "O": "Other"},
                        value=person.gender or ""
                    ).props("outlined dense").classes("flex-1")
                    birth_year = ui.number("Birth Year", value=person.birth_year, format="%.0f").props("outlined dense").classes("flex-1")

                occupation = ui.input("Occupation", value=person.occupation or "").props("outlined dense").classes("w-full")

                # Contact Information
                ui.label("Contact Information").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    phone = ui.input("Phone", value=person.phone or "").props("outlined dense").classes("flex-1")
                    email = ui.input("Email", value=person.email or "").props("outlined dense").classes("flex-1")

                # Location
                ui.label("Location").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    city = ui.input("City", value=person.city or "").props("outlined dense").classes("flex-1")
                    state = ui.input("State", value=person.state or "").props("outlined dense").classes("flex-1")

                country = ui.input("Country", value=person.country or "").props("outlined dense").classes("w-full")

                # Cultural Information
                ui.label("Cultural Information").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    gothra = ui.input("Gothra", value=person.gothra or "").props("outlined dense").classes("flex-1")
                    nakshatra = ui.input("Nakshatra", value=person.nakshatra or "").props("outlined dense").classes("flex-1")

                # Interests
                ui.label("Interests & Activities").classes("font-bold text-sm text-gray-700 mt-2")
                religious_interests = ui.textarea("Religious Interests", value=person.religious_interests or "").props("outlined rows=2").classes("w-full")
                spiritual_interests = ui.textarea("Spiritual Interests", value=person.spiritual_interests or "").props("outlined rows=2").classes("w-full")
                social_interests = ui.textarea("Social Interests", value=person.social_interests or "").props("outlined rows=2").classes("w-full")
                hobbies = ui.textarea("Hobbies", value=person.hobbies or "").props("outlined rows=2").classes("w-full")

                # Notes
                ui.label("Notes").classes("font-bold text-sm text-gray-700 mt-2")
                notes = ui.textarea("Additional Notes", value=person.notes or "").props("outlined rows=3").classes("w-full")

            # Buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                def save_changes():
                    """Save the edited person and sync with GraphLite."""
                    try:
                        # Step 1: Update CRM
                        success = self.store.update_person(
                            person.id,
                            first_name=first_name.value,
                            last_name=last_name.value,
                            gender=gender.value if gender.value else None,
                            birth_year=int(birth_year.value) if birth_year.value else None,
                            occupation=occupation.value,
                            phone=phone.value,
                            email=email.value,
                            city=city.value,
                            state=state.value,
                            country=country.value,
                            gothra=gothra.value,
                            nakshatra=nakshatra.value,
                            religious_interests=religious_interests.value,
                            spiritual_interests=spiritual_interests.value,
                            social_interests=social_interests.value,
                            hobbies=hobbies.value,
                            notes=notes.value
                        )

                        if success:
                            # Step 2: Sync with GraphLite
                            graphlite_updated = False
                            old_name = person.full_name
                            new_name = f"{first_name.value} {last_name.value}"

                            # Find person in GraphLite by old name
                            graphlite_persons = self.person_store.find_by_name(old_name)
                            if graphlite_persons:
                                # Update the first match
                                gp = graphlite_persons[0]

                                # Build interests list
                                interests_list = []
                                if hobbies.value:
                                    interests_list.extend([h.strip() for h in hobbies.value.split(',') if h.strip()])
                                if religious_interests.value:
                                    interests_list.extend([r.strip() for r in religious_interests.value.split(',') if r.strip()])

                                # Update GraphLite person
                                gp.name = new_name
                                gp.location = city.value or ""
                                gp.gender = gender.value if gender.value else None
                                gp.interests = interests_list[:10]  # Limit to 10

                                # Save changes to GraphLite
                                self.person_store.update_person(gp)
                                graphlite_updated = True

                            if graphlite_updated:
                                ui.notify(f"✅ Updated {new_name} in CRM and GraphLite", type="positive")
                            else:
                                ui.notify(f"✅ Updated {new_name} in CRM (not found in GraphLite)", type="positive")

                            dialog.close()
                            self._load_data()  # Refresh the table
                        else:
                            ui.notify("❌ Failed to update person", type="negative")
                    except Exception as e:
                        ui.notify(f"❌ Error: {str(e)}", type="negative")

                ui.button("Save Changes", on_click=save_changes).props("color=primary")

        dialog.open()

    def _delete_person(self, person_id: int):
        """Delete person from both CRM and GraphLite with confirmation."""
        person = self.store.get_person(person_id)
        if not person:
            return

        with ui.dialog() as dialog, ui.card().classes("p-6"):
            ui.label(f"⚠️ Delete {person.full_name}?").classes("text-xl font-bold mb-4")
            ui.label("This will permanently delete this person from:").classes("mb-2")
            ui.label("  • CRM Database").classes("ml-4")
            ui.label("  • Family Tree (GraphLite)").classes("ml-4")
            ui.label("  • All associated relationships").classes("ml-4")
            ui.label("This action cannot be undone.").classes("font-bold text-red-600 mt-4")

            with ui.row().classes("w-full justify-end gap-2 mt-6"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                def confirm_delete():
                    """Perform the deletion."""
                    try:
                        # Step 1: Find person in GraphLite (need ID for relationship cleanup)
                        graphlite_deleted = False
                        graphlite_persons = self.person_store.find_by_name(person.full_name)

                        if graphlite_persons:
                            for gp in graphlite_persons:
                                # Step 1a: Clean up relationships in FamilyGraph FIRST
                                self.family_graph.delete_person_relationships(gp.id)

                                # Step 1b: Then delete person from PersonStore
                                self.person_store.delete_person(gp.id)
                                graphlite_deleted = True

                        # Step 2: Delete from CRM database
                        crm_deleted = self.store.delete_person(person_id)

                        if crm_deleted:
                            if graphlite_deleted:
                                ui.notify(f"✅ Deleted {person.full_name} from CRM and GraphLite", type="positive")
                            else:
                                ui.notify(f"✅ Deleted {person.full_name} from CRM (not found in GraphLite)", type="positive")
                            dialog.close()
                            self._load_data()  # Refresh the table
                        else:
                            ui.notify("❌ Failed to delete person from CRM", type="negative")
                    except Exception as e:
                        ui.notify(f"❌ Error deleting person: {str(e)}", type="negative")
                        print(f"Delete error details: {e}")  # Debug logging

                ui.button("Delete", on_click=confirm_delete).props("color=negative")

        dialog.open()

    def _add_person_dialog(self):
        """Show add person dialog."""
        with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[600px] max-h-[80vh] overflow-auto"):
            ui.label("➕ Add New Person").classes("text-xl font-bold mb-4")

            with ui.column().classes("w-full gap-3"):
                # Basic Information
                ui.label("Basic Information").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    first_name = ui.input("First Name *", placeholder="Required").props("outlined dense").classes("flex-1")
                    last_name = ui.input("Last Name *", placeholder="Required").props("outlined dense").classes("flex-1")

                with ui.row().classes("w-full gap-2"):
                    gender = ui.select(
                        label="Gender",
                        options={"M": "Male", "F": "Female", "O": "Other", "": "Unspecified"},
                        value=""
                    ).props("outlined dense").classes("flex-1")
                    birth_year = ui.number("Birth Year", format="%.0f", placeholder="e.g., 1985").props("outlined dense").classes("flex-1")

                occupation = ui.input("Occupation", placeholder="e.g., Software Engineer").props("outlined dense").classes("w-full")

                # Contact Information
                ui.label("Contact Information").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    phone = ui.input("Phone", placeholder="e.g., +1-555-123-4567").props("outlined dense").classes("flex-1")
                    email = ui.input("Email", placeholder="e.g., john@example.com").props("outlined dense type=email").classes("flex-1")

                # Location
                ui.label("Location").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    city = ui.input("City", placeholder="e.g., San Francisco").props("outlined dense").classes("flex-1")
                    state = ui.input("State", placeholder="e.g., California").props("outlined dense").classes("flex-1")

                country = ui.input("Country", placeholder="e.g., USA").props("outlined dense").classes("w-full")

                # Family
                ui.label("Family").classes("font-bold text-sm text-gray-700 mt-2")
                families = self.registry.get_all()
                family_options = [""] + [f.code for f in families if not f.is_archived]
                family_code = ui.select(
                    label="Family Code (optional)",
                    options=family_options,
                    value=""
                ).props("outlined dense").classes("w-full")

                # Cultural Information
                ui.label("Cultural Information (Optional)").classes("font-bold text-sm text-gray-700 mt-2")
                with ui.row().classes("w-full gap-2"):
                    gothra = ui.input("Gothra", placeholder="e.g., Kashyap").props("outlined dense").classes("flex-1")
                    nakshatra = ui.input("Nakshatra", placeholder="e.g., Rohini").props("outlined dense").classes("flex-1")

                # Interests
                ui.label("Interests & Activities (Optional)").classes("font-bold text-sm text-gray-700 mt-2")
                religious_interests = ui.textarea("Religious Interests", placeholder="e.g., Temple visits, daily puja").props("outlined rows=2").classes("w-full")
                spiritual_interests = ui.textarea("Spiritual Interests", placeholder="e.g., Meditation, yoga").props("outlined rows=2").classes("w-full")
                social_interests = ui.textarea("Social Interests", placeholder="e.g., Community service, volunteering").props("outlined rows=2").classes("w-full")
                hobbies = ui.textarea("Hobbies", placeholder="e.g., Reading, cricket, cooking").props("outlined rows=2").classes("w-full")

                # Notes
                ui.label("Notes (Optional)").classes("font-bold text-sm text-gray-700 mt-2")
                notes = ui.textarea("Additional Notes").props("outlined rows=3").classes("w-full")

            # Buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                def add_person():
                    """Add the new person."""
                    # Validation
                    if not first_name.value or not last_name.value:
                        ui.notify("❌ First name and last name are required", type="negative")
                        return

                    try:
                        # Add to CRM
                        person_id = self.store.add_person(
                            first_name=first_name.value,
                            last_name=last_name.value,
                            gender=gender.value if gender.value else None,
                            birth_year=int(birth_year.value) if birth_year.value else None,
                            occupation=occupation.value or None,
                            phone=phone.value or None,
                            email=email.value or None,
                            city=city.value or None,
                            state=state.value or None,
                            country=country.value or None,
                            family_code=family_code.value if family_code.value else None,
                            gothra=gothra.value or None,
                            nakshatra=nakshatra.value or None,
                            religious_interests=religious_interests.value or None,
                            spiritual_interests=spiritual_interests.value or None,
                            social_interests=social_interests.value or None,
                            hobbies=hobbies.value or None,
                            notes=notes.value or None
                        )

                        if person_id:
                            # Add to GraphLite
                            full_name = f"{first_name.value} {last_name.value}"
                            location = city.value or ""

                            # Build interests list
                            interests_list = []
                            if hobbies.value:
                                interests_list.extend([h.strip() for h in hobbies.value.split(',') if h.strip()])
                            if religious_interests.value:
                                interests_list.extend([r.strip() for r in religious_interests.value.split(',') if r.strip()])

                            person_obj = Person(
                                name=full_name,
                                location=location,
                                gender=gender.value if gender.value else None,
                                interests=interests_list[:10]  # Limit to 10
                            )
                            graphlite_id = self.person_store.add_person(person_obj)

                            ui.notify(f"✅ Added {full_name} to CRM and GraphLite", type="positive")
                            dialog.close()
                            self._load_data()  # Refresh the table
                        else:
                            ui.notify("❌ Failed to add person to CRM", type="negative")
                    except Exception as e:
                        ui.notify(f"❌ Error adding person: {str(e)}", type="negative")

                ui.button("Add Person", on_click=add_person).props("color=primary")

        dialog.open()
