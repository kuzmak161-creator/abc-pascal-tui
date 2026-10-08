"""Редактор кода: TextArea + автодополнение + автозакрытие скобок + автоотступы."""
from __future__ import annotations

from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.widgets import OptionList, TextArea
from textual.widgets.option_list import Option

from .completions import (
    KIND_MARK,
    Completion,
    CompletionEngine,
    current_prefix,
    expand_snippet,
    leading_indent,
    opens_block,
    scan_context,
)

PAIRS = {"(": ")", "[": "]", "{": "}", "'": "'"}
CLOSERS = {")", "]", "}", "'"}
_SAFE_NEXT = set(")]};,")


class CompletionPopup(OptionList):
    """Панель подсказок под редактором. Не получает фокус — ввод остаётся в редакторе."""

    DEFAULT_CSS = """
    CompletionPopup {
        display: none;
        width: 100%;
        height: auto;
        max-height: 8;
        background: $panel;
        border: round $primary;
        padding: 0 1;
    }
    """
    can_focus = False


class CodeEditor(TextArea):
    BINDINGS = [
        Binding("ctrl+space,ctrl+@,f3", "complete", "Complete", show=False),
    ]

    def __init__(self, text: str, engine: CompletionEngine, settings: dict, language: str | None = "pascal", **kwargs):
        super().__init__(
            text,
            language=language,
            soft_wrap=bool(settings.get("soft_wrap", False)),
            show_line_numbers=bool(settings.get("show_line_numbers", True)),
            tab_behavior="indent" if settings.get("tab_inserts_indent", True) else "focus",
            **kwargs,
        )
        self.engine = engine
        self._s: dict = dict(settings)
        self._popup: CompletionPopup | None = None
        self._items: list[Completion] = []
        self._refresh_pending = False
        self._skip_next = False
        self._force = False
        self._broken = False  # True — подсказки сломались в этой версии Textual, отключены
        self.indent_width = int(settings.get("tab_width", 2))

    # ------------------------------------------------------
    # настройка
    # ------------------------------------------------------
    def attach_popup(self, popup: CompletionPopup) -> None:
        self._popup = popup

    @property
    def unit(self) -> str:
        return " " * int(self._s.get("tab_width", 2))

    def apply_settings(self, settings: dict, editor_theme: str = "css") -> None:
        self._s = dict(settings)
        self.show_line_numbers = bool(settings.get("show_line_numbers", True))
        self.soft_wrap = bool(settings.get("soft_wrap", False))
        self.tab_behavior = "indent" if settings.get("tab_inserts_indent", True) else "focus"
        self.indent_width = int(settings.get("tab_width", 2))
        try:
            self.theme = editor_theme
        except Exception:  # noqa: BLE001 — неизвестная тема редактора
            pass
        if not settings.get("autocomplete", True):
            self.hide_popup()

    # ------------------------------------------------------
    # всплывающий список
    # ------------------------------------------------------
    def _popup_open(self) -> bool:
        return bool(self._popup is not None and self._popup.display)

    def hide_popup(self) -> None:
        if self._popup is not None and self._popup.display:
            self._popup.display = False
        self._items = []

    @staticmethod
    def _render_item(c: Completion) -> Text:
        text = Text()
        text.append(f"{KIND_MARK.get(c.kind, '?')} ", style="dim")
        text.append(c.label)
        if c.detail:
            text.append("  " + c.detail, style="dim italic")
        return text

    def _fit_popup(self, rows: int) -> None:
        if self._popup is not None:
            limit = int(self._s.get("autocomplete_max_items", 8))
            self._popup.styles.max_height = min(rows, limit) + 2

    def _schedule_refresh(self, force: bool = False) -> None:
        self._force = self._force or force
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self.call_after_refresh(self._do_refresh)

    def _do_refresh(self) -> None:
        self._refresh_pending = False
        force, self._force = self._force, False
        if self._broken:
            return
        try:
            self._refresh_inner(force)
        except Exception:  # noqa: BLE001 — не роняем редактор из-за подсказок
            self._broken = True
            try:
                self.hide_popup()
            except Exception:  # noqa: BLE001
                pass

    def _refresh_inner(self, force: bool) -> None:
        if self._skip_next:
            self._skip_next = False
            self.hide_popup()
            return
        s = self._s
        popup = self._popup
        if popup is None or not s.get("autocomplete", True) or self.read_only:
            return
        if not self.has_focus or not self.selection.is_empty:
            self.hide_popup()
            return
        row, col = self.cursor_location
        line = self.document.get_line(row)
        start, prefix = current_prefix(line, col)
        min_chars = 1 if force else int(s.get("autocomplete_min_chars", 2))
        if len(prefix) < min_chars or scan_context(line[:start]) != "code":
            self.hide_popup()
            return
        items = self.engine.suggest(
            prefix,
            self.text if s.get("autocomplete_buffer", True) else "",
            max_items=int(s.get("autocomplete_max_items", 8)),
            use_buffer=bool(s.get("autocomplete_buffer", True)),
            use_snippets=bool(s.get("autocomplete_snippets", True)),
        )
        if not items:
            self.hide_popup()
            return
        self._items = items
        popup.clear_options()
        popup.add_options([Option(self._render_item(c)) for c in items])
        popup.highlighted = 0
        self._fit_popup(len(items))
        popup.display = True

    def action_complete(self) -> None:
        self._schedule_refresh(force=True)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._schedule_refresh()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        self._schedule_refresh()

    def on_blur(self, event: events.Blur) -> None:
        # небольшая задержка: клик по подсказке на миг забирает фокус
        self.set_timer(0.4, self._hide_if_unfocused)

    def _hide_if_unfocused(self) -> None:
        if not self.has_focus:
            self.hide_popup()

    def accept_completion(self, index: int | None) -> None:
        if index is None or not (0 <= index < len(self._items)):
            self.hide_popup()
            return
        item = self._items[index]
        row, col = self.cursor_location
        line = self.document.get_line(row)
        start, _prefix = current_prefix(line, col)
        text, rel_row, rel_col = expand_snippet(item.insert, leading_indent(line), self.unit)
        self._skip_next = True
        self.hide_popup()
        self.replace(text, (row, start), (row, col))
        if rel_row == 0:
            self.move_cursor((row, start + rel_col))
        else:
            self.move_cursor((row + rel_row, rel_col))
        self.focus()

    # ------------------------------------------------------
    # клавиши
    # ------------------------------------------------------
    async def _on_key(self, event: events.Key) -> None:
        key = event.key

        if self._popup_open() and self._popup is not None:
            if key == "down":
                self._popup.action_cursor_down()
                self._consume(event)
                return
            if key == "up":
                self._popup.action_cursor_up()
                self._consume(event)
                return
            if key == "tab" or (key == "enter" and self._s.get("autocomplete_accept_enter", False)):
                self.accept_completion(self._popup.highlighted)
                self._consume(event)
                return
            if key == "escape":
                self.hide_popup()
                self._consume(event)
                return

        if self.read_only or not self.selection.is_empty:
            return

        if key == "enter" and self._s.get("auto_indent", True):
            if self._smart_enter():
                self._consume(event)
            return

        if not self._s.get("auto_close_brackets", True):
            return
        if key == "backspace":
            if self._smart_backspace():
                self._consume(event)
            return
        ch = event.character
        if ch and len(ch) == 1 and self._handle_pair(ch):
            self._consume(event)

    @staticmethod
    def _consume(event: events.Key) -> None:
        event.stop()
        event.prevent_default()

    # ------------------------------------------------------
    # умные правки
    # ------------------------------------------------------
    def _smart_enter(self) -> bool:
        row, col = self.cursor_location
        line = self.document.get_line(row)
        before, after = line[:col], line[col:]
        indent = leading_indent(before)
        extra = self.unit if opens_block(before) else ""
        # пробелы сразу после курсора «съедаем», чтобы хвост строки не получил лишний отступ
        skip = len(after) - len(after.lstrip(" \t"))
        self.replace("\n" + indent + extra, (row, col), (row, col + skip))
        self.move_cursor((row + 1, len(indent) + len(extra)))
        return True

    def _smart_backspace(self) -> bool:
        row, col = self.cursor_location
        if col == 0:
            return False
        line = self.document.get_line(row)
        prev = line[col - 1]
        nxt = line[col] if col < len(line) else ""
        if nxt and PAIRS.get(prev) == nxt:
            self.delete((row, col - 1), (row, col + 1))
            self.move_cursor((row, col - 1))
            return True
        return False

    def _handle_pair(self, ch: str) -> bool:
        row, col = self.cursor_location
        line = self.document.get_line(row)
        prev = line[col - 1] if col > 0 else ""
        nxt = line[col] if col < len(line) else ""
        ctx = scan_context(line[:col])

        if ctx == "comment":
            return False

        # перешагнуть уже стоящий закрывающий символ
        if ch in CLOSERS and nxt == ch:
            if ch != "'" or ctx == "string":
                self.move_cursor((row, col + 1))
                return True

        if ch == "'":
            if ctx == "string":
                return False  # это закрывающая кавычка — обычный ввод
            if prev and (prev.isalnum() or prev == "_"):
                return False
        elif ch not in PAIRS:
            return False
        elif ctx != "code":
            return False

        if nxt and not nxt.isspace() and nxt not in _SAFE_NEXT:
            return False

        self.insert(ch + PAIRS[ch], (row, col))
        self.move_cursor((row, col + 1))
        return True


def make_editor(text: str, engine: CompletionEngine, settings: dict, **kwargs) -> CodeEditor:
    """Создаёт редактор; если язык 'pascal' не поддержан в этой сборке Textual — без подсветки."""
    try:
        return CodeEditor(text, engine, settings, language="pascal", **kwargs)
    except Exception:  # noqa: BLE001
        return CodeEditor(text, engine, settings, language=None, **kwargs)
