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


class TabsTests(unittest.TestCase):
    """Логика вкладок: id по полному пути, без затирания и потерь."""

    def setUp(self):
        from pascaltui.screens import tabs as T

        self.T = T

        class FakeCE:
            def __init__(self, text, engine, settings, id=None):
                self.text, self.id, self.focused = text, id, False

            def attach_popup(self, popup):
                pass

            def focus(self):
                self.focused = True

        T.CodeEditor = FakeCE
        tabs = T.EditorTabs.__new__(T.EditorTabs)
        tabs.engine, tabs.settings = None, {}
        tabs._editors, tabs._paths, tabs._popup = {}, {}, None
        tabs.active = ""
        tabs.panes, tabs.removed = [], []
        tabs.add_pane = lambda pane: tabs.panes.append(pane)
        tabs.remove_pane = lambda tid: tabs.removed.append(tid)
        self.tabs = tabs

    def test_ids_are_valid_identifiers(self):
        import re

        for name in ["main.pas", "лаба 1.pas", "1.pas", "a/b/ж.pas", "x" * 300 + ".pas"]:
            tid = self.T.tab_id_for("/p/" + name)
            self.assertRegex(tid, r"^[A-Za-z][A-Za-z0-9_-]*$")

    def test_same_basename_in_different_folders(self):
        a, b = "/p/lab1/main.pas", "/p/lab2/main.pas"
        self.assertNotEqual(self.T.tab_id_for(a), self.T.tab_id_for(b))
        self.tabs.open_file_tab(a, "AAA")
        self.tabs.open_file_tab(b, "BBB")
        self.assertEqual(len(self.tabs.open_paths()), 2)
        self.assertEqual(self.tabs.active_path(), "/p/lab2/main.pas")
        self.assertEqual(self.tabs.get_active_editor().text, "BBB")

    def test_reopen_does_not_overwrite_unsaved_edits(self):
        self.tabs.open_file_tab("/p/a.pas", "disk")
        self.tabs.get_active_editor().text = "edited"
        self.tabs.open_file_tab("/p/a.pas", "disk")
        self.assertEqual(self.tabs.get_active_editor().text, "edited")
        self.tabs.open_file_tab("/p/a.pas", "fresh", reload=True)
        self.assertEqual(self.tabs.get_active_editor().text, "fresh")

    def test_active_path_follows_active_tab(self):
        self.tabs.open_file_tab("/p/a.pas", "A")
        self.tabs.open_file_tab("/p/b.pas", "B")
        self.tabs.active = self.T.tab_id_for("/p/a.pas")      # пользователь нажал на первую вкладку
        self.assertEqual(self.tabs.active_path(), "/p/a.pas")
        self.assertEqual(self.tabs.get_active_file_name(), "a.pas")   # а не id вида «a_pas»

    def test_close_under_folder_not_prefix_collision(self):
        for p in ["/p/lab1/a.pas", "/p/lab1/sub/b.pas", "/p/lab10/c.pas", "/p/lab1.pas"]:
            self.tabs.open_file_tab(p, "x")
        closed = self.tabs.close_under("/p/lab1")
        self.assertEqual(sorted(closed), ["/p/lab1/a.pas", "/p/lab1/sub/b.pas"])
        self.assertEqual(sorted(self.tabs.open_paths()), ["/p/lab1.pas", "/p/lab10/c.pas"])

    def test_close_returns_path_and_clears_state(self):
        self.tabs.open_file_tab("/p/a.pas", "A")
        tid = self.tabs.active
        self.assertEqual(self.tabs.close_file_tab(tid), "/p/a.pas")
        self.assertEqual(self.tabs.open_paths(), [])
        self.assertIsNone(self.tabs.close_file_tab(tid))

    def test_replace_tab_when_not_new(self):
        self.tabs.open_file_tab("/p/a.pas", "A")
        self.tabs.open_file_tab("/p/b.pas", "B", new_tab=False)
        self.assertEqual(self.tabs.open_paths(), ["/p/b.pas"])

    def test_is_inside(self):
        self.assertTrue(self.T.is_inside("/p/a/b.pas", "/p/a"))
        self.assertFalse(self.T.is_inside("/p/ab/b.pas", "/p/a"))


class ImportTests(unittest.TestCase):
    def test_all_ui_modules_import(self):
        from pascaltui import app  # noqa: F401
        from pascaltui import commands  # noqa: F401
        from pascaltui.screens import dialogs, file_menu, option_windows, theme_editor  # noqa: F401

    def test_bindings_translated(self):
        from pascaltui.app import make_bindings
        ru = {b.key: b.description for b in make_bindings("ru") if b.show}
        en = {b.key: b.description for b in make_bindings("en") if b.show}
        self.assertEqual(set(ru), {"ctrl+q", "ctrl+o", "ctrl+r", "ctrl+s", "ctrl+w", "f2"})
        for key in ru:
            self.assertTrue(ru[key] and en[key])
            self.assertNotEqual(ru[key], en[key], key)


if __name__ == "__main__":
    print("stub Textual:", USING_STUB)
    unittest.main(verbosity=1)
