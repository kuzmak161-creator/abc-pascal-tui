"""Окна: «Темы и подсветка» и «Автодополнение»."""
from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Switch

from .. import templates, themes
from ..i18n import available_languages, tr
from .theme_editor import ThemeEditorScreen

_CSS = """
#win_container {
    width: 60;
    max-width: 98%;
    height: auto;
    max-height: 92%;
    background: $panel;
    border: thick $primary;
    padding: 1 2;
}
#win_scroll { height: auto; max-height: 70%; }
.win_label { margin-top: 1; }
.sw_row { height: 3; }
.sw_label { height: 3; content-align: left middle; padding-left: 1; }
#theme_buttons { height: 3; margin-top: 1; }
#win_status { color: $warning; height: auto; }
#win_buttons { height: 3; margin-top: 1; }
.win_btn { margin-right: 1; }
"""


class _Window(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, lang: str):
        super().__init__()
        self._lang = lang

    def _t(self, key: str, **kw) -> str:
        return tr(self._lang, key, **kw)

    def _buttons(self) -> Horizontal:
        return Horizontal(
            Button(self._t("btn_save"), variant="success", id="win_save", classes="win_btn"),
            Button(self._t("btn_cancel"), variant="default", id="win_cancel", classes="win_btn"),
            id="win_buttons",
        )

    def action_cancel(self) -> None:
        self.dismiss(None)


class AutocompleteScreen(_Window):
    """Результат: dict с настройками автодополнения или None."""

    CSS = "AutocompleteScreen { align: center middle; background: rgba(0,0,0,0.6); }" + _CSS
    SWITCHES = ("autocomplete", "autocomplete_buffer", "autocomplete_snippets", "autocomplete_accept_enter",
                "auto_close_brackets", "auto_indent", "tab_inserts_indent", "show_line_numbers",
                "soft_wrap", "save_on_quit", "syntax_highlight")
    INTS = ("autocomplete_min_chars", "autocomplete_max_items", "tab_width")

    def __init__(self, lang: str, settings: dict):
        super().__init__(lang)
        self._s = dict(settings)

    def compose(self) -> ComposeResult:
        with Vertical(id="win_container"):
            yield Label(self._t("autocomplete_title"))
            with VerticalScroll(id="win_scroll"):
                for key in self.SWITCHES:
                    yield Horizontal(
                        Switch(value=bool(self._s.get(key)), id=f"set_{key}"),
                        Label(self._t(f"set_{key}"), classes="sw_label"),
                        classes="sw_row",
                    )
                for key in self.INTS:
                    yield Label(self._t(f"set_{key}"), classes="win_label")
                    yield Input(value=str(self._s.get(key, "")), type="integer", id=f"set_{key}")
                yield Label(self._t("hint_hotkeys"), classes="win_label")
            yield self._buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "win_cancel":
            self.dismiss(None)
        elif event.button.id == "win_save":
            out: dict = {k: self.query_one(f"#set_{k}", Switch).value for k in self.SWITCHES}
            for k in self.INTS:
                try:
                    out[k] = int(self.query_one(f"#set_{k}", Input).value.strip())
                except ValueError:
                    out[k] = self._s.get(k)
            self.dismiss(out)


class ThemesScreen(_Window):
    """Выбор темы (с предпросмотром), создание/изменение/удаление своих, подсветка кода.

    Результат: {"theme": ..., "editor_theme": ...} или None.
    """

    CSS = "ThemesScreen { align: center middle; background: rgba(0,0,0,0.6); }" + _CSS

    def __init__(self, lang: str, settings: dict, current_theme: str):
        super().__init__(lang)
        self._s = dict(settings)
        self._orig = current_theme
        self._cur = current_theme

    def _options(self) -> list[tuple[str, str]]:
        names = self.app.theme_names() or [self._cur]  # type: ignore[attr-defined]
        return [(n, n) for n in names]

    def compose(self) -> ComposeResult:
        opts = self._options()
        cur = self._cur if self._cur in [v for _, v in opts] else opts[0][1]
        editor_opts = [(self._t("editor_theme_auto"), "auto")] + [(n, n) for n in themes.EDITOR_THEMES]
        wanted = self._s.get("editor_theme", "auto")
        wanted = wanted if wanted in [v for _, v in editor_opts] else "auto"
        with Vertical(id="win_container"):
            yield Label(self._t("themes_title"))
            with VerticalScroll(id="win_scroll"):
                yield Label(self._t("set_theme"), classes="win_label")
                yield Select(opts, value=cur, allow_blank=False, id="sel_theme")
                with Horizontal(id="theme_buttons"):
                    yield Button(self._t("btn_theme_new"), id="theme_new", classes="win_btn")
                    yield Button(self._t("btn_theme_edit"), id="theme_edit", classes="win_btn")
                    yield Button(self._t("btn_theme_delete"), id="theme_delete", variant="error", classes="win_btn")
                yield Label("", id="win_status")
                yield Label(self._t("set_editor_theme"), classes="win_label")
                yield Select(editor_opts, value=wanted, allow_blank=False, id="sel_editor_theme")
            yield self._buttons()

    @on(Select.Changed, "#sel_theme")
    def _preview(self, event: Select.Changed) -> None:
        if isinstance(event.value, str):
            self._cur = event.value
            self.app.preview_theme(event.value)  # type: ignore[attr-defined]

    def _status(self, text: str) -> None:
        self.query_one("#win_status", Label).update(text)

    def _refresh_select(self, name: str) -> None:
        sel = self.query_one("#sel_theme", Select)
        sel.set_options(self._options())
        names = [v for _, v in self._options()]
        sel.value = name if name in names else names[0]

    def _after_editor(self, theme: dict | None) -> None:
        if theme:
            self._refresh_select(theme["name"])

    def _open_editor(self, base: dict | None, is_user: bool) -> None:
        self.app.push_screen(ThemeEditorScreen(self._lang, base, is_user), self._after_editor)  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid, app = event.button.id, self.app
        if bid == "win_cancel":
            self.action_cancel()
        elif bid == "win_save":
            editor = self.query_one("#sel_editor_theme", Select).value
            self.dismiss({"theme": self._cur, "editor_theme": editor if isinstance(editor, str) else "auto"})
        elif bid == "theme_new":
            self._open_editor(None, False)
        elif bid == "theme_edit":
            self._open_editor(app.theme_data(self._cur), app.is_user_theme(self._cur))  # type: ignore[attr-defined]
        elif bid == "theme_delete":
            if app.is_user_theme(self._cur):  # type: ignore[attr-defined]
                name = self._cur
                app.remove_user_theme(name)  # type: ignore[attr-defined]
                self._status(self._t("log_theme_deleted", name=name).strip())
                self._refresh_select(self._orig)
            else:
                self._status(self._t("theme_builtin_readonly"))

    def action_cancel(self) -> None:
        self.app.preview_theme(self._orig)  # type: ignore[attr-defined]
        self.dismiss(None)


class GeneralScreen(_Window):
    """Язык интерфейса и шаблон нового файла. Результат: dict или None."""

    CSS = "GeneralScreen { align: center middle; background: rgba(0,0,0,0.6); }" + _CSS

    def __init__(self, lang: str, settings: dict):
        super().__init__(lang)
        self._s = dict(settings)

    @staticmethod
    def _pick(options: list[tuple[str, str]], wanted: str) -> str:
        values = [v for _, v in options]
        return wanted if wanted in values else values[0]

    def compose(self) -> ComposeResult:
        langs = [(name, code) for code, name in available_languages()] or [(self._lang, self._lang)]
        tpls = templates.template_choices(self._lang)
        with Vertical(id="win_container"):
            yield Label(self._t("general_title"))
            with VerticalScroll(id="win_scroll"):
                yield Label(self._t("set_language"), classes="win_label")
                yield Select(langs, value=self._pick(langs, self._lang), allow_blank=False, id="sel_language")
                yield Label(self._t("set_start_template"), classes="win_label")
                yield Select(tpls, value=self._pick(tpls, self._s.get("start_template", "hello")),
                             allow_blank=False, id="sel_start_template")
            yield self._buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "win_cancel":
            self.dismiss(None)
        elif event.button.id == "win_save":
            out = {}
            for key in ("language", "start_template"):
                value = self.query_one(f"#sel_{key}", Select).value
                if isinstance(value, str):
                    out[key] = value
            self.dismiss(out)


class RunScreen(_Window):
    """Запуск и пути. Результат: dict или None."""

    CSS = "RunScreen { align: center middle; background: rgba(0,0,0,0.6); }" + _CSS

    def __init__(self, lang: str, settings: dict):
        super().__init__(lang)
        self._s = dict(settings)

    def compose(self) -> ComposeResult:
        runtimes = [(self._t("runtime_mono"), "mono"), (self._t("runtime_dotnet"), "dotnet")]
        current = self._s.get("runtime", "mono")
        with Vertical(id="win_container"):
            yield Label(self._t("run_title"))
            with VerticalScroll(id="win_scroll"):
                yield Label(self._t("set_runtime"), classes="win_label")
                yield Select(runtimes, value=current if current in ("mono", "dotnet") else "mono",
                             allow_blank=False, id="sel_runtime")
                yield Label(self._t("set_compile_timeout"), classes="win_label")
                yield Input(value=str(self._s.get("compile_timeout", 60)), type="integer", id="in_compile_timeout")
                yield Label(self._t("set_compiler_path"), classes="win_label")
                yield Input(value=str(self._s.get("compiler_path", "")), id="in_compiler_path")
                yield Label(self._t("set_projects_dir"), classes="win_label")
                yield Input(value=str(self._s.get("projects_dir", "")), id="in_projects_dir")
                yield Button(self._t("btn_show_paths"), id="show_paths", classes="win_label")
            yield self._buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "win_cancel":
            self.dismiss(None)
        elif bid == "show_paths":
            self.app.action_show_paths()  # type: ignore[attr-defined]
        elif bid == "win_save":
            out: dict = {}
            runtime = self.query_one("#sel_runtime", Select).value
            if isinstance(runtime, str):
                out["runtime"] = runtime
            try:
                out["compile_timeout"] = int(self.query_one("#in_compile_timeout", Input).value.strip())
            except ValueError:
                pass
            for key in ("compiler_path", "projects_dir"):
                value = self.query_one(f"#in_{key}", Input).value.strip()
                if value:
                    out[key] = value
            self.dismiss(out)
