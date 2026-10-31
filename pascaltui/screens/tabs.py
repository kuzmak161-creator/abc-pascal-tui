"""Вкладки редактора: TabbedContent + маленькая кнопка «+».

Вкладка определяется ПОЛНЫМ путём файла (а не именем): два main.pas из разных папок —
это две разные вкладки, и ни одна не затирает другую.
"""
from __future__ import annotations

import hashlib
import os

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, TabbedContent, TabPane

from ..completions import CompletionEngine
from ..editor import CodeEditor, CompletionPopup


def norm_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def tab_id_for(path: str) -> str:
    """Допустимый id вкладки для Textual: латиница/цифры, начинается с буквы.

    Имя файла в id использовать нельзя: кириллица, точки и имена вида «1.pas» делают id недопустимым.
    """
    return "t" + hashlib.sha256(norm_path(path).encode("utf-8")).hexdigest()[:12]


def is_inside(path: str, folder: str) -> bool:
    """Лежит ли path внутри folder (или совпадает с ним). «lab1» не считается родителем «lab10»."""
    a, f = norm_path(path), norm_path(folder)
    return a == f or a.startswith(f + os.sep)


class TabBar(Horizontal):
    """Узкая панель с маленькой кнопкой «+» (открывает файловое меню для нового файла)."""

    DEFAULT_CSS = """
    TabBar {
        height: 1;
        margin-bottom: 0;
    }
    TabBar #new_tab_btn {
        width: 3;
        min-width: 3;
        height: 1;
        padding: 0;
        margin: 0;
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("+", variant="success", id="new_tab_btn")


class EditorTabs(TabbedContent):
    """Обёртка над TabbedContent, управляющая редакторами по полному пути файла."""

    def __init__(self, engine: CompletionEngine, settings: dict, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.settings = settings
        self._editors: dict[str, CodeEditor] = {}   # id вкладки -> редактор
        self._paths: dict[str, str] = {}            # id вкладки -> полный путь файла
        self._popup: CompletionPopup | None = None

    def attach_popup(self, popup: CompletionPopup) -> None:
        self._popup = popup
        for editor in self._editors.values():
            editor.attach_popup(popup)

    # ---- состояние ----
    def open_paths(self) -> list[str]:
        return list(self._paths.values())

    def open_editors(self) -> list[tuple[str, CodeEditor]]:
        """[(путь, редактор)] всех открытых вкладок."""
        return [(self._paths[tid], ed) for tid, ed in self._editors.items()]

    def active_path(self) -> str | None:
        return self._paths.get(self.active)

    def get_active_editor(self) -> CodeEditor | None:
        return self._editors.get(self.active)

    def get_active_file_name(self) -> str:
        path = self.active_path()
        return os.path.basename(path) if path else ""

    # ---- открыть / закрыть ----
    def open_file_tab(self, file_path: str, text: str, new_tab: bool = True,
                      label: str | None = None, reload: bool = False) -> None:
        tab_id = tab_id_for(file_path)

        if tab_id in self._editors:  # файл уже открыт — просто переключаемся, правки не теряем
            self.active = tab_id
            if reload:
                self._editors[tab_id].text = text
            return

        if not new_tab and self.active in self._editors:
            self.close_file_tab(self.active)  # заменяем текущую вкладку

        editor = CodeEditor(text, self.engine, self.settings, id=f"editor_{tab_id}")
        editor.attach_popup(self._popup)
        self._editors[tab_id] = editor
        self._paths[tab_id] = os.path.abspath(file_path)

        self.add_pane(TabPane(label or os.path.basename(file_path), editor, id=tab_id))
        self.active = tab_id
        editor.focus()

    def close_file_tab(self, tab_id: str) -> str | None:
        """Закрывает вкладку (без сохранения!). Возвращает путь закрытого файла."""
        if tab_id not in self._editors:
            return None
        path = self._paths.pop(tab_id, None)
        del self._editors[tab_id]
        self.remove_pane(tab_id)
        return path

    def close_under(self, path: str) -> list[str]:
        """Закрывает вкладки файла или всех файлов папки (после удаления/переименования)."""
        closed = []
        for tab_id, tab_path in list(self._paths.items()):
            if is_inside(tab_path, path):
                self.close_file_tab(tab_id)
                closed.append(tab_path)
        return closed

    def close_all(self) -> None:
        for tab_id in list(self._editors):
            self.close_file_tab(tab_id)

    def apply_settings(self, settings: dict, editor_theme: str) -> None:
        self.settings = settings
        for editor in self._editors.values():
            editor.apply_settings(settings, editor_theme)
