"""Simple UI test to verify NiceGUI works."""

from nicegui import ui

ui.label("🏠 Test App - If you see this, NiceGUI works!").classes("text-2xl font-bold")
ui.button("Click me", on_click=lambda: ui.notify("It works!"))

ui.run(title="Test", port=8080, reload=False)
