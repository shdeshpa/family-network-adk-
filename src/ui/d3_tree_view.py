"""D3.js Family Tree Visualization."""

from nicegui import ui
from typing import Optional
import json

from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph


class D3TreeView:
    """Interactive family tree using D3.js force-directed graph."""

    def __init__(
        self,
        crm_store: CRMStoreV2 = None,
        family_registry: FamilyRegistry = None,
        person_store: PersonStore = None,
        family_graph: FamilyGraph = None,
        on_node_click=None
    ):
        # CRM V2 stores for person data
        self.crm_store = crm_store or CRMStoreV2()
        self.family_registry = family_registry or FamilyRegistry()
        # GraphLite for relationships
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
        self.on_node_click = on_node_click
        self.person_dialog = None

    def render(self):
        """Render the D3.js tree view."""
        # Get persons from CRM V2
        persons = self.crm_store.get_all()
        print(f"[D3TreeView] render() called - found {len(persons)} persons")

        if not persons:
            ui.label("No family data yet. Add persons using Text Input or Record tabs.").classes("text-gray-500 p-8")
            return

        # Get unique locations for filters
        cities = set()
        states = set()
        for p in persons:
            if not p.is_archived:
                # Try to get location from GraphLite
                matches = self.person_store.find_by_name(p.full_name)
                if matches and matches[0].location:
                    loc = matches[0].location
                    # Parse location (e.g., "Mumbai, Maharashtra" or "Seattle")
                    parts = [part.strip() for part in loc.split(',')]
                    if len(parts) >= 2:
                        cities.add(parts[0])
                        states.add(parts[1])
                    elif len(parts) == 1 and parts[0]:
                        cities.add(parts[0])

        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1").style("min-width: 1200px"):
                # Toolbar
                with ui.row().classes("w-full justify-between items-center mb-2"):
                    ui.label("🌳 Family Tree (D3.js)").classes("text-lg font-bold")
                    with ui.row().classes("gap-2"):
                        ui.html('<button onclick="if(window.resetD3View) window.resetD3View()" class="q-btn q-btn-item non-selectable no-outline q-btn--flat q-btn--rectangle q-btn-padding text-primary q-btn--dense" style="font-size: 0.875rem;">🔍 Reset View</button>', sanitize=False)
                        ui.button("🔄 Refresh Data", on_click=lambda: ui.navigate.reload()).props("dense flat size=sm")

                # Filters
                if cities or states:
                    with ui.expansion("🔍 Filters", icon="filter_list").classes("w-full mb-2"):
                        with ui.row().classes("gap-4"):
                            if cities:
                                with ui.column():
                                    ui.label("Filter by City:").classes("text-sm font-bold")
                                    city_select = ui.select(
                                        options=["All Cities"] + sorted(list(cities)),
                                        value="All Cities",
                                        on_change=lambda e: ui.run_javascript(f'if(window.filterByLocation) window.filterByLocation("city", "{e.value}")')
                                    ).props("dense").classes("w-48")
                            if states:
                                with ui.column():
                                    ui.label("Filter by State:").classes("text-sm font-bold")
                                    state_select = ui.select(
                                        options=["All States"] + sorted(list(states)),
                                        value="All States",
                                        on_change=lambda e: ui.run_javascript(f'if(window.filterByLocation) window.filterByLocation("state", "{e.value}")')
                                    ).props("dense").classes("w-48")

                # Build graph data
                graph_data = self._build_graph_data(persons)
                print(f"[D3TreeView] graph_data = {graph_data[:200]}...")  # First 200 chars

                # D3 container with tooltip
                ui.html('''
                <style>
                #d3-tooltip {
                    position: absolute;
                    padding: 12px;
                    background: white;
                    border: 2px solid #3b82f6;
                    border-radius: 8px;
                    pointer-events: none;
                    opacity: 0;
                    transition: opacity 0.2s;
                    font-size: 13px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    z-index: 1000;
                }
                #d3-tooltip .tooltip-header {
                    font-weight: bold;
                    margin-bottom: 8px;
                    padding-bottom: 6px;
                    border-bottom: 1px solid #e5e7eb;
                    color: #1f2937;
                }
                #d3-tooltip .tooltip-row {
                    margin: 4px 0;
                    color: #4b5563;
                }
                #d3-tooltip .tooltip-label {
                    font-weight: 600;
                    color: #374151;
                }
                </style>
                <div id="d3-tooltip"></div>
                <div id="d3-tree-container" style="width:100%;min-width:1200px;height:900px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;position:relative;"></div>
                ''', sanitize=False)

                # Add D3.js library
                ui.add_head_html('<script src="https://d3js.org/d3.v7.min.js"></script>')

                # Add D3 visualization script
                d3_script = f'''
                <script>
                (function initD3Tree() {{
                    if (typeof d3 === 'undefined') {{
                        console.log('D3 not loaded yet, retrying...');
                        setTimeout(initD3Tree, 100);
                        return;
                    }}

                    const container = document.getElementById('d3-tree-container');
                    if (!container) {{
                        console.log('Container not found, retrying...');
                        setTimeout(initD3Tree, 100);
                        return;
                    }}

                    console.log('Initializing D3 Tree...');

                    const data = {graph_data};
                    console.log('Graph data:', data);
                    console.log('Nodes:', data.nodes.length, 'Links:', data.links.length);

                    // Clear any existing SVG
                    d3.select(container).selectAll('*').remove();

                    const width = container.clientWidth;
                    const height = container.clientHeight;
                    console.log('Container dimensions:', width, 'x', height);

                    const svg = d3.select(container)
                        .append('svg')
                        .attr('width', width)
                        .attr('height', height)
                        .attr('viewBox', [0, 0, width, height]);

                    // Add zoom and pan functionality
                    const g = svg.append('g');

                    const zoom = d3.zoom()
                        .scaleExtent([0.1, 4])
                        .on('zoom', (event) => {{
                            g.attr('transform', event.transform);
                        }});

                    svg.call(zoom);

                    // Expose reset view function
                    window.resetD3View = () => {{
                        svg.transition().duration(750).call(
                            zoom.transform,
                            d3.zoomIdentity.translate(0, 0).scale(1)
                        );
                    }};

                    // Create arrow markers for parent-child relationships
                    svg.append('defs').selectAll('marker')
                        .data(['parent_child'])
                        .join('marker')
                        .attr('id', d => `arrow-${{d}}`)
                        .attr('viewBox', '0 -5 10 10')
                        .attr('refX', 20)
                        .attr('refY', 0)
                        .attr('markerWidth', 6)
                        .attr('markerHeight', 6)
                        .attr('orient', 'auto')
                        .append('path')
                        .attr('fill', '#93c5fd')
                        .attr('d', 'M0,-5L10,0L0,5');

                    // Create force simulation
                    const simulation = d3.forceSimulation(data.nodes)
                        .force('link', d3.forceLink(data.links)
                            .id(d => d.id)
                            .distance(d => {{
                                if (d.type === 'spouse') return 80;
                                if (d.type === 'parent_child') return 150;
                                if (d.type === 'sibling') return 120;
                                return 100;
                            }}))
                        .force('charge', d3.forceManyBody().strength(-500))
                        .force('center', d3.forceCenter(width / 2, height / 2))
                        .force('collision', d3.forceCollide().radius(50))
                        .force('x', d3.forceX(width / 2).strength(0.05))
                        .force('y', d3.forceY(height / 2).strength(0.05));

                    // Create links
                    const link = g.append('g')
                        .selectAll('line')
                        .data(data.links)
                        .join('line')
                        .attr('stroke', d => {{
                            if (d.type === 'spouse') return '#f9a8d4';
                            if (d.type === 'parent_child') return '#93c5fd';
                            if (d.type === 'sibling') return '#c4b5fd';
                            if (d.type === 'friend_of') return '#fbbf24';
                            if (d.type === 'colleague') return '#a78bfa';
                            if (d.type === 'mentor') return '#34d399';
                            return '#d1d5db';
                        }})
                        .attr('stroke-width', 2)
                        .attr('stroke-dasharray', d => d.type === 'spouse' ? '5,5' : d.type === 'sibling' ? '2,2' : '0')
                        .attr('marker-end', d => d.type === 'parent_child' ? 'url(#arrow-parent_child)' : null);

                    // Create nodes
                    const node = g.append('g')
                        .selectAll('g')
                        .data(data.nodes)
                        .join('g')
                        .call(d3.drag()
                            .on('start', dragstarted)
                            .on('drag', dragged)
                            .on('end', dragended));

                    // Custom tooltip element
                    const tooltip = d3.select('#d3-tooltip');

                    // Add circles for nodes
                    node.append('circle')
                        .attr('r', 20)
                        .attr('fill', d => d.gender === 'M' ? '#60a5fa' : d.gender === 'F' ? '#f472b6' : '#9ca3af')
                        .attr('stroke', d => d.gender === 'M' ? '#2563eb' : d.gender === 'F' ? '#db2777' : '#6b7280')
                        .attr('stroke-width', 2)
                        .style('cursor', 'pointer')
                        .on('click', function(event, d) {{
                            event.stopPropagation();
                            console.log('Node clicked:', d);
                            // Trigger Python callback via global function
                            if (window.onD3NodeClick) {{
                                window.onD3NodeClick(d.personId, d.label);
                            }}
                        }})
                        .on('mouseover', function(event, d) {{
                            d3.select(this).attr('r', 25);

                            // Build tooltip content
                            const genderText = d.gender === 'M' ? 'Male' : d.gender === 'F' ? 'Female' : 'Unknown';
                            let tooltipHTML = `<div class="tooltip-header">${{d.label}}</div>`;

                            if (d.phone) {{
                                tooltipHTML += `<div class="tooltip-row"><span class="tooltip-label">Phone:</span> ${{d.phone}}</div>`;
                            }}
                            if (d.city) {{
                                tooltipHTML += `<div class="tooltip-row"><span class="tooltip-label">City:</span> ${{d.city}}</div>`;
                            }}
                            if (d.state) {{
                                tooltipHTML += `<div class="tooltip-row"><span class="tooltip-label">State:</span> ${{d.state}}</div>`;
                            }}
                            tooltipHTML += `<div class="tooltip-row"><span class="tooltip-label">Gender:</span> ${{genderText}}</div>`;

                            tooltip.html(tooltipHTML)
                                .style('left', (event.pageX + 15) + 'px')
                                .style('top', (event.pageY - 15) + 'px')
                                .style('opacity', 1);
                        }})
                        .on('mousemove', function(event) {{
                            tooltip
                                .style('left', (event.pageX + 15) + 'px')
                                .style('top', (event.pageY - 15) + 'px');
                        }})
                        .on('mouseout', function() {{
                            d3.select(this).attr('r', 20);
                            tooltip.style('opacity', 0);
                        }});

                    // Add labels
                    node.append('text')
                        .text(d => d.label)
                        .attr('x', 0)
                        .attr('y', 35)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '11px')
                        .attr('font-weight', 'bold')
                        .attr('fill', '#1f2937');

                    console.log('Created', node.size(), 'node groups and', link.size(), 'links');

                    // Update positions on tick
                    simulation.on('tick', () => {{
                        link
                            .attr('x1', d => d.source.x)
                            .attr('y1', d => d.source.y)
                            .attr('x2', d => d.target.x)
                            .attr('y2', d => d.target.y);

                        node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
                    }});

                    // Drag functions
                    function dragstarted(event) {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        event.subject.fx = event.subject.x;
                        event.subject.fy = event.subject.y;
                    }}

                    function dragged(event) {{
                        event.subject.fx = event.x;
                        event.subject.fy = event.y;
                    }}

                    function dragended(event) {{
                        if (!event.active) simulation.alphaTarget(0);
                        event.subject.fx = null;
                        event.subject.fy = null;
                    }}

                    // Filtering function
                    let currentCityFilter = 'All Cities';
                    let currentStateFilter = 'All States';

                    window.filterByLocation = (filterType, value) => {{
                        if (filterType === 'city') {{
                            currentCityFilter = value;
                        }} else if (filterType === 'state') {{
                            currentStateFilter = value;
                        }}

                        node.style('opacity', d => {{
                            const cityMatch = currentCityFilter === 'All Cities' || d.city === currentCityFilter;
                            const stateMatch = currentStateFilter === 'All States' || d.state === currentStateFilter;
                            return (cityMatch && stateMatch) ? 1 : 0.1;
                        }});

                        node.selectAll('text').style('opacity', d => {{
                            const cityMatch = currentCityFilter === 'All Cities' || d.city === currentCityFilter;
                            const stateMatch = currentStateFilter === 'All States' || d.state === currentStateFilter;
                            return (cityMatch && stateMatch) ? 1 : 0.1;
                        }});

                        // Also dim links connected to filtered nodes
                        link.style('opacity', d => {{
                            const sourceCityMatch = currentCityFilter === 'All Cities' || d.source.city === currentCityFilter;
                            const sourceStateMatch = currentStateFilter === 'All States' || d.source.state === currentStateFilter;
                            const targetCityMatch = currentCityFilter === 'All Cities' || d.target.city === currentCityFilter;
                            const targetStateMatch = currentStateFilter === 'All States' || d.target.state === currentStateFilter;

                            const sourceVisible = sourceCityMatch && sourceStateMatch;
                            const targetVisible = targetCityMatch && targetStateMatch;

                            return (sourceVisible && targetVisible) ? 1 : 0.1;
                        }});

                        console.log('Filtered by', filterType, ':', value);
                    }};

                    console.log('D3 Tree initialized successfully!');
                }})();
                </script>
                '''
                ui.add_body_html(d3_script)

                # Register JavaScript callback for node clicks
                # Create a bridge using JavaScript to store clicks and Python timer to poll
                ui.run_javascript('''
                window.clickedPersonId = null;
                window.onD3NodeClick = function(personId, personName) {
                    console.log('Node clicked - person ID:', personId);
                    window.clickedPersonId = personId;
                };
                ''')

                # Create a timer that checks for clicks
                async def poll_for_clicks():
                    person_id = await ui.run_javascript('window.clickedPersonId', timeout=0.5)
                    if person_id:
                        await ui.run_javascript('window.clickedPersonId = null')
                        self._show_person_details(person_id)

                ui.timer(0.2, poll_for_clicks)

            # Legend
            with ui.card().classes("w-64 p-4"):
                ui.label("Legend").classes("font-bold mb-3")
                with ui.column().classes("gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:20px;height:20px;background:#60a5fa;border:2px solid #2563eb;border-radius:50%;"></div>', sanitize=False)
                        ui.label("Male")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:20px;height:20px;background:#f472b6;border:2px solid #db2777;border-radius:50%;"></div>', sanitize=False)
                        ui.label("Female")

                    ui.separator()

                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#93c5fd;"></div>', sanitize=False)
                        ui.label("Parent-Child").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#f9a8d4;border-top:2px dashed #f9a8d4;"></div>', sanitize=False)
                        ui.label("Spouse").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#c4b5fd;border-top:2px dotted #c4b5fd;"></div>', sanitize=False)
                        ui.label("Sibling").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#fbbf24;"></div>', sanitize=False)
                        ui.label("Friend").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#a78bfa;"></div>', sanitize=False)
                        ui.label("Colleague").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#34d399;"></div>', sanitize=False)
                        ui.label("Mentor").classes("text-sm")
                    with ui.row().classes("items-center gap-2"):
                        ui.html('<div style="width:40px;height:2px;background:#d1d5db;"></div>', sanitize=False)
                        ui.label("Other").classes("text-sm")

                    ui.separator()

                    ui.label("Controls").classes("font-bold mb-2")
                    ui.label("• Drag nodes to reposition").classes("text-xs text-gray-600")
                    ui.label("• Scroll to zoom in/out").classes("text-xs text-gray-600")
                    ui.label("• Click & drag canvas to pan").classes("text-xs text-gray-600")
                    ui.label("• Click 'Reset View' to center").classes("text-xs text-gray-600")

    def _show_person_details(self, person_id: int):
        """Show person details dialog with tabs."""
        # Get person from CRM
        person = self.crm_store.get_person(person_id)
        if not person:
            ui.notify(f"Person with ID {person_id} not found", type="negative")
            return

        # Close existing dialog if any
        if self.person_dialog:
            self.person_dialog.close()

        # Create new dialog
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
            self.person_dialog = dialog

            # Header
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label(f"👤 {person.full_name}").classes("text-2xl font-bold")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            # Tabs
            with ui.tabs().classes("w-full") as tabs:
                details_tab = ui.tab("Personal Info", icon="person")
                relationships_tab = ui.tab("Relationships", icon="people")
                donations_tab = ui.tab("Donations", icon="volunteer_activism")

            with ui.tab_panels(tabs, value=details_tab).classes("w-full"):
                # Personal Info Tab
                with ui.tab_panel(details_tab):
                    with ui.grid(columns=2).classes("gap-4 w-full"):
                        # Left column
                        with ui.column().classes("gap-2"):
                            if person.gender:
                                self._detail_row("Gender", "Male" if person.gender == "M" else "Female" if person.gender == "F" else person.gender)
                            if person.phone:
                                self._detail_row("Phone", person.phone)
                            if person.email:
                                self._detail_row("Email", person.email)
                            if person.family_code:
                                self._detail_row("Family", person.family_code)

                        # Right column
                        with ui.column().classes("gap-2"):
                            # Get location from GraphLite
                            matches = self.person_store.find_by_name(person.full_name)
                            if matches and matches[0].location:
                                self._detail_row("Location", matches[0].location)
                            if person.gothra:
                                self._detail_row("Gothra", person.gothra)
                            if person.nakshatra:
                                self._detail_row("Nakshatra", person.nakshatra)

                    # Religious Interests & Hobbies
                    if person.religious_interests or person.hobbies:
                        ui.separator().classes("my-4")
                        with ui.grid(columns=1).classes("gap-2 w-full"):
                            if person.religious_interests:
                                self._detail_row("Religious Interests", person.religious_interests)
                            if person.hobbies:
                                self._detail_row("Hobbies", person.hobbies)

                # Relationships Tab
                with ui.tab_panel(relationships_tab):
                    relationships = self.crm_store.get_relationships(person_id)

                    if not relationships:
                        ui.label("No relationships found").classes("text-gray-500 p-4")
                    else:
                        # Build relationships table data
                        rel_rows = []
                        for rel in relationships:
                            # Determine other person ID
                            if rel['person1_id'] == person_id:
                                other_id = rel['person2_id']
                            else:
                                other_id = rel['person1_id']

                            # Look up the other person's name
                            other_person = self.crm_store.get_person(other_id)
                            other_name = other_person.full_name if other_person else f"Person {other_id}"

                            rel_rows.append({
                                'name': other_name,
                                'relation': rel.get('relation_term', rel['relation_type']),
                                'type': rel['relation_type']
                            })

                        # Create table
                        ui.table(
                            columns=[
                                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
                                {'name': 'relation', 'label': 'Relation', 'field': 'relation', 'align': 'left'},
                                {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left'}
                            ],
                            rows=rel_rows
                        ).classes("w-full")

                # Donations Tab
                with ui.tab_panel(donations_tab):
                    ui.label("Donation tracking coming soon...").classes("text-gray-500 p-4")
                    # Placeholder for future donation functionality

        dialog.open()

    def _detail_row(self, label: str, value: str):
        """Helper to create a detail row."""
        with ui.row().classes("items-center gap-2"):
            ui.label(f"{label}:").classes("font-semibold text-gray-700 min-w-32")
            ui.label(value).classes("text-gray-900")

    def _build_graph_data(self, persons) -> str:
        """
        Build D3.js graph data (nodes and links).

        Returns JSON string with format:
        {
            "nodes": [{"id": "p1", "label": "John", "gender": "M", "personId": 1}, ...],
            "links": [{"source": "p1", "target": "p2", "type": "spouse"}, ...]
        }
        """
        nodes = []
        links = []
        added_links = set()

        # Build CRM ID -> GraphLite ID mapping by name
        crm_to_graph_id = {}
        for p in persons:
            if p.is_archived:
                continue
            # Find in GraphLite by name
            matches = self.person_store.find_by_name(p.full_name)
            if matches:
                crm_to_graph_id[p.id] = matches[0].id

        # Build nodes from CRM V2 persons
        for p in persons:
            if p.is_archived:
                continue

            # Get location from GraphLite
            city = ""
            state = ""
            location = ""
            matches = self.person_store.find_by_name(p.full_name)
            if matches and matches[0].location:
                location = matches[0].location
                parts = [part.strip() for part in location.split(',')]
                if len(parts) >= 2:
                    city = parts[0]
                    state = parts[1]
                elif len(parts) == 1:
                    city = parts[0]

            nodes.append({
                "id": f"p{p.id}",
                "personId": p.id,
                "label": p.full_name,
                "gender": p.gender or "",
                "city": city,
                "state": state,
                "location": location,
                "phone": p.phone or "",
                "email": p.email or ""
            })

        # Add links from GraphLite relationships
        for p in persons:
            if p.is_archived:
                continue

            graph_id = crm_to_graph_id.get(p.id)
            if not graph_id:
                continue

            try:
                # Get children
                children_graph_ids = self.family_graph.get_children(graph_id)
                for child_graph_id in children_graph_ids:
                    child_crm_id = self._find_crm_id_by_graph_id(child_graph_id, crm_to_graph_id)
                    if child_crm_id:
                        key = (p.id, child_crm_id, "pc")
                        if key not in added_links:
                            links.append({
                                "source": f"p{p.id}",
                                "target": f"p{child_crm_id}",
                                "type": "parent_child"
                            })
                            added_links.add(key)
            except Exception:
                pass

            try:
                # Get spouses
                spouses_graph_ids = self.family_graph.get_spouse(graph_id)
                for spouse_graph_id in spouses_graph_ids:
                    spouse_crm_id = self._find_crm_id_by_graph_id(spouse_graph_id, crm_to_graph_id)
                    if spouse_crm_id:
                        key = tuple(sorted([p.id, spouse_crm_id])) + ("sp",)
                        if key not in added_links:
                            links.append({
                                "source": f"p{p.id}",
                                "target": f"p{spouse_crm_id}",
                                "type": "spouse"
                            })
                            added_links.add(key)
            except Exception:
                pass

            try:
                # Get siblings
                siblings_graph_ids = self.family_graph.get_siblings(graph_id)
                for sibling_graph_id in siblings_graph_ids:
                    sibling_crm_id = self._find_crm_id_by_graph_id(sibling_graph_id, crm_to_graph_id)
                    if sibling_crm_id:
                        key = tuple(sorted([p.id, sibling_crm_id])) + ("sib",)
                        if key not in added_links:
                            links.append({
                                "source": f"p{p.id}",
                                "target": f"p{sibling_crm_id}",
                                "type": "sibling"
                            })
                            added_links.add(key)
            except Exception:
                pass

        # Add custom relationships from CRM V2 (friend_of, colleague, etc.)
        for p in persons:
            if p.is_archived:
                continue

            try:
                crm_relationships = self.crm_store.get_relationships(p.id)
                for rel in crm_relationships:
                    # Skip if this is a standard family relationship already handled
                    if rel['relation_type'] in ['parent_child', 'spouse', 'sibling']:
                        continue

                    # Determine source and target
                    if rel['person1_id'] == p.id:
                        other_id = rel['person2_id']
                    else:
                        other_id = rel['person1_id']

                    # Create unique key for this relationship
                    key = tuple(sorted([p.id, other_id])) + (rel['relation_type'],)
                    if key not in added_links:
                        links.append({
                            "source": f"p{p.id}",
                            "target": f"p{other_id}",
                            "type": rel['relation_type'],
                            "label": rel.get('relation_term', rel['relation_type'])
                        })
                        added_links.add(key)
            except Exception as e:
                print(f"[D3TreeView] Error getting CRM relationships for {p.full_name}: {e}")
                pass

        result = {"nodes": nodes, "links": links}
        print(f"[D3TreeView] Built graph: {len(nodes)} nodes, {len(links)} links")
        return json.dumps(result)

    def _find_crm_id_by_graph_id(self, graph_id: int, crm_to_graph_map: dict) -> Optional[int]:
        """Find CRM V2 ID given GraphLite ID."""
        for crm_id, gid in crm_to_graph_map.items():
            if gid == graph_id:
                return crm_id
        return None
