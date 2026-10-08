"""Тесты чистой логики (без Textual). Запуск: python3 tests/test_logic.py"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pascaltui import completions as C, files, i18n, settings, templates, themes  # noqa: E402


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.engine = C.CompletionEngine.from_files()

    def test_prefix(self):
        self.assertEqual(C.current_prefix("  writ", 6), (2, "writ"))
        self.assertEqual(C.current_prefix("x := 12", 7), (7, ""))   # число — не префикс
        self.assertEqual(C.current_prefix("", 0), (0, ""))

    def test_context(self):
        self.assertEqual(C.scan_context("x := 'abc"), "string")
        self.assertEqual(C.scan_context("x := 'it''s' + wri"), "code")
        self.assertEqual(C.scan_context("x := 1; // комм"), "comment")
        self.assertEqual(C.scan_context("{ коммент "), "comment")
        self.assertEqual(C.scan_context("(* a *) wri"), "code")

    def test_opens_block(self):
        self.assertTrue(C.opens_block("  for i := 1 to 3 do"))
        self.assertTrue(C.opens_block("begin"))
        self.assertTrue(C.opens_block("if a then begin // x"))
        self.assertFalse(C.opens_block("writeln('begin');"))
        self.assertFalse(C.opens_block("x := y;"))

    def test_suggest_basic(self):
        r = self.engine.suggest("wri")
        labels = [c.trigger for c in r]
        self.assertIn("write", labels)
        self.assertIn("writeln", labels)

    def test_exact_keyword_hidden_but_snippet_shown(self):
        r = self.engine.suggest("for")
        kinds = {(c.trigger, c.kind) for c in r}
        self.assertNotIn(("for", "keyword"), kinds)
        self.assertIn(("for", "snippet"), kinds)

    def test_snippets_toggle(self):
        r = self.engine.suggest("for", use_snippets=False)
        self.assertTrue(all(c.kind != "snippet" for c in r))

    def test_buffer_words(self):
        r = self.engine.suggest("cou", "var counter: integer; counter := 1;", use_buffer=True)
        self.assertIn("counter", [c.trigger for c in r])
        r = self.engine.suggest("cou", "var counter: integer;", use_buffer=False)
        self.assertNotIn("counter", [c.trigger for c in r])

    def test_max_items(self):
        self.assertLessEqual(len(self.engine.suggest("r", max_items=3)), 3)

    def test_expand_snippet(self):
        text, row, col = C.expand_snippet("for $0 do\n\tbegin\n\tend;", "  ", " ")
        self.assertEqual(text, "for  do\n   begin\n   end;")
        self.assertEqual((row, col), (0, 4))
        text, row, col = C.expand_snippet("repeat\n\t$0\nuntil ;", "", "  ")
        self.assertEqual(text, "repeat\n  \nuntil ;")
        self.assertEqual((row, col), (1, 2))
        text, row, col = C.expand_snippet("a\n\t$0", "  ", "  ")   # курсор на строке с отступом
        self.assertEqual((row, col), (1, 4))


class SettingsTests(unittest.TestCase):
    def test_sanitize(self):
        base = settings.default_settings()
        out = settings.sanitize(
            {"tab_width": 99, "autocomplete": "yes", "language": "", "unknown": 1,
             "autocomplete_min_chars": 3}, base)
        self.assertEqual(out["tab_width"], 8)
        self.assertEqual(out["autocomplete"], base["autocomplete"])
        self.assertEqual(out["language"], base["language"])
        self.assertEqual(out["autocomplete_min_chars"], 3)
        self.assertNotIn("unknown", out)

    def test_legacy_settings_compatible(self):
        base = settings.default_settings()
        legacy = {"language": "en", "start_template": "empty", "runtime": "dotnet",
                  "compiler_path": "/x/pabcnetc.exe", "projects_dir": "/x/Projects"}
        out = settings.sanitize(legacy, base)
        self.assertEqual(out["runtime"], "dotnet")
        self.assertEqual(out["compiler_path"], "/x/pabcnetc.exe")


class I18nTests(unittest.TestCase):
    def test_parity(self):
        ru, en = i18n._tables["ru"], i18n._tables["en"]
        self.assertEqual(set(ru), set(en))

    def test_format_and_fallback(self):
        self.assertIn("a.pas", i18n.tr("ru", "active_file", name="a.pas"))
        self.assertEqual(i18n.tr("xx", "footer_quit"), i18n.tr("en", "footer_quit"))
        self.assertEqual(i18n.tr("ru", "no_such_key"), "no_such_key")

    def test_footer_differs(self):
        self.assertNotEqual(i18n.tr("ru", "footer_quit"), i18n.tr("en", "footer_quit"))


class ThemeTests(unittest.TestCase):
    def test_validate(self):
        t = themes.validate_theme({"name": "x", "primary": "ABC", "background": "#112233", "foo": 1})
        self.assertEqual(t["primary"], "#aabbcc")
        self.assertEqual(t["background"], "#112233")
        self.assertIsNone(themes.validate_theme({"name": "x", "primary": "red"}))
        self.assertIsNone(themes.validate_theme({"primary": "#ffffff"}))

    def test_builtin_loaded(self):
        all_themes = themes.load_all()
        for name in ("pascal-dark", "pascal-light", "abc-blue", "terminal-green"):
            self.assertIn(name, all_themes)

    def test_slug(self):
        self.assertEqual(themes.slugify("My Theme!"), "my-theme")
        self.assertEqual(themes.slugify("!!!"), "theme")


class TemplateTests(unittest.TestCase):
    def test_templates(self):
        self.assertEqual(templates.template_code("hello"), "begin\n writeln('Hello World');\nend.")
        self.assertEqual(templates.empty_code(), "begin\n \nend.")
        self.assertIn(("Hello World", "hello"), templates.template_choices("ru"))


class FilesTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p, err = files.create_file(d, "a", "x")
            self.assertIsNone(err)
            self.assertEqual(files.project_files(d), ["a.pas"])
            self.assertEqual(files.create_file(d, "a.pas", "y")[1], "exists")  # не перезаписывает
            self.assertEqual(open(p).read(), "x")
            self.assertEqual(files.create_file(d, "../evil", "z")[1], "bad_name")
            self.assertEqual(files.create_file(d, "  ", "z")[1], "bad_name")
            open(os.path.join(d, "a.exe"), "w").close()
            _, err = files.rename_file(d, "a.pas", "b")
            self.assertIsNone(err)
            self.assertTrue(os.path.exists(os.path.join(d, "b.exe")))
            _, err = files.copy_file(d, "b.pas", "c")
            self.assertIsNone(err)
            self.assertEqual(files.copy_file(d, "b.pas", "c")[1], "exists")
            self.assertEqual(files.auto_filename(d), "project_1")
            self.assertIsNone(files.delete_file(d, "b.pas"))
            self.assertFalse(os.path.exists(os.path.join(d, "b.exe")))

    def test_cp1251_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "old.pas")
            with open(p, "wb") as f:
                f.write("writeln('Привет');".encode("cp1251"))
            text, err = files.read_text(p)
            self.assertIsNone(err)
            self.assertIn("Привет", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
