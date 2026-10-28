"""Файловый менеджер проектов."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView

from ..files import project_files
from ..i18n import tr


class FileItem(ListItem):
    """Строка списка; хранит имя файла (а не индекс — индексы «уплывают» при поиске)."""

    def __init__(self, filename: str, active: bool = False):
        marker = "▶" if active else " "
        super().__init__(Label(f"{marker}📄 {filename}", markup=False))
        self.filename = filename


class FileMenuScreen(ModalScreen):
    """Результат: (действие, имя_файла | None) или None.

    Действия: select, create, delete, rename, copy, clear, undo.
    """

    BINDINGS = [Binding("escape", "close", "Close", show=False)]

    CSS = """
    FileMenuScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #menu_container {
        width: 48;
        max-width: 98%;
        height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }
    #search_input {
        margin-bottom: 1;
    }
    #menu_file_list {
        background: $surface;
        border: solid $primary;
        height: 1fr;
        margin-bottom: 1;
    }
    .menu_btn {
        width: 100%;
        margin-bottom: 1;
    }
    .btn_row {
        height: 3;
        margin-bottom: 1;
    }
    .half_btn {
        width: 50%;
        margin-right: 1;
    }
    """

    def __init__(self, projects_dir: str, lang: str, current_name: str = ""):
        super().__init__()
        self._lang = lang
        self._current = current_name
        self._all_files = project_files(projects_dir)

    def compose(self) -> ComposeResult:
        L = self._lang
        with Vertical(id="menu_container"):
            yield Label(tr(L, "menu_title"))
            yield Input(placeholder=tr(L, "menu_search_ph"), id="search_input")
            yield ListView(
                *[FileItem(f, f == self._current) for f in self._all_files], id="menu_file_list"
            )
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "menu_new"), variant="primary", id="menu_create_btn", classes="half_btn")
                yield Button(tr(L, "menu_copy"), variant="default", id="menu_copy_btn", classes="half_btn")
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "menu_rename"), variant="warning", id="menu_rename_btn", classes="half_btn")
                yield Button(tr(L, "menu_delete"), variant="error", id="menu_delete_btn", classes="half_btn")
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "btn_clear"), variant="error", id="menu_clear_btn", classes="half_btn")
                yield Button(tr(L, "btn_undo"), variant="warning", id="menu_undo_btn", classes="half_btn")
            yield Button(tr(L, "menu_close"), variant="default", id="menu_close_btn", classes="menu_btn")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search_input":
            return
        query = event.value.lower().strip()
        filtered = [f for f in self._all_files if query in f.lower()] if query else self._all_files

        async def rebuild() -> None:
            file_list = self.query_one("#menu_file_list", ListView)
            await file_list.clear()
            for f in filtered:
                await file_list.append(FileItem(f, f == self._current))

        self.call_after_refresh(rebuild)

    def _highlighted_name(self) -> str | None:
        child = self.query_one("#menu_file_list", ListView).highlighted_child
        return child.filename if isinstance(child, FileItem) else None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, FileItem):
            self.dismiss(("select", event.item.filename))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "menu_close_btn":
            self.dismiss(None)
        elif bid == "menu_create_btn":
            self.dismiss(("create", None))
        elif bid == "menu_clear_btn":
            self.dismiss(("clear", None))
        elif bid == "menu_undo_btn":
            self.dismiss(("undo", None))
        elif bid in ("menu_delete_btn", "menu_rename_btn", "menu_copy_btn"):
            name = self._highlighted_name()
            if name:
                action = {"menu_delete_btn": "delete", "menu_rename_btn": "rename", "menu_copy_btn": "copy"}[bid]
                self.dismiss((action, name))

    def action_close(self) -> None:
        self.dismiss(None)
