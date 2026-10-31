"""Главное приложение PascalTUI."""
from __future__ import annotations

import asyncio
import os

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, RichLog

from . import files, runner, templates, themes
from .completions import CompletionEngine
from .editor import CompletionPopup, make_editor
from .i18n import tr
from .paths import COMPILER_FILE, SETTINGS_PATH, candidate_share_dirs
from .commands import SettingsCommands
from .screens import (
    AutocompleteScreen,
    ConfirmDialog,
    FileMenuScreen,
    GeneralScreen,
    InputDialog,
    RunScreen,
    ThemesScreen,
)
from .screens.tabs import EditorTabs, TabBar, is_inside
from .settings import load_settings, runtime_config, sanitize, save_settings

DEFAULT_THEME_FALLBACK = "textual-dark"


def make_bindings(lang: str) -> list[Binding]:
    return [
        Binding("ctrl+q", "quit", tr(lang, "footer_quit"), key_display="^Q", priority=True),
        Binding("ctrl+o", "open_menu", tr(lang, "footer_open_menu"), key_display="^O"),
        Binding("ctrl+r", "run", tr(lang, "footer_run"), key_display="^R"),
        Binding("ctrl+s", "save", tr(lang, "footer_save"), key_display="^S"),
        Binding("ctrl+w", "close_tab", tr(lang, "close_tab"), key_display="^W"),
        Binding("f2", "settings", tr(lang, "footer_settings"), key_display="F2"),
        Binding("q", "quit", "", show=False),
        Binding("o", "open_menu", "", show=False),
        Binding("s", "settings", "", show=False),
    ]


_INITIAL_LANG = load_settings().get("language", "ru")


class PascalTUI(App):
    COMMANDS = {SettingsCommands}
    BINDINGS = make_bindings(_INITIAL_LANG)

    CSS = """
    #main_layout { layout: vertical; }
    #workspace { height: 3fr; }
    #buttons_container { height: 3; margin-top: 1; margin-bottom: 1; }
    #log_box { height: 1fr; min-height: 4; }
    Button { margin-right: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.lang: str = self.settings["language"]
        self.engine = CompletionEngine.from_files()
        self._theme_defs: dict[str, dict] = themes.load_all()
        self.code_backup = ""
        self._busy = False
        self.open_files: list[str] = []
        self.file_texts: dict[str, str] = {}
        
        try:
            os.makedirs(self.projects_dir, exist_ok=True)
        except OSError:
            pass
        self.current_file = self._initial_file()

    @property
    def projects_dir(self) -> str:
        return os.path.expanduser(self.settings["projects_dir"])

    @property
    def compiler_path(self) -> str:
        return os.path.expanduser(self.settings["compiler_path"])

    @property
    def use_dotnet(self) -> bool:
        return self.settings.get("runtime") == "dotnet"

    @property
    def editor(self):
        return self.tabs.get_active_editor() if hasattr(self, "tabs") else None

    def _t(self, key: str, **kw) -> str:
        return tr(self.lang, key, **kw)

    def _log(self, key: str, **kw) -> None:
        self.log_box.write(self._t(key, **kw))

    def _log_file_error(self, code: str, name: str = "") -> None:
        if code == "exists":
            self._log("log_exists", name=name)
        elif code == "bad_name":
            self._log("log_bad_name")
        else:
            self._log("log_io_error", err=code.removeprefix("io:"))

    def _template_text(self) -> str:
        return templates.template_code(self.settings.get("start_template", "hello"))

    def _initial_file(self) -> str:
        d = self.projects_dir
        existing = files.project_files(d)
        last = self.settings.get("last_file", "")
        if last and last in existing:
            return os.path.join(d, last)
        if "main.pas" in existing:
            return os.path.join(d, "main.pas")
        if existing:
            return os.path.join(d, existing[0])
        main = os.path.join(d, "main.pas")
        files.write_text(main, self._template_text())
        return main

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_layout"):
            with Vertical(id="workspace"):
                yield Label(
                    self._t("active_file", name=os.path.basename(self.current_file)),
                    id="cur_file_lbl",
                )
                yield TabBar(id="tab_plus")
                self.tabs = EditorTabs(self.engine, self.settings, id="editor_tabs")
                yield self.tabs
                self.popup = CompletionPopup(id="completion_popup")
                yield self.popup
            with Horizontal(id="buttons_container"):
                n = len(files.project_files(self.projects_dir))
                yield Button(self._t("btn_projects", n=n), variant="primary", id="open_menu_btn")
                yield Button(self._t("btn_run"), variant="success", id="run_btn")
                yield Button(self._t("btn_settings"), variant="default", id="settings_btn")
            self.log_box = RichLog(wrap=True, id="log_box")
            yield self.log_box
        try:
            footer = Footer(show_command_palette=False)
        except TypeError:
            footer = Footer()
        yield footer

    def on_mount(self) -> None:
        for data in self._theme_defs.values():
            self._register_theme_quiet(data)
        self.apply_theme(self.settings.get("theme", "pascal-dark"))
        self.tabs.attach_popup(self.popup)
        text, _err = files.read_text(self.current_file)
        self.tabs.open_file_tab(self.current_file, text or self._template_text(),
                                label=self._tab_label(self.current_file))
        self.tabs.apply_settings(self.settings, self._editor_theme_name())
        self._update_titles()
        self.tabs.get_active_editor().focus()
        self.open_files = [os.path.basename(self.current_file)]
        self.file_texts[os.path.basename(self.current_file)] = self.editor.text if self.editor else ""

    def _update_titles(self) -> None:
        self.title = self._t("app_title")
        active = self.tabs.get_active_file_name() if hasattr(self, "tabs") else ""
        self.sub_title = active or os.path.basename(self.current_file)

    def _register_theme_quiet(self, data: dict) -> bool:
        theme = themes.to_textual_theme(data)
        if theme is None:
            return False
        try:
            self.register_theme(theme)
        except Exception:
            return False
        return True

    def theme_names(self) -> list[str]:
        try:
            return sorted(self.available_themes)
        except Exception:
            return sorted(self._theme_defs)

    def is_user_theme(self, name: str) -> bool:
        return bool(self._theme_defs.get(name, {}).get("_user", False))

    def theme_data(self, name: str) -> dict:
        if name in self._theme_defs:
            return {k: v for k, v in self._theme_defs[name].items() if not k.startswith("_")}
        data: dict = {"name": name, "dark": True, "editor_theme": "css"}
        try:
            theme = self.available_themes[name]
            data["dark"] = bool(getattr(theme, "dark", True))
            for key in themes.COLOR_KEYS + themes.OPTIONAL_COLOR_KEYS:
                value = themes.normalize_hex(getattr(theme, key, None))
                if value:
                    data[key] = value
        except Exception:
            pass
        return data

    def register_user_theme(self, data: dict) -> bool:
        if not self._register_theme_quiet(data):
            return False
        entry = dict(data)
        entry["_user"] = True
        self._theme_defs[entry["name"]] = entry
        return True

    def remove_user_theme(self, name: str) -> None:
        themes.delete_user_theme(name)
        try:
            self.unregister_theme(name)
        except Exception:
            pass
        self._theme_defs = themes.load_all()
        for data in self._theme_defs.values():
            self._register_theme_quiet(data)
        if getattr(self, "theme", None) == name:
            self.apply_theme(DEFAULT_THEME_FALLBACK)
        self._log("log_theme_deleted", name=name)

    def _editor_theme_name(self) -> str:
        choice = self.settings.get("editor_theme", "auto")
        if choice != "auto":
            return choice
        data = self._theme_defs.get(getattr(self, "theme", ""))
        return data.get("editor_theme", "css") if data else "css"

    def apply_theme(self, name: str) -> None:
        if name in self.theme_names():
            try:
                self.theme = name
            except Exception:
                pass
        try:
            self.tabs.apply_settings(self.settings, self._editor_theme_name())
        except Exception:
            pass

    def preview_theme(self, name: str) -> None:
        self.apply_theme(name)

    def _persist_settings(self) -> None:
        err = save_settings(self.settings)
        if err:
            self._log("log_settings_err", err=err)

    def _retranslate_bindings(self) -> None:
        try:
            for binding in make_bindings(self.lang):
                if binding.show:
                    self._bindings.key_to_bindings[binding.key] = [binding]
            self.refresh_bindings()
        except Exception:
            pass

    def _refresh_static_labels(self) -> None:
        n = len(files.project_files(self.projects_dir))
        self.query_one("#cur_file_lbl", Label).update(
            self._t("active_file", name=os.path.basename(self.current_file))
        )
        self.query_one("#open_menu_btn", Button).label = self._t("btn_projects", n=n)
        self.query_one("#run_btn", Button).label = self._t("btn_run")
        self.query_one("#settings_btn", Button).label = self._t("btn_settings")
        self._update_titles()

    def action_settings(self) -> None:
        if len(self.screen_stack) > 1:
            return
        if self.editor:
            self.editor.hide_popup()
        self.action_command_palette()

    def apply_changes(self, changes: dict) -> None:
        old_lang = self.lang
        self.settings = sanitize({**self.settings, **changes}, self.settings)
        self.lang = self.settings["language"]
        self._persist_settings()
        if "theme" in changes:
            self.apply_theme(self.settings["theme"])
        if self.editor:
            self.tabs.apply_settings(self.settings, self._editor_theme_name())
        if self.lang != old_lang:
            self._retranslate_bindings()
        self._refresh_static_labels()
        self._log("log_settings_saved")

    def action_set_option(self, key: str, value) -> None:
        self.apply_changes({key: value})

    def action_toggle_option(self, key: str) -> None:
        self.apply_changes({key: not self.settings.get(key, False)})

    def action_open_themes(self) -> None:
        self.push_screen(
            ThemesScreen(self.lang, self.settings, getattr(self, "theme", DEFAULT_THEME_FALLBACK)),
            lambda r: self.apply_changes(r) if r else None,
        )

    def action_open_autocomplete(self) -> None:
        self.push_screen(
            AutocompleteScreen(self.lang, self.settings),
            lambda r: self.apply_changes(r) if r else None,
        )

    def action_open_general(self) -> None:
        self.push_screen(
            GeneralScreen(self.lang, self.settings),
            lambda r: self.apply_changes(r) if r else None,
        )

    def action_open_run(self) -> None:
        self.push_screen(RunScreen(self.lang, self.settings), self._apply_run)

    def _apply_run(self, result: dict | None) -> None:
        if not result:
            return
        changes = {k: result[k] for k in ("runtime", "compile_timeout") if k in result}
        compiler = os.path.expanduser(result.get("compiler_path", self.compiler_path))
        if compiler != self.compiler_path:
            if os.path.exists(compiler):
                changes["compiler_path"] = compiler
            else:
                self._log("log_compiler_not_found_path", path=compiler)
        projects = os.path.expanduser(result.get("projects_dir", self.projects_dir))
        switch = False
        if projects != self.projects_dir:
            try:
                os.makedirs(projects, exist_ok=True)
                changes["projects_dir"] = projects
                switch = True
            except OSError:
                self._log("log_projects_not_found_path", path=projects)
        if switch:
            self.save_current_file()
        self.apply_changes(changes)
        if switch:
            self.save_all_files()
            self.tabs.close_all()
            self.current_file = self._initial_file()
            self._load_current_into_editor()
            self._refresh_static_labels()

    def _prompt(self, title_key: str, default: str, callback) -> None:
        self.push_screen(
            InputDialog(
                title=self._t(title_key),
                placeholder=default,
                default=default,
                ok_label=self._t("dlg_ok"),
                cancel_label=self._t("dlg_cancel"),
            ),
            callback,
        )

    def action_prompt_tab_width(self) -> None:
        self._prompt("dlg_tab_width_title", str(self.settings.get("tab_width", 2)), self._apply_tab_width)

    def _apply_tab_width(self, value: str | None) -> None:
        if value and value.isdigit():
            self.apply_changes({"tab_width": int(value)})

    def action_prompt_compiler_path(self) -> None:
        self._prompt("dlg_compiler_title", self.compiler_path, self._apply_compiler_path)

    def _apply_compiler_path(self, path: str | None) -> None:
        if not path:
            return
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            self._log("log_compiler_not_found_path", path=path)
            return
        self.apply_changes({"compiler_path": path})

    def action_prompt_projects_dir(self) -> None:
        self._prompt("dlg_projects_title", self.projects_dir, self._apply_projects_dir)

    def _apply_projects_dir(self, path: str | None) -> None:
        if not path:
            return
        path = os.path.expanduser(path)
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            self._log("log_projects_not_found_path", path=path)
            return
        self.save_all_files()
        self.apply_changes({"projects_dir": path})
        self.tabs.close_all()
        self.current_file = self._initial_file()
        self._load_current_into_editor()
        self._refresh_static_labels()

    def action_show_paths(self) -> None:
        self._log("log_paths", script=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tui")),
                  compiler=self.compiler_path, projects=self.projects_dir, config=str(SETTINGS_PATH))

    def _tab_label(self, path: str) -> str:
        """Подпись вкладки: имя файла; если такое имя уже открыто — путь от папки проектов."""
        base = os.path.basename(path)
        same = [p for p in self.tabs.open_paths() if os.path.basename(p) == base and os.path.abspath(p) != os.path.abspath(path)]
        if same:
            return os.path.relpath(path, self.projects_dir).replace(os.sep, "/")
        return base

    def save_current_file(self, notify: bool = False) -> bool:
        """Сохраняет открытую вкладку в её собственный файл (а не в «последний открытый»)."""
        ed = self.editor
        path = self.tabs.active_path() if hasattr(self, "tabs") else None
        if not ed or not path:
            return True
        err = files.write_text(path, ed.text)
        if err:
            self._log("log_save_err", err=err)
            return False
        if notify:
            self._log("log_saved", name=os.path.basename(path))
        self.file_texts[os.path.basename(path)] = ed.text
        return True

    def save_all_files(self) -> bool:
        """Сохраняет все открытые вкладки (модули в соседних вкладках нужны компилятору)."""
        ok = True
        for path, ed in self.tabs.open_editors():
            err = files.write_text(path, ed.text)
            if err:
                self._log("log_save_err", err=err)
                ok = False
        return ok

    def action_save(self) -> None:
        self.save_current_file(notify=True)

    def _load_current_into_editor(self) -> None:
        text, err = files.read_text(self.current_file)
        if err:
            self._log("log_read_err", err=err)
            return
        self.tabs.open_file_tab(self.current_file, text, label=self._tab_label(self.current_file), reload=True)
        name = os.path.basename(self.current_file)
        self.file_texts[name] = text
        if name not in self.open_files:
            self.open_files.append(name)

    def _remember_last_file(self) -> None:
        self.settings["last_file"] = os.path.relpath(self.current_file, self.projects_dir).replace(os.sep, "/")
        save_settings(self.settings)

    def open_file(self, name: str, new_tab: bool = True) -> None:
        path = os.path.join(self.projects_dir, name)
        text, err = files.read_text(path)
        if err:
            self._log("log_read_err", err=err)
            return
        self.save_current_file()
        self.current_file = path
        self.tabs.open_file_tab(path, text, new_tab=new_tab, label=self._tab_label(path))
        basename = os.path.basename(path)
        self.file_texts[basename] = text
        if basename not in self.open_files:
            self.open_files.append(basename)
        self._remember_last_file()
        self._refresh_static_labels()
        self._log("log_opened", name=name)

    async def action_quit(self) -> None:
        if self.settings.get("save_on_quit", True):
            self.save_all_files()
        self.exit()

    def action_close_tab(self) -> None:
        if not hasattr(self, "tabs") or not self.tabs.active:
            return
        if len(self.tabs.open_paths()) <= 1:  # последнюю вкладку не закрываем — редактор не должен остаться пустым
            return
        self.save_current_file()  # правки не теряем
        self.tabs.close_file_tab(self.tabs.active)
        # current_file обновится в on_tabbed_content_tab_activated, когда Textual выберет соседнюю вкладку

    def on_tabbed_content_tab_activated(self, event) -> None:
        """Переключили вкладку (в том числе нажатием): current_file должен совпасть с ней."""
        path = self.tabs.active_path() if hasattr(self, "tabs") else None
        if not path or path == self.current_file:
            return
        self.current_file = path
        try:
            self._remember_last_file()
            self._refresh_static_labels()
        except Exception:  # noqa: BLE001 — экран ещё не готов (первая вкладка при запуске)
            pass

    def action_open_menu(self, new_tab: bool = False) -> None:
        if len(self.screen_stack) > 1:
            return
        if self.editor:
            self.editor.hide_popup()
        self.save_all_files()
        self.push_screen(
            FileMenuScreen(self.projects_dir, self.lang, os.path.basename(self.current_file), new_tab),
            self.handle_menu_result,
        )

    def _reopen_menu(self) -> None:
        self._refresh_static_labels()
        self.action_open_menu()

    def handle_menu_result(self, result) -> None:
        if not result:
            self._refresh_static_labels()
            return
        action, name, new_tab = result

        if action == "select":
            self.open_file(name, new_tab=new_tab)
        elif action == "create_file":
            auto = files.auto_filename(self.projects_dir)
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_create_title"),
                    placeholder=auto,
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                    allow_empty=True,
                ),
                lambda value, a=auto, d=name, nt=new_tab: self._do_create_file(value, a, d, nt),
            )
        elif action == "create_dir":
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_create_dir_title"),
                    placeholder="folder_name",
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                    allow_empty=False,
                ),
                lambda value, d=name, nt=new_tab: self._do_create_dir(value, d, nt),
            )
        elif action.startswith("delete_"):
            is_dir = action.endswith("_dir")
            base_name = os.path.basename(name)
            msg = f"🗑️ Delete folder '{base_name}'?" if is_dir else self._t("dlg_delete_title", name=base_name)
            self.push_screen(
                ConfirmDialog(msg, yes_label=self._t("dlg_yes"), no_label=self._t("dlg_no")),
                lambda ok, n=name, isd=is_dir: self._do_delete(n, bool(ok), isd),
            )
        elif action.startswith("rename_"):
            is_dir = action.endswith("_dir")
            base_name = os.path.basename(name)
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_rename_title", name=base_name),
                    placeholder="new_name",
                    default=os.path.splitext(base_name)[0],
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                ),
                lambda value, n=name, isd=is_dir: self._do_rename(n, value, isd),
            )
        elif action.startswith("copy_"):
            is_dir = action.endswith("_dir")
            base_name = os.path.basename(name)
            suggestion = f"{os.path.splitext(base_name)[0]}_copy"
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_copy_title", name=base_name),
                    placeholder=suggestion,
                    default=suggestion,
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                ),
                lambda value, n=name, isd=is_dir: self._do_copy(n, value, isd),
            )
        elif action == "clear":
            self.code_backup = self.editor.text if self.editor else ""
            if self.editor:
                self.editor.text = templates.empty_code()
        elif action == "undo":
            if self.code_backup and self.editor:
                self.editor.text = self.code_backup

    def _do_create_file(self, value: str | None, auto: str, subdir: str, new_tab: bool) -> None:
        if value is None:
            self._reopen_menu()
            return
        name = value or auto
        base = self.projects_dir if subdir == "." else os.path.join(self.projects_dir, subdir)
        path, err = files.create_file(base, name, self._template_text())
        if err:
            self._log_file_error(err, name)
        else:
            self.open_file(os.path.relpath(path, self.projects_dir), new_tab=True)
            self._log("log_created", name=os.path.basename(path))
        self._reopen_menu()

    def _do_create_dir(self, value: str | None, subdir: str, new_tab: bool) -> None:
        if value is None:
            self._reopen_menu()
            return
        base = self.projects_dir if subdir == "." else os.path.join(self.projects_dir, subdir)
        path, err = files.create_dir(base, value)
        if err:
            self._log_file_error(err, value)
        else:
            self._log("log_dir_created", name=value)
        self._reopen_menu()

    def _do_delete(self, rel_path: str, confirmed: bool, is_dir: bool) -> None:
        if not confirmed:
            self._reopen_menu()
            return
        target = os.path.join(self.projects_dir, rel_path)
        base = os.path.dirname(target)
        name = os.path.basename(rel_path)
        err = files.delete_dir(base, name) if is_dir else files.delete_file(base, name)
        if err:
            self._log_file_error(err, name)
        else:
            self._log("log_deleted", name=name)
            was_current = is_inside(self.current_file, target)
            self.tabs.close_under(target)  # иначе вкладка «воскресит» удалённый файл при сохранении
            if not self.tabs.open_paths():
                remaining = files.all_project_files(self.projects_dir) if hasattr(files, "all_project_files") else files.project_files(self.projects_dir)
                if remaining:
                    self.open_file(remaining[0], new_tab=True)
                else:
                    self.current_file = os.path.join(self.projects_dir, "main.pas")
                    files.write_text(self.current_file, self._template_text())
                    self._load_current_into_editor()
                self._remember_last_file()
            elif was_current:
                self.current_file = self.tabs.active_path() or self.current_file
                self._remember_last_file()
        self._reopen_menu()

    def _do_rename(self, rel_path: str, new_name: str | None, is_dir: bool) -> None:
        if new_name:
            old_abs = os.path.join(self.projects_dir, rel_path)
            base = os.path.dirname(old_abs)
            old = os.path.basename(rel_path)
            if is_dir:
                path, err = files.rename_dir(base, old, new_name)
            else:
                path, err = files.rename_file(base, old, new_name)
            if err:
                self._log_file_error(err, new_name)
            else:
                self._log("log_renamed", old=old, new=os.path.basename(path))
                was_current = is_inside(self.current_file, old_abs)
                tail = os.path.relpath(self.current_file, old_abs) if was_current else None
                self.tabs.close_under(old_abs)  # вкладки со старыми путями закрываем (файлы уже сохранены)
                if was_current:
                    target = path if tail == "." else os.path.join(path, tail)
                    self.open_file(os.path.relpath(target, self.projects_dir), new_tab=True)
                elif not self.tabs.open_paths():
                    self.open_file(os.path.relpath(path, self.projects_dir), new_tab=True)
        self._reopen_menu()

    def _do_copy(self, rel_path: str, new_name: str | None, is_dir: bool) -> None:
        if new_name:
            base = os.path.dirname(os.path.join(self.projects_dir, rel_path))
            src = os.path.basename(rel_path)
            if is_dir:
                path, err = files.copy_dir(base, src, new_name)
            else:
                path, err = files.copy_file(base, src, new_name)
            if err:
                self._log_file_error(err, new_name)
            else:
                self._log("log_copied", old=src, new=os.path.basename(path))
        self._reopen_menu()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "new_tab_btn":
            self.action_open_menu(new_tab=True)
            return
        if bid == "open_menu_btn":
            self.action_open_menu()
        elif bid == "run_btn":
            self.action_run()
        elif bid == "settings_btn":
            self.action_settings()

    def action_run(self) -> None:
        if len(self.screen_stack) > 1:
            return
        if self._busy:
            self._log("log_busy")
            return
        self._run_current_file()

    @work(exclusive=True)
    async def _run_current_file(self) -> None:
        self._busy = True
        try:
            if self.editor:
                self.editor.hide_popup()
            self.log_box.clear()
            self.save_all_files()
            source = self.tabs.active_path() or self.current_file
            self._log("log_compiling", name=os.path.basename(source))
            compiler = self.compiler_path
            if not os.path.exists(compiler):
                searched = "\n".join(os.path.join(d, COMPILER_FILE) for d in candidate_share_dirs())
                self._log("log_no_compiler", paths=searched)
                return
            timeout = int(self.settings.get("compile_timeout", 60))
            res = await asyncio.to_thread(runner.compile_pascal, compiler, source, timeout)
            if res.error == "no_mono":
                self._log("log_no_mono")
                return
            if res.error == "timeout":
                self._log("log_timeout", sec=timeout)
                return
            if res.error:
                self._log("log_io_error", err=res.error.removeprefix("os:"))
                return
            if not res.ok:
                self._log("log_compile_err")
                if res.stdout:
                    self.log_box.write(res.stdout)
                if res.stderr:
                    self.log_box.write(res.stderr)
                return
            exe = runner.exe_path(source)
            self._log("log_compiled_ok")
            if self.use_dotnet:
                err = runner.write_runtime_config(exe, runtime_config())
                if err:
                    self._log("log_runtimeconfig_err", err=err)
                else:
                    self._log("log_runtimeconfig")
            with self.suspend():
                self._run_in_terminal(exe)
        finally:
            self._busy = False
            if self.editor:
                try:
                    self.editor.focus()
                except Exception:
                    pass

    def _run_in_terminal(self, exe: str) -> None:
        os.system("clear")
        print(self._t("run_header"))
        print(self._t("run_running", name=os.path.basename(exe)))
        err = runner.run_program(exe, self.settings.get("runtime", "mono"))
        if err == "no_mono":
            print(self._t("log_no_mono"))
        elif err == "no_dotnet":
            print(self._t("log_no_dotnet"))
        elif err:
            print(self._t("run_exc", e=err))
        print(self._t("run_footer"))
        try:
            input(self._t("run_enter"))
        except EOFError:
            pass


def main() -> None:
    PascalTUI().run()