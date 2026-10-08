"""Экран настроек: язык, тема, редактор, автодополнение, запуск и пути."""
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

SELECT_KEYS = ("language", "theme", "editor_theme", "start_template", "runtime")
SWITCH_KEYS = (
    "autocomplete", "autocomplete_buffer", "autocomplete_snippets", "autocomplete_accept_enter",
    "auto_close_brackets", "auto_indent", "tab_inserts_indent", "show_line_numbers",
    "soft_wrap", "save_on_quit",
)
INT_KEYS = ("tab_width", "autocomplete_min_chars", "autocomplete_max_items", "compile_timeout")
STR_KEYS = ("compiler_path", "projects_dir")


class SettingsScreen(ModalScreen):
    """Результат: dict с изменёнными настройками или None при отмене."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    CSS = """
    SettingsScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #settings_container {
        width: 64;
        max-width: 98%;
        height: 92%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }
    #settings_scroll {
        height: 1fr;
    }
    .sec_title {
        margin-top: 1;
        text-style: bold;
        color: $accent;
    }
    .set_label {
        margin-top: 1;
    }
    .sw_row {
        height: 3;
    }
    .sw_label {
        height: 3;
        content-align: left middle;
        padding-left: 1;
    }
    #theme_buttons {
        height: 3;
        margin-top: 1;
    }
    .theme_btn {
        margin-right: 1;
    }
    #settings_status {
        color: $warning;
        height: auto;
    }
    #settings_buttons {
        height: 3;
        margin-top: 1;
    }
    .set_btn {
        margin-right: 1;
    }
    """

    def __init__(self, settings: dict, lang: str, current_theme: str):
        super().__init__()
        self._s = dict(settings)
        self._lang = lang
        self._orig_theme = current_theme
        self._cur_theme = current_theme

    # ------------------------------------------------------
    def _t(self, key: str, **kw) -> str:
        return tr(self._lang, key, **kw)

    @staticmethod
    def _pick(options: list[tuple[str, str]], wanted: str) -> str:
        values = [v for _, v in options]
        return wanted if wanted in values else values[0]

    def _theme_options(self) -> list[tuple[str, str]]:
        names = self.app.theme_names() or [self._cur_theme]  # type: ignore[attr-defined]
        return [(n, n) for n in names]

    def _select(self, key: str, options: list[tuple[str, str]], wanted: str) -> Select:
        return Select(options, value=self._pick(options, wanted), allow_blank=False, id=f"set_{key}")

    def _sw(self, key: str) -> Horizontal:
        return Horizontal(
            Switch(value=bool(self._s.get(key, False)), id=f"set_{key}"),
            Label(self._t(f"set_{key}"), classes="sw_label"),
            classes="sw_row",
        )

    def _field(self, key: str, **kw) -> tuple[Label, Input]:
        return (
            Label(self._t(f"set_{key}"), classes="set_label"),
            Input(value=str(self._s.get(key, "")), id=f"set_{key}", **kw),
        )

    # ------------------------------------------------------
    def compose(self) -> ComposeResult:
        L = self._lang
        s = self._s
        editor_options = [(self._t("editor_theme_auto"), "auto")] + [(n, n) for n in themes.EDITOR_THEMES]
        runtime_options = [(self._t("runtime_mono"), "mono"), (self._t("runtime_dotnet"), "dotnet")]

        with Vertical(id="settings_container"):
            yield Label(self._t("settings_title"))
            with VerticalScroll(id="settings_scroll"):
                yield Label(self._t("sec_general"), classes="sec_title")
                yield Label(self._t("set_language"), classes="set_label")
                yield self._select("language", [(name, code) for code, name in available_languages()], L)
                yield Label(self._t("set_start_template"), classes="set_label")
                yield self._select("start_template", templates.template_choices(L), s.get("start_template", "hello"))

                yield Label(self._t("sec_theme"), classes="sec_title")
                yield Label(self._t("set_theme"), classes="set_label")
                yield self._select("theme", self._theme_options(), self._cur_theme)
                with Horizontal(id="theme_buttons"):
                    yield Button(self._t("btn_theme_new"), id="theme_new", classes="theme_btn")
                    yield Button(self._t("btn_theme_edit"), id="theme_edit", classes="theme_btn")
                    yield Button(self._t("btn_theme_delete"), id="theme_delete", variant="error", classes="theme_btn")
                yield Label("", id="settings_status")
                yield Label(self._t("set_editor_theme"), classes="set_label")
                yield self._select("editor_theme", editor_options, s.get("editor_theme", "auto"))

                yield Label(self._t("sec_editor"), classes="sec_title")
                for key in ("auto_close_brackets", "auto_indent", "tab_inserts_indent",
                            "show_line_numbers", "soft_wrap", "save_on_quit"):
                    yield self._sw(key)
                yield from self._field("tab_width", type="integer")

                yield Label(self._t("sec_autocomplete"), classes="sec_title")
                for key in ("autocomplete", "autocomplete_buffer", "autocomplete_snippets",
                            "autocomplete_accept_enter"):
                    yield self._sw(key)
                yield from self._field("autocomplete_min_chars", type="integer")
                yield from self._field("autocomplete_max_items", type="integer")
                yield Label(self._t("hint_hotkeys"), classes="set_label")

                yield Label(self._t("sec_run"), classes="sec_title")
                yield Label(self._t("set_runtime"), classes="set_label")
                yield self._select("runtime", runtime_options, s.get("runtime", "mono"))
                yield from self._field("compile_timeout", type="integer")
                yield from self._field("compiler_path")
                yield from self._field("projects_dir")

            with Horizontal(id="settings_buttons"):
                yield Button(self._t("btn_save"), variant="success", id="settings_save", classes="set_btn")
                yield Button(self._t("btn_cancel"), variant="default", id="settings_cancel", classes="set_btn")

    # ------------------------------------------------------
    # тема: предпросмотр и управление
    # ------------------------------------------------------
    def _status(self, text: str) -> None:
        self.query_one("#settings_status", Label).update(text)

    @on(Select.Changed, "#set_theme")
    def _theme_changed(self, event: Select.Changed) -> None:
        if isinstance(event.value, str):
            self._cur_theme = event.value
            self.app.preview_theme(event.value)  # type: ignore[attr-defined]

    def _refresh_theme_select(self, select_name: str | None = None) -> None:
        select = self.query_one("#set_theme", Select)
        select.set_options(self._theme_options())
        wanted = select_name or self._cur_theme
        names = [v for _, v in self._theme_options()]
        select.value = wanted if wanted in names else names[0]

    def _on_theme_saved(self, theme: dict | None) -> None:
        if theme:
            self._refresh_theme_select(theme["name"])

    def _open_theme_editor(self, base: dict | None, is_user: bool) -> None:
        self.app.push_screen(  # type: ignore[attr-defined]
            ThemeEditorScreen(self._lang, base, is_user), self._on_theme_saved
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        app = self.app
        if bid == "settings_save":
            self.dismiss(self._collect())
        elif bid == "settings_cancel":
            self.action_cancel()
        elif bid == "theme_new":
            self._open_theme_editor(None, False)
        elif bid == "theme_edit":
            self._open_theme_editor(app.theme_data(self._cur_theme), app.is_user_theme(self._cur_theme))  # type: ignore[attr-defined]
        elif bid == "theme_delete":
            if app.is_user_theme(self._cur_theme):  # type: ignore[attr-defined]
                name = self._cur_theme
                app.remove_user_theme(name)  # type: ignore[attr-defined]
                self._status(self._t("log_theme_deleted", name=name).strip())
                self._refresh_theme_select(self._orig_theme)
            else:
                self._status(self._t("theme_builtin_readonly"))

    # ------------------------------------------------------
    def _collect(self) -> dict:
        out: dict = {}
        for key in SELECT_KEYS:
            value = self.query_one(f"#set_{key}", Select).value
            if isinstance(value, str):
                out[key] = value
        for key in SWITCH_KEYS:
            out[key] = self.query_one(f"#set_{key}", Switch).value
        for key in INT_KEYS:
            raw = self.query_one(f"#set_{key}", Input).value.strip()
            try:
                out[key] = int(raw)
            except ValueError:
                out[key] = self._s.get(key)
        for key in STR_KEYS:
            value = self.query_one(f"#set_{key}", Input).value.strip()
            if value:
                out[key] = value
        return out

    def action_cancel(self) -> None:
        self.app.preview_theme(self._orig_theme)  # type: ignore[attr-defined]
        self.dismiss(None)
