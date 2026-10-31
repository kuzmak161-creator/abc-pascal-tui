"""Файловый менеджер проектов."""
from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView

from ..files import list_dir
from ..i18n import tr


class FileItem(ListItem):
    def __init__(self, name: str, is_dir: bool, active: bool = False):
        marker = "▶" if active else " "
        icon = "📁" if is_dir else "📄"
        super().__init__(Label(f"{marker}{icon} {name}", markup=False))
        self.filename = name
        self.is_dir = is_dir


class FileMenuScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close", show=False)]

    CSS = """
    FileMenuScreen { align: center middle; background: rgba(0, 0, 0, 0.5); }
    #menu_container { width: 60; max-width: 98%; height: 90%; background: $panel; border: thick $primary; padding: 1; }
    #search_input { margin-bottom: 1; }
    #menu_file_list { background: $surface; border: solid $primary; height: 1fr; margin-bottom: 1; }
    .menu_btn { width: 100%; margin-bottom: 1; }
    .btn_row { height: 3; margin-bottom: 1; }
    .half_btn { width: 50%; margin-right: 1; }
    """

    def __init__(self, root_dir: str, lang: str, current_file: str = "", new_tab: bool = False):
        super().__init__()
        self._lang = lang
        self._root = root_dir
        self._current_dir = root_dir
        self._current_file = os.path.basename(current_file) if current_file else ""
        self._new_tab = new_tab

    def compose(self) -> ComposeResult:
        L = self._lang
        with Vertical(id="menu_container"):
            yield Label(tr(L, "menu_title"))
            yield Input(placeholder=tr(L, "menu_search_ph"), id="search_input")
            yield ListView(id="menu_file_list")

            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "menu_up"), variant="default", id="menu_up_btn", classes="half_btn")
                yield Button(tr(L, "menu_new"), variant="primary", id="menu_create_file_btn", classes="half_btn")
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "menu_new_dir"), variant="success", id="menu_create_dir_btn", classes="half_btn")
                yield Button(tr(L, "menu_copy"), variant="default", id="menu_copy_btn", classes="half_btn")
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "menu_rename"), variant="warning", id="menu_rename_btn", classes="half_btn")
                yield Button(tr(L, "menu_delete"), variant="error", id="menu_delete_btn", classes="half_btn")
            with Horizontal(classes="btn_row"):
                yield Button(tr(L, "btn_clear"), variant="error", id="menu_clear_btn", classes="half_btn")
                yield Button(tr(L, "btn_undo"), variant="warning", id="menu_undo_btn", classes="half_btn")
            yield Button(tr(L, "menu_close"), variant="default", id="menu_close_btn", classes="menu_btn")

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self, query: str = "") -> None:
        items = list_dir(self._current_dir)
        filtered = [i for i in items if query in i[0].lower()] if query else items

        file_list = self.query_one("#menu_file_list", ListView)
        file_list.clear()
        for name, is_dir in filtered:
            active = (name == self._current_file and not is_dir)
            file_list.append(FileItem(name, is_dir, active))
        if filtered:
            file_list.index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search_input":
            self._rebuild_list(event.value.lower().strip())

    def _highlighted_item(self) -> tuple[str, bool] | None:
        child = self.query_one("#menu_file_list", ListView).highlighted_child
        if isinstance(child, FileItem):
            return child.filename, child.is_dir
        return None

    def _relpath(self, name: str) -> str:
        return os.path.relpath(os.path.join(self._current_dir, name), self._root)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, FileItem):
            if event.item.is_dir:
                self._current_dir = os.path.join(self._current_dir, event.item.filename)
                self._current_file = ""
                self.query_one("#search_input", Input).value = ""
                self._rebuild_list()
            else:
                self.dismiss(("select", self._relpath(event.item.filename), self._new_tab))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        item = self._highlighted_item()

        if bid == "menu_close_btn":
            self.dismiss(None)
        elif bid == "menu_up_btn":
            if os.path.normpath(self._current_dir) != os.path.normpath(self._root):
                self._current_dir = os.path.dirname(self._current_dir)
                self._current_file = ""
                self.query_one("#search_input", Input).value = ""
                self._rebuild_list()
        elif bid == "menu_create_file_btn":
            self.dismiss(("create_file", os.path.relpath(self._current_dir, self._root), self._new_tab))
        elif bid == "menu_create_dir_btn":
            self.dismiss(("create_dir", os.path.relpath(self._current_dir, self._root), self._new_tab))
        elif bid == "menu_clear_btn":
            self.dismiss(("clear", None, self._new_tab))
        elif bid == "menu_undo_btn":
            self.dismiss(("undo", None, self._new_tab))
        elif bid in ("menu_delete_btn", "menu_rename_btn", "menu_copy_btn") and item:
            name, is_dir = item
            action = {"menu_delete_btn": "delete", "menu_rename_btn": "rename", "menu_copy_btn": "copy"}[bid]
            self.dismiss((f"{action}_{'dir' if is_dir else 'file'}", self._relpath(name), self._new_tab))

    def action_close(self) -> None:
        self.dismiss(None)