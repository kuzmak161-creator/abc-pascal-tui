"""Дымовой тест UI без настоящего Textual.

Если Textual не установлен, подставляется заглушка: проверяются импорты всех UI-модулей
и логика правок редактора (скобки, отступы, вставка подсказки). Реальный интерфейс этим
НЕ проверяется — только то, что код импортируется и логика считает позиции верно.
Запуск: python3 tests/test_editor_stub.py
"""
import importlib.util
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _install_stub() -> None:
    class _Meta(type):
        def __getattr__(cls, attr):
            if attr.startswith("__"):
                raise AttributeError(attr)
            return type(attr, (Stub,), {})

    _Meta.__or__ = lambda cls, other: cls

    class Stub(metaclass=_Meta):
        def __init__(self, *a, **k):
            pass

        def __class_getitem__(cls, item):
            return cls

    def make_module(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        mod.__path__ = []  # type: ignore[attr-defined]

        def getattr_(attr):
            if attr.startswith("__"):
                raise AttributeError(attr)
            return type(attr, (Stub,), {})

        mod.__getattr__ = getattr_  # type: ignore[attr-defined]
        return mod

    names = [
        "textual", "textual.app", "textual.binding", "textual.containers", "textual.events",
        "textual.geometry", "textual.screen", "textual.widgets", "textual.widgets.option_list",
        "textual.theme", "textual.command",
    ]
    for n in names:
        sys.modules[n] = make_module(n)

    def on(*a, **k):
        return lambda f: f

    def work(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

    class Binding(Stub):
        def __init__(self, key, action, description="", show=True, **k):
            self.key, self.action, self.description, self.show = key, action, description, show

    class Offset(Stub):
        def __init__(self, x=0, y=0):
            self.x, self.y = x, y

    class Text:  # rich.Text заменитель не нужен — rich обычно стоит вместе с textual
        pass

    sys.modules["textual"].on = on
    sys.modules["textual"].work = work
    sys.modules["textual.binding"].Binding = Binding
    sys.modules["textual.geometry"].Offset = Offset
    if importlib.util.find_spec("rich") is None:
        rich = make_module("rich")
        rich_text = types.ModuleType("rich.text")

        class RText:
            def __init__(self, *a, **k):
                self.parts = []

            def append(self, s, style=None):
                self.parts.append(s)

        rich_text.Text = RText
        sys.modules["rich"] = rich
        sys.modules["rich.text"] = rich_text


USING_STUB = False
try:
    import textual  # noqa: F401
    if not hasattr(textual, "__version__"):
        raise ImportError
except ImportError:
    _install_stub()
    USING_STUB = True

from pascaltui import editor as E  # noqa: E402
from pascaltui.completions import CompletionEngine  # noqa: E402


class FakeDoc:
    def __init__(self, lines):
        self.lines = lines

    def get_line(self, row):
        return self.lines[row]


class FakeEditor(E.CodeEditor):
    """CodeEditor без настоящего TextArea: текст — список строк, курсор — (row, col)."""

    def __init__(self, text, settings):  # noqa: super().__init__ намеренно не вызывается
        self.engine = CompletionEngine.from_files()
        self._s = dict(settings)
        self.lines = text.split("\n")
        self.cursor = (0, 0)
        self._items = []
        self._skip_next = False
        self.focused = False

    @property
    def document(self):
        return FakeDoc(self.lines)

    @property
    def cursor_location(self):
        return self.cursor

    @property
    def text(self):
        return "\n".join(self.lines)

    def move_cursor(self, loc):
        self.cursor = tuple(loc)

    def focus(self):
        self.focused = True

    def hide_popup(self):
        pass

    def insert(self, text, location):
        self.replace(text, location, location)

    def replace(self, text, start, end):
        (r1, c1), (r2, c2) = start, end
        before = self.lines[r1][:c1]
        after = self.lines[r2][c2:]
        new = (before + text + after).split("\n")
        self.lines[r1:r2 + 1] = new

    def delete(self, start, end):
        self.replace("", start, end)


SETTINGS = {"tab_width": 2, "auto_indent": True, "auto_close_brackets": True}


def make(text, cursor):
    ed = FakeEditor(text, SETTINGS)
    ed.cursor = cursor
    return ed


class EditorLogicTests(unittest.TestCase):
    def test_pair_paren(self):
        ed = make("writeln", (0, 7))
        self.assertTrue(ed._handle_pair("("))
        self.assertEqual(ed.text, "writeln()")
        self.assertEqual(ed.cursor, (0, 8))

    def test_skip_over_closer(self):
        ed = make("f()", (0, 2))
        self.assertTrue(ed._handle_pair(")"))
        self.assertEqual(ed.text, "f()")
        self.assertEqual(ed.cursor, (0, 3))

    def test_quote_pair_and_string_context(self):
        ed = make("x := ", (0, 5))
        self.assertTrue(ed._handle_pair("'"))
        self.assertEqual(ed.text, "x := ''")
        self.assertEqual(ed.cursor, (0, 6))
        # апостроф внутри строки — обычный ввод
        ed = make("x := 'ab", (0, 8))
        self.assertFalse(ed._handle_pair("'"))
        # апостроф после буквы (не в строке) — не парим
        ed = make("it", (0, 2))
        self.assertFalse(ed._handle_pair("'"))

    def test_no_pair_in_comment(self):
        ed = make("// note ", (0, 8))
        self.assertFalse(ed._handle_pair("("))
        self.assertFalse(ed._handle_pair("'"))

    def test_no_pair_before_word(self):
        ed = make("abc", (0, 0))
        self.assertFalse(ed._handle_pair("("))

    def test_backspace_pair(self):
        ed = make("f()", (0, 2))
        self.assertTrue(ed._smart_backspace())
        self.assertEqual(ed.text, "f")
        self.assertEqual(ed.cursor, (0, 1))
        ed = make("f(x)", (0, 3))
        self.assertFalse(ed._smart_backspace())

    def test_enter_keeps_and_adds_indent(self):
        ed = make("  if a then begin", (0, 17))
        ed._smart_enter()
        self.assertEqual(ed.lines, ["  if a then begin", "    "])
        self.assertEqual(ed.cursor, (1, 4))
        ed = make("  x := 1;", (0, 9))
        ed._smart_enter()
        self.assertEqual(ed.lines, ["  x := 1;", "  "])
        self.assertEqual(ed.cursor, (1, 2))

    def test_enter_in_middle_of_line(self):
        ed = make("begin end", (0, 5))
        ed._smart_enter()
        self.assertEqual(ed.lines, ["begin", "  end"])  # хвост строки переезжает вместе с отступом

    def test_accept_plain_word(self):
        ed = make("  wri", (0, 5))
        ed._items = ed.engine.suggest("wri")
        idx = [c.trigger for c in ed._items].index("writeln")
        ed.accept_completion(idx)
        self.assertEqual(ed.text, "  writeln()")
        self.assertEqual(ed.cursor, (0, 10))
        self.assertTrue(ed._skip_next)

    def test_accept_snippet_multiline(self):
        ed = make("  for", (0, 5))
        ed._items = [c for c in ed.engine.suggest("for") if c.kind == "snippet" and c.trigger == "for"]
        ed.accept_completion(0)
        self.assertEqual(
            ed.lines,
            ["  for var i := 1 to  do", "    begin", "    ", "    end;"],
        )
        self.assertEqual(ed.cursor, (0, 20))

    def test_accept_snippet_cursor_on_later_line(self):
        ed = make("repeat", (0, 6))
        ed._items = [c for c in ed.engine.suggest("repeat") if c.kind == "snippet"]
        ed.accept_completion(0)
        self.assertEqual(ed.lines, ["repeat", "  ", "until ;"])
        self.assertEqual(ed.cursor, (1, 2))

    def test_accept_bad_index(self):
        ed = make("x", (0, 1))
        ed._items = []
        ed.accept_completion(None)
        ed.accept_completion(5)
        self.assertEqual(ed.text, "x")


class ImportTests(unittest.TestCase):
    def test_all_ui_modules_import(self):
        from pascaltui import app  # noqa: F401
        from pascaltui import commands  # noqa: F401
        from pascaltui.screens import dialogs, file_menu, option_windows, theme_editor  # noqa: F401

    def test_bindings_translated(self):
        from pascaltui.app import make_bindings
        ru = {b.key: b.description for b in make_bindings("ru") if b.show}
        en = {b.key: b.description for b in make_bindings("en") if b.show}
        self.assertEqual(set(ru), {"ctrl+q", "ctrl+o", "ctrl+r", "ctrl+s", "f2"})
        for key in ru:
            self.assertTrue(ru[key] and en[key])
            self.assertNotEqual(ru[key], en[key], key)


if __name__ == "__main__":
    print("stub Textual:", USING_STUB)
    unittest.main(verbosity=1)
