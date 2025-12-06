"""Enhanced CRM Editor UI - Clean and elegant."""

from nicegui import ui
from src.graph.enhanced_crm import EnhancedCRM, PersonProfile


class CRMEditor:
    """Elegant CRM editor with sortable columns."""
    
    CURRENCIES = {"USD": "US Dollar", "INR": "Indian Rupee", "EUR": "Euro", "GBP": "British Pound"}
    GENDERS = {"": "Not specified", "M": "Male", "F": "Female", "O": "Other"}
    
    def __init__(self):
        self.crm = EnhancedCRM()
        self.selected_ids: set = set()
        self.all_persons: list = []
        self.sort_column = "first_name"
        self.sort_ascending = True
    
    def render(self):
        """Render the CRM editor."""
        with ui.column().classes("w-full"):
            # Compact toolbar
            with ui.row().classes("w-full gap-2 mb-3 items-center"):
                self.search_input = ui.input(placeholder="🔍 Search...").classes("w-48").props("dense outlined")
                self.search_input.on("keydown.enter", self._search)
                
                ui.button("Search", on_click=self._search).props("dense").classes("text-sm")
                ui.button("Show All", on_click=self._load_all).props("flat dense").classes("text-sm")
                
                ui.space()
                
                ui.button("+ Add Person", on_click=self._show_add_dialog).props("dense").classes("text-sm bg-green-600 text-white")
                
                ui.space()
                
                self.select_all_btn = ui.button("☐ All", on_click=self._toggle_select_all).props("flat dense").classes("text-sm")
                self.delete_btn = ui.button("🗑️ Delete (0)", on_click=self._delete_selected).props("flat dense").classes("text-sm text-red-500")
                self.delete_btn.set_visibility(False)
            
            # Table container
            self.table_container = ui.column().classes("w-full")
            self._load_all()
    
    def _load_all(self):
        self.all_persons = self.crm.get_all()
        self._apply_sort()
        self._render_table()
    
    def _search(self):
        query = self.search_input.value
        self.all_persons = self.crm.search(query=query)
        self._apply_sort()
        self._render_table()
    
    def _sort_by(self, column: str):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self._apply_sort()
        self._render_table()
    
    def _apply_sort(self):
        def get_key(p: PersonProfile):
            val = getattr(p, self.sort_column, "") or ""
            if self.sort_column == "first_name":
                val = (p.first_name + " " + p.last_name).lower()
            return str(val).lower()
        self.all_persons.sort(key=get_key, reverse=not self.sort_ascending)
    
    def _toggle_select_all(self):
        if len(self.selected_ids) == len(self.all_persons):
            self.selected_ids.clear()
        else:
            self.selected_ids = {p.id for p in self.all_persons}
        self._render_table()
    
    def _update_selection_ui(self):
        count = len(self.selected_ids)
        self.delete_btn.set_text(f"🗑️ Delete ({count})")
        self.delete_btn.set_visibility(count > 0)
        
        if count == len(self.all_persons) and count > 0:
            self.select_all_btn.set_text("☑ All")
        else:
            self.select_all_btn.set_text("☐ All")
    
    def _render_table(self):
        self.table_container.clear()
        self._update_selection_ui()
        
        with self.table_container:
            if not self.all_persons:
                ui.label("No records found").classes("text-gray-500 p-4")
                return
            
            ui.label(f"{len(self.all_persons)} records").classes("text-xs text-gray-400 mb-1")
            
            # Column definitions
            columns = [
                ("", "checkbox", "w-8"),
                ("Name", "first_name", "w-36"),
                ("Phone", "phone", "w-28"),
                ("Email", "email", "w-40"),
                ("City", "city", "w-28"),
                ("₹/$", "preferred_currency", "w-12"),
                ("Gothra", "gothra", "w-24"),
                ("Interests", "interests", "w-32"),
                ("", "actions", "w-16"),
            ]
            
            # Header
            with ui.row().classes("w-full bg-gray-50 border-b text-xs font-semibold text-gray-600 items-center py-1 px-2"):
                for label, field, width in columns:
                    if field == "checkbox":
                        ui.label("").classes(width)
                    elif field == "actions":
                        ui.label("").classes(width)
                    elif field == "interests":
                        ui.label(label).classes(f"{width} truncate")
                    else:
                        # Sortable column header
                        arrow = ""
                        if self.sort_column == field:
                            arrow = " ↑" if self.sort_ascending else " ↓"
                        
                        btn = ui.button(
                            f"{label}{arrow}",
                            on_click=lambda f=field: self._sort_by(f)
                        ).props("flat dense no-caps").classes(f"{width} text-xs text-gray-600 justify-start p-0")
            
            # Rows
            with ui.scroll_area().classes("w-full").style("height: 350px;"):
                for p in self.all_persons:
                    is_selected = p.id in self.selected_ids
                    bg = "bg-blue-50" if is_selected else "hover:bg-gray-50"
                    
                    with ui.row().classes(f"w-full border-b text-sm items-center py-1 px-2 {bg}"):
                        # Checkbox
                        ui.checkbox(
                            value=is_selected,
                            on_change=lambda e, pid=p.id: self._on_check(pid, e.value)
                        ).props("dense").classes("w-8")
                        
                        # Name
                        ui.label(p.full_name).classes("w-36 truncate")
                        
                        # Phone
                        ui.label(p.phone or "—").classes("w-28 truncate text-gray-600")
                        
                        # Email
                        ui.label(p.email or "—").classes("w-40 truncate text-gray-600")
                        
                        # City
                        ui.label(p.city or "—").classes("w-28 truncate")
                        
                        # Currency
                        ui.label(p.preferred_currency).classes("w-12 text-center")
                        
                        # Gothra
                        ui.label(p.gothra or "—").classes("w-24 truncate")
                        
                        # Interests
                        interests = ", ".join(p.general_interests[:2]) if p.general_interests else "—"
                        ui.label(interests).classes("w-32 truncate text-gray-500")
                        
                        # Actions
                        with ui.row().classes("w-16 gap-0"):
                            ui.button(
                                icon="edit",
                                on_click=lambda pid=p.id: self._show_edit_dialog(pid)
                            ).props("flat dense round size=sm").classes("text-blue-500")
                            ui.button(
                                icon="delete",
                                on_click=lambda pid=p.id, name=p.full_name: self._confirm_delete(pid, name)
                            ).props("flat dense round size=sm").classes("text-red-400")
    
    def _on_check(self, person_id: int, checked: bool):
        if checked:
            self.selected_ids.add(person_id)
        else:
            self.selected_ids.discard(person_id)
        self._update_selection_ui()
    
    def _delete_selected(self):
        if not self.selected_ids:
            return
        
        count = len(self.selected_ids)
        with ui.dialog() as dialog, ui.card().classes("p-4"):
            ui.label(f"Delete {count} person(s)?").classes("font-bold")
            ui.label("This cannot be undone.").classes("text-sm text-gray-500")
            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                def do_delete():
                    for pid in list(self.selected_ids):
                        self.crm.delete_person(pid)
                    self.selected_ids.clear()
                    dialog.close()
                    self._load_all()
                    ui.notify(f"Deleted {count} person(s)")
                ui.button("Delete", on_click=do_delete).props("color=red")
        dialog.open()
    
    def _confirm_delete(self, person_id: int, name: str):
        with ui.dialog() as dialog, ui.card().classes("p-4"):
            ui.label(f"Delete {name}?").classes("font-bold")
            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                def do_delete():
                    self.crm.delete_person(person_id)
                    self.selected_ids.discard(person_id)
                    dialog.close()
                    self._load_all()
                    ui.notify(f"Deleted {name}")
                ui.button("Delete", on_click=do_delete).props("color=red")
        dialog.open()
    
    def _show_add_dialog(self):
        self._show_person_dialog(PersonProfile(), is_new=True)
    
    def _show_edit_dialog(self, person_id: int):
        person = self.crm.get_person(person_id)
        if person:
            self._show_person_dialog(person, is_new=False)
    
    def _show_person_dialog(self, person: PersonProfile, is_new: bool):
        with ui.dialog() as dialog, ui.card().classes("w-[550px] p-4"):
            ui.label("Add Person" if is_new else f"Edit {person.full_name}").classes("text-lg font-bold mb-3")
            
            with ui.scroll_area().classes("h-[380px] pr-2"):
                with ui.column().classes("w-full gap-3"):
                    # Basic
                    ui.label("Basic Info").classes("text-xs font-bold text-gray-500 uppercase")
                    with ui.row().classes("w-full gap-2"):
                        first_name = ui.input("First Name *", value=person.first_name).props("dense outlined").classes("flex-1")
                        last_name = ui.input("Last Name", value=person.last_name).props("dense outlined").classes("flex-1")
                    with ui.row().classes("w-full gap-2"):
                        gender_val = person.gender if person.gender in self.GENDERS else None
                        gender = ui.select(self.GENDERS, label="Gender", value=gender_val).props("dense outlined").classes("w-32")
                        age = ui.number("Age", value=person.age, min=0, max=150).props("dense outlined").classes("w-20")
                    
                    # Contact
                    ui.label("Contact").classes("text-xs font-bold text-gray-500 uppercase mt-2")
                    with ui.row().classes("w-full gap-2"):
                        phone = ui.input("Phone", value=person.phone).props("dense outlined").classes("flex-1")
                        email = ui.input("Email", value=person.email).props("dense outlined").classes("flex-1")
                    currency_val = person.preferred_currency if person.preferred_currency in self.CURRENCIES else "USD"
                    currency = ui.select(self.CURRENCIES, label="Currency", value=currency_val).props("dense outlined").classes("w-40")
                    
                    # Location
                    ui.label("Location").classes("text-xs font-bold text-gray-500 uppercase mt-2")
                    with ui.row().classes("w-full gap-2"):
                        city = ui.input("City", value=person.city).props("dense outlined").classes("flex-1")
                        state = ui.input("State", value=person.state).props("dense outlined").classes("flex-1")
                        country = ui.input("Country", value=person.country).props("dense outlined").classes("flex-1")
                    
                    # Cultural
                    ui.label("Cultural").classes("text-xs font-bold text-gray-500 uppercase mt-2")
                    with ui.row().classes("w-full gap-2"):
                        gothra = ui.input("Gothra", value=person.gothra).props("dense outlined").classes("flex-1")
                        nakshatra = ui.input("Nakshatra", value=person.nakshatra).props("dense outlined").classes("flex-1")
                    
                    # Interests
                    ui.label("Interests").classes("text-xs font-bold text-gray-500 uppercase mt-2")
                    interests_str = ", ".join(person.general_interests) if person.general_interests else ""
                    interests = ui.input("Interests (comma-separated)", value=interests_str).props("dense outlined").classes("w-full")
                    
                    temples_str = ""
                    if person.temple_interests:
                        temples_str = "\n".join([f"{t.get('name','')}, {t.get('location','')}, {t.get('deity','')}" for t in person.temple_interests])
                    temples = ui.textarea("Temples (name, location, deity per line)", value=temples_str).props("dense outlined rows=2").classes("w-full")
                    
                    notes = ui.textarea("Notes", value=person.notes).props("dense outlined rows=2").classes("w-full")
            
            with ui.row().classes("w-full justify-between mt-4"):
                if not is_new:
                    ui.button("Delete", on_click=lambda: self._delete_from_dialog(person.id, person.full_name, dialog)).props("flat color=red")
                else:
                    ui.label("")
                with ui.row().classes("gap-2"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    def save():
                        if not first_name.value:
                            ui.notify("First name required", type="warning")
                            return
                        temple_list = []
                        if temples.value:
                            for line in temples.value.strip().split("\n"):
                                parts = [p.strip() for p in line.split(",")]
                                if parts and parts[0]:
                                    temple_list.append({"name": parts[0], "location": parts[1] if len(parts) > 1 else "", "deity": parts[2] if len(parts) > 2 else ""})
                        data = {
                            "first_name": first_name.value,
                            "last_name": last_name.value or "",
                            "gender": gender.value or "",
                            "age": int(age.value) if age.value else None,
                            "phone": phone.value or "",
                            "email": email.value or "",
                            "preferred_currency": currency.value or "USD",
                            "city": city.value or "",
                            "state": state.value or "",
                            "country": country.value or "",
                            "gothra": gothra.value or "",
                            "nakshatra": nakshatra.value or "",
                            "general_interests": [i.strip() for i in interests.value.split(",") if i.strip()],
                            "temple_interests": temple_list,
                            "notes": notes.value or ""
                        }
                        if is_new:
                            self.crm.add_person(PersonProfile(**data))
                            ui.notify(f"Added {first_name.value}")
                        else:
                            self.crm.update_person(person.id, **data)
                            ui.notify(f"Updated {first_name.value}")
                        dialog.close()
                        self._load_all()
                    ui.button("Save", on_click=save).props("color=primary")
        dialog.open()
    
    def _delete_from_dialog(self, person_id: int, name: str, parent_dialog):
        self.crm.delete_person(person_id)
        ui.notify(f"Deleted {name}")
        parent_dialog.close()
        self._load_all()
