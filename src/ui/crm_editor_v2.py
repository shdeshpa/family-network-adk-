"""CRM Editor V2 - Shows data from CRM V2 with family grouping."""

from nicegui import ui
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.models_v2 import PersonProfileV2, Donation
from typing import Optional


class CRMEditorV2:
    """CRM Editor for V2 data with family grouping."""

    def __init__(self):
        self.store = CRMStoreV2()
        self.registry = FamilyRegistry()
        self.selected_family_code = None

    def render(self):
        """Render the CRM V2 editor."""
        with ui.column().classes("w-full"):
            # Header
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label("📇 CRM V2 - Family-Based View").classes("text-xl font-bold")
                with ui.row().classes("gap-2"):
                    ui.button("🔄 Refresh", on_click=self._refresh).props("dense").classes("text-sm")
                    ui.button("+ Add Family", on_click=self._show_add_family_dialog).props("dense").classes("text-sm bg-blue-500 text-white")
                    ui.button("+ Add Person", on_click=self._show_add_person_dialog).props("dense").classes("text-sm bg-green-500 text-white")

            # Search and filters
            with ui.row().classes("w-full gap-2 mb-4"):
                self.search_input = ui.input(placeholder="🔍 Search persons...").classes("flex-1").props("dense outlined")
                self.search_input.on("keydown.enter", self._search_persons)
                ui.button("Search", on_click=self._search_persons).props("dense").classes("text-sm")

                self.family_select = ui.select(
                    label="Filter by Family",
                    options=["All Families"],
                    value="All Families"
                ).props("dense outlined").classes("w-64")
                self.family_select.on("update:model-value", self._filter_by_family)

            # Main content area
            self.content_container = ui.column().classes("w-full")
            self._load_data()

    def _refresh(self):
        """Refresh all data."""
        self._load_data()
        ui.notify("Refreshed", type="info")

    def _load_data(self):
        """Load and display all families and persons."""
        self.content_container.clear()

        # Update family dropdown
        families = self.registry.get_all()
        family_options = ["All Families"] + [f.code for f in families]
        self.family_select.options = family_options

        # Get all persons
        persons = self.store.get_all_persons()

        with self.content_container:
            if not persons:
                ui.label("No persons found. Process some text to add data!").classes("text-gray-500 p-4")
                return

            # Show statistics
            with ui.card().classes("w-full p-4 mb-4 bg-blue-50"):
                ui.label(f"📊 Statistics").classes("font-bold mb-2")
                with ui.row().classes("gap-8"):
                    ui.label(f"👨‍👩‍👧‍👦 {len(families)} Families")
                    ui.label(f"👤 {len(persons)} Persons")

            # Group persons by family
            family_groups = {}
            persons_without_family = []

            for person in persons:
                if person.family_code:
                    if person.family_code not in family_groups:
                        family_groups[person.family_code] = []
                    family_groups[person.family_code].append(person)
                else:
                    persons_without_family.append(person)

            # Display families
            for family in families:
                family_persons = family_groups.get(family.code, [])
                if not family_persons and self.selected_family_code:
                    continue

                self._render_family_card(family, family_persons)

            # Display persons without family
            if persons_without_family:
                self._render_unassigned_persons(persons_without_family)

    def _render_family_card(self, family, persons):
        """Render a family card with its members."""
        with ui.expansion(text=f"👨‍👩‍👧‍👦 {family.code} ({len(persons)} members)", icon="family_restroom").classes("w-full mb-2"):
            with ui.card().classes("w-full p-4"):
                # Family details
                with ui.row().classes("w-full justify-between mb-4"):
                    with ui.column():
                        ui.label(f"Surname: {family.surname}").classes("font-bold")
                        ui.label(f"City: {family.city}").classes("text-sm text-gray-600")
                        if family.description:
                            ui.label(f"Description: {family.description}").classes("text-sm text-gray-600")
                    with ui.column().classes("items-end"):
                        ui.label(f"ID: {family.id}").classes("text-xs text-gray-400")
                        ui.label(f"Created: {family.created_at[:10] if family.created_at else 'N/A'}").classes("text-xs text-gray-400")

                ui.separator()

                # Members table
                if persons:
                    ui.label(f"Members ({len(persons)}):").classes("font-bold mt-4 mb-2")

                    # Table header
                    with ui.row().classes("w-full bg-gray-100 p-2 font-bold text-sm"):
                        ui.label("Name").classes("w-48")
                        ui.label("Gender").classes("w-20")
                        ui.label("Birth Year").classes("w-24")
                        ui.label("Occupation").classes("w-32")
                        ui.label("City").classes("w-32")
                        ui.label("Phone").classes("w-32")
                        ui.label("Actions").classes("w-24")

                    # Table rows
                    for person in persons:
                        self._render_person_row(person)
                else:
                    ui.label("No members yet").classes("text-gray-500 italic mt-2")

    def _render_person_row(self, person: PersonProfileV2):
        """Render a person row in the table."""
        with ui.row().classes("w-full p-2 text-sm border-b hover:bg-gray-50 items-center"):
            ui.label(f"{person.first_name} {person.last_name}").classes("w-48 font-medium")
            ui.label(person.gender or "-").classes("w-20")
            ui.label(str(person.birth_year) if person.birth_year else "-").classes("w-24")
            ui.label(person.occupation or "-").classes("w-32 truncate")
            ui.label(person.city or "-").classes("w-32 truncate")
            ui.label(person.phone or "-").classes("w-32")

            with ui.row().classes("w-24 gap-1"):
                ui.button("👁️", on_click=lambda p=person: self._show_person_details(p)).props("flat dense size=sm").tooltip("View details")
                ui.button("✏️", on_click=lambda p=person: self._edit_person(p)).props("flat dense size=sm").tooltip("Edit")

    def _render_unassigned_persons(self, persons):
        """Render persons without a family assignment."""
        with ui.expansion(text=f"❓ Unassigned Persons ({len(persons)})", icon="person_off").classes("w-full mb-2 bg-yellow-50"):
            with ui.card().classes("w-full p-4"):
                ui.label("These persons don't have a family assigned:").classes("text-sm text-gray-600 mb-4")

                # Table
                with ui.row().classes("w-full bg-gray-100 p-2 font-bold text-sm"):
                    ui.label("Name").classes("w-48")
                    ui.label("Gender").classes("w-20")
                    ui.label("City").classes("w-32")
                    ui.label("Notes").classes("flex-1")
                    ui.label("Actions").classes("w-24")

                for person in persons:
                    with ui.row().classes("w-full p-2 text-sm border-b hover:bg-gray-50 items-center"):
                        ui.label(f"{person.first_name} {person.last_name}").classes("w-48 font-medium")
                        ui.label(person.gender or "-").classes("w-20")
                        ui.label(person.city or "-").classes("w-32")
                        notes_preview = (person.notes[:50] + "...") if person.notes and len(person.notes) > 50 else (person.notes or "-")
                        ui.label(notes_preview).classes("flex-1 truncate text-gray-600")

                        with ui.row().classes("w-24 gap-1"):
                            ui.button("👁️", on_click=lambda p=person: self._show_person_details(p)).props("flat dense size=sm").tooltip("View")
                            ui.button("✏️", on_click=lambda p=person: self._edit_person(p)).props("flat dense size=sm").tooltip("Edit")

    def _search_persons(self):
        """Search persons by name."""
        query = self.search_input.value
        if not query:
            self._load_data()
            return

        persons = self.store.search_persons(query=query)

        self.content_container.clear()
        with self.content_container:
            ui.label(f"Search results for: '{query}'").classes("font-bold mb-4")

            if not persons:
                ui.label("No results found").classes("text-gray-500")
                return

            ui.label(f"Found {len(persons)} person(s)").classes("text-sm text-gray-600 mb-2")

            # Display results
            with ui.card().classes("w-full p-4"):
                with ui.row().classes("w-full bg-gray-100 p-2 font-bold text-sm"):
                    ui.label("Name").classes("w-48")
                    ui.label("Family").classes("w-32")
                    ui.label("City").classes("w-32")
                    ui.label("Occupation").classes("w-32")
                    ui.label("Actions").classes("w-24")

                for person in persons:
                    with ui.row().classes("w-full p-2 text-sm border-b hover:bg-gray-50 items-center"):
                        ui.label(f"{person.first_name} {person.last_name}").classes("w-48 font-medium")
                        ui.label(person.family_code or "-").classes("w-32")
                        ui.label(person.city or "-").classes("w-32")
                        ui.label(person.occupation or "-").classes("w-32 truncate")

                        with ui.row().classes("w-24 gap-1"):
                            ui.button("👁️", on_click=lambda p=person: self._show_person_details(p)).props("flat dense size=sm")
                            ui.button("✏️", on_click=lambda p=person: self._edit_person(p)).props("flat dense size=sm")

    def _filter_by_family(self, e):
        """Filter persons by family code."""
        family_code = e.args if e.args != "All Families" else None
        self.selected_family_code = family_code
        # TODO: Implement filtered view
        self._load_data()

    def _show_person_details(self, person: PersonProfileV2):
        """Show detailed person information in a dialog."""
        with ui.dialog() as dialog, ui.card().classes("p-6 min-w-96"):
            ui.label(f"👤 {person.first_name} {person.last_name}").classes("text-xl font-bold mb-4")

            with ui.column().classes("w-full gap-2"):
                self._detail_row("ID", str(person.id))
                self._detail_row("Gender", person.gender or "-")
                self._detail_row("Birth Year", str(person.birth_year) if person.birth_year else "-")
                self._detail_row("Occupation", person.occupation or "-")

                ui.separator()

                self._detail_row("Phone", person.phone or "-")
                self._detail_row("Email", person.email or "-")
                self._detail_row("City", person.city or "-")
                self._detail_row("State", person.state or "-")
                self._detail_row("Country", person.country or "-")

                ui.separator()

                self._detail_row("Family Code", person.family_code or "-")
                self._detail_row("Gothra", person.gothra or "-")
                self._detail_row("Nakshatra", person.nakshatra or "-")

                if person.notes:
                    ui.separator()
                    ui.label("Notes:").classes("font-bold text-sm")
                    ui.label(person.notes).classes("text-sm text-gray-700 whitespace-pre-wrap")

                # Show donations
                donations = self.store.get_donations(person.id)
                if donations:
                    ui.separator()
                    ui.label(f"💰 Donations ({len(donations)}):").classes("font-bold text-sm mt-2")
                    for don in donations:
                        ui.label(f"  • {don.amount} {don.currency} - {don.cause or 'General'}").classes("text-sm")

            ui.button("Close", on_click=dialog.close).classes("mt-4")

        dialog.open()

    def _detail_row(self, label: str, value: str):
        """Render a detail row."""
        with ui.row().classes("w-full"):
            ui.label(f"{label}:").classes("w-32 font-bold text-sm")
            ui.label(value).classes("text-sm text-gray-700")

    def _edit_person(self, person: PersonProfileV2):
        """Edit person details."""
        with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[600px]"):
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

                # Interests (multi-line)
                ui.label("Interests & Activities").classes("font-bold text-sm text-gray-700 mt-2")
                religious_interests = ui.textarea("Religious Interests", value=person.religious_interests or "").props("outlined").classes("w-full").props("rows=2")
                spiritual_interests = ui.textarea("Spiritual Interests", value=person.spiritual_interests or "").props("outlined").classes("w-full").props("rows=2")
                social_interests = ui.textarea("Social Interests", value=person.social_interests or "").props("outlined").classes("w-full").props("rows=2")
                hobbies = ui.textarea("Hobbies", value=person.hobbies or "").props("outlined").classes("w-full").props("rows=2")

                # Notes
                ui.label("Notes").classes("font-bold text-sm text-gray-700 mt-2")
                notes = ui.textarea("Additional Notes", value=person.notes or "").props("outlined").classes("w-full").props("rows=3")

            # Buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                def save_changes():
                    """Save the edited person."""
                    try:
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
                            ui.notify(f"✅ Updated {first_name.value} {last_name.value}", type="positive")
                            dialog.close()
                            self._load_data()
                        else:
                            ui.notify("❌ Failed to update person", type="negative")
                    except Exception as e:
                        ui.notify(f"❌ Error: {str(e)}", type="negative")

                ui.button("Save Changes", on_click=save_changes).props("color=primary")

        dialog.open()

    def _show_add_family_dialog(self):
        """Show dialog to add a new family."""
        ui.notify("Add Family dialog - Coming soon!", type="info")

    def _show_add_person_dialog(self):
        """Show dialog to add a new person."""
        ui.notify("Add Person dialog - Coming soon!", type="info")
