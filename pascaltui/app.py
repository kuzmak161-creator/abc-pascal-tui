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
from .settings import load_settings, runtime_config, sanitize, save_settings

DEFAULT_THEME_FALLBACK = "textual-dark"


def make_bindings(lang: str) -> list[Binding]:
    """Горячие клавиши с переведёнными подписями для Footer."""
    return [
        Binding("ctrl+q", "quit", tr(lang, "footer_quit"), key_display="^Q", priority=True),
        Binding("ctrl+o", "open_menu", tr(lang, "footer_open_menu"), key_display="^O"),
        Binding("ctrl+r", "run", tr(lang, "footer_run"), key_display="^R"),
        Binding("ctrl+s", "save", tr(lang, "footer_save"), key_display="^S"),
        Binding("f2", "settings", tr(lang, "footer_settings"), key_display="F2"),
        # короткие клавиши как в старой версии (работают, когда фокус не в редакторе)
        Binding("q", "quit", "", show=False),
        Binding("o", "open_menu", "", show=False),
        Binding("s", "settings", "", show=False),
    ]


# Язык нужен уже на этапе объявления класса — Footer читает BINDINGS при старте.
_INITIAL_LANG = load_settings().get("language", "ru")


class PascalTUI(App):
    # Только наши команды: встроенные английские (Theme, Keys, Screenshot...) убраны —
    # тема теперь одна, в разделе «Оформление и темы».
    COMMANDS = {SettingsCommands}
    BINDINGS = make_bindings(_INITIAL_LANG)

    CSS = """
    #main_layout {
        layout: vertical;
    }
    #workspace {
        height: 3fr;
    }
    #buttons_container {
        height: 3;
        margin-top: 1;
        margin-bottom: 1;
    }
    #log_box {
        height: 1fr;
        min-height: 4;
    }
    Button {
        margin-right: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.lang: str = self.settings["language"]
        self.engine = CompletionEngine.from_files()
        self._theme_defs: dict[str, dict] = themes.load_all()
        self.code_backup = ""
        self._busy = False

        try:
            os.makedirs(self.projects_dir, exist_ok=True)
        except OSError:
            pass
        self.current_file = self._initial_file()

    # ------------------------------------------------------
    # свойства-«ярлыки»
    # ------------------------------------------------------
    @property
    def projects_dir(self) -> str:
        return os.path.expanduser(self.settings["projects_dir"])

    @property
    def compiler_path(self) -> str:
        return os.path.expanduser(self.settings["compiler_path"])

    @property
    def use_dotnet(self) -> bool:
        return self.settings.get("runtime") == "dotnet"

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

    # ------------------------------------------------------
    # старт
    # ------------------------------------------------------
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
                text, _err = files.read_text(self.current_file)
                self.editor = make_editor(text or self._template_text(), self.engine, self.settings, id="editor")
                yield self.editor
                self.popup = CompletionPopup(id="completion_popup")
                yield self.popup
            with Horizontal(id="buttons_container"):
                n = len(files.project_files(self.projects_dir))
                yield Button(self._t("btn_projects", n=n), variant="primary", id="open_menu_btn")
                yield Button(self._t("btn_run"), variant="success", id="run_btn")
                yield Button(self._t("btn_settings"), variant="default", id="settings_btn")
            self.log_box = RichLog(wrap=True, id="log_box")
            yield self.log_box
        try:  # убираем английскую кнопку "palette" — вместо неё переведённая F2
            footer = Footer(show_command_palette=False)
        except TypeError:
            footer = Footer()
        yield footer

    def on_mount(self) -> None:
        for data in self._theme_defs.values():
            self._register_theme_quiet(data)
        self.apply_theme(self.settings.get("theme", "pascal-dark"))
        self.editor.attach_popup(self.popup)
        self.editor.apply_settings(self.settings, self._editor_theme_name())
        self._update_titles()
        self.editor.focus()

    def _update_titles(self) -> None:
        self.title = self._t("app_title")
        self.sub_title = os.path.basename(self.current_file)

    # ------------------------------------------------------
    # темы
    # ------------------------------------------------------
    def _register_theme_quiet(self, data: dict) -> bool:
        theme = themes.to_textual_theme(data)
        if theme is None:
            return False
        try:
            self.register_theme(theme)
        except Exception:  # noqa: BLE001
            return False
        return True

    def theme_names(self) -> list[str]:
        try:
            return sorted(self.available_themes)
        except Exception:  # noqa: BLE001
            return sorted(self._theme_defs)

    def is_user_theme(self, name: str) -> bool:
        return bool(self._theme_defs.get(name, {}).get("_user", False))

    def theme_data(self, name: str) -> dict:
        """Описание темы для редактора (из JSON или из встроенной темы Textual)."""
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
        except Exception:  # noqa: BLE001
            pass
        return data

    def register_user_theme(self, data: dict) -> bool:
        """Вызывается редактором тем после сохранения файла."""
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
        except Exception:  # noqa: BLE001
            pass
        self._theme_defs = themes.load_all()  # вдруг под этим именем есть встроенная
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
            except Exception:  # noqa: BLE001
                pass
        try:
            self.editor.apply_settings(self.settings, self._editor_theme_name())
        except Exception:  # noqa: BLE001
            pass

    def preview_theme(self, name: str) -> None:
        """Предпросмотр из экрана настроек (без сохранения)."""
        self.apply_theme(name)

    # ------------------------------------------------------
    # настройки
    # ------------------------------------------------------
    def _persist_settings(self) -> None:
        err = save_settings(self.settings)
        if err:
            self._log("log_settings_err", err=err)

    def _retranslate_bindings(self) -> None:
        """Обновляет подписи в Footer после смены языка (без перезапуска)."""
        try:
            for binding in make_bindings(self.lang):
                if binding.show:
                    self._bindings.key_to_bindings[binding.key] = [binding]
            self.refresh_bindings()
        except Exception:  # noqa: BLE001
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
        self.editor.hide_popup()
        self.action_command_palette()

    def apply_changes(self, changes: dict) -> None:
        """Применяет и сохраняет изменённые настройки."""
        old_lang = self.lang
        self.settings = sanitize({**self.settings, **changes}, self.settings)
        self.lang = self.settings["language"]
        self._persist_settings()
        if "theme" in changes:
            self.apply_theme(self.settings["theme"])
        self.editor.apply_settings(self.settings, self._editor_theme_name())
        if self.lang != old_lang:
            self._retranslate_bindings()
        self._refresh_static_labels()
        self._log("log_settings_saved")

    # --- действия палитры команд ---
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
        self.save_current_file()
        self.apply_changes({"projects_dir": path})
        self.current_file = self._initial_file()
        self._load_current_into_editor()
        self._refresh_static_labels()

    def action_show_paths(self) -> None:
        self._log("log_paths", script=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tui")),
                  compiler=self.compiler_path, projects=self.projects_dir, config=str(SETTINGS_PATH))

    # ------------------------------------------------------
    # файлы
    # ------------------------------------------------------
    def save_current_file(self, notify: bool = False) -> bool:
        if not self.current_file:
            return True
        err = files.write_text(self.current_file, self.editor.text)
        if err:
            self._log("log_save_err", err=err)
            return False
        if notify:
            self._log("log_saved", name=os.path.basename(self.current_file))
        return True

    def action_save(self) -> None:
        self.save_current_file(notify=True)

    def _load_current_into_editor(self) -> None:
        text, err = files.read_text(self.current_file)
        if err:
            self._log("log_read_err", err=err)
            return
        self.editor.text = text

    def _remember_last_file(self) -> None:
        self.settings["last_file"] = os.path.basename(self.current_file)
        save_settings(self.settings)

    def open_file(self, name: str) -> None:
        path = os.path.join(self.projects_dir, name)
        text, err = files.read_text(path)
        if err:
            self._log("log_read_err", err=err)
            return
        self.current_file = path
        self.editor.text = text
        self._remember_last_file()
        self._refresh_static_labels()
        self._log("log_opened", name=name)

    async def action_quit(self) -> None:
        if self.settings.get("save_on_quit", True):
            self.save_current_file()
        self.exit()

    # ------------------------------------------------------
    # меню проектов
    # ------------------------------------------------------
    def action_open_menu(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self.editor.hide_popup()
        self.save_current_file()
        self.push_screen(
            FileMenuScreen(self.projects_dir, self.lang, os.path.basename(self.current_file)),
            self.handle_menu_result,
        )

    def _reopen_menu(self) -> None:
        self._refresh_static_labels()
        self.action_open_menu()

    def handle_menu_result(self, result) -> None:
        if not result:
            self._refresh_static_labels()
            return
        action, name = result

        if action == "select":
            self.open_file(name)
        elif action == "create":
            auto = files.auto_filename(self.projects_dir)
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_create_title"),
                    placeholder=auto,
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                    allow_empty=True,
                ),
                lambda value, a=auto: self._do_create(value, a),
            )
        elif action == "delete":
            self.push_screen(
                ConfirmDialog(
                    self._t("dlg_delete_title", name=name),
                    yes_label=self._t("dlg_yes"),
                    no_label=self._t("dlg_no"),
                ),
                lambda ok, n=name: self._do_delete(n, bool(ok)),
            )
        elif action == "rename":
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_rename_title", name=name),
                    placeholder="new_name",
                    default=os.path.splitext(name)[0],
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                ),
                lambda value, n=name: self._do_rename(n, value),
            )
        elif action == "copy":
            suggestion = f"{os.path.splitext(name)[0]}_copy"
            self.push_screen(
                InputDialog(
                    title=self._t("dlg_copy_title", name=name),
                    placeholder=suggestion,
                    default=suggestion,
                    ok_label=self._t("dlg_ok"),
                    cancel_label=self._t("dlg_cancel"),
                ),
                lambda value, n=name: self._do_copy(n, value),
            )
        elif action == "clear":
            self.code_backup = self.editor.text
            self.editor.text = templates.empty_code()
        elif action == "undo":
            if self.code_backup:
                self.editor.text = self.code_backup

    def _do_create(self, value: str | None, auto: str) -> None:
        if value is None:  # Отмена — ничего не создаём (раньше создавался файл с авто-именем)
            self._reopen_menu()
            return
        name = value or auto
        path, err = files.create_file(self.projects_dir, name, self._template_text())
        if err:
            self._log_file_error(err, name)
        else:
            self.current_file = path
            self._load_current_into_editor()
            self._remember_last_file()
            self._log("log_created", name=os.path.basename(path))
        self._reopen_menu()

    def _do_delete(self, name: str, confirmed: bool) -> None:
        if confirmed:
            err = files.delete_file(self.projects_dir, name)
            if err:
                self._log_file_error(err, name)
            else:
                self._log("log_deleted", name=name)
                # переключаемся, только если удалили ОТКРЫТЫЙ файл (раньше переключало всегда)
                if os.path.basename(self.current_file) == name:
                    remaining = files.project_files(self.projects_dir)
                    if remaining:
                        self.current_file = os.path.join(self.projects_dir, remaining[0])
                    else:
                        self.current_file = os.path.join(self.projects_dir, "main.pas")
                        files.write_text(self.current_file, self._template_text())
                    self._load_current_into_editor()
                    self._remember_last_file()
        self._reopen_menu()

    def _do_rename(self, old_name: str, new_name: str | None) -> None:
        if new_name:
            path, err = files.rename_file(self.projects_dir, old_name, new_name)
            if err:
                self._log_file_error(err, new_name)
            else:
                new_base = os.path.basename(path)
                if os.path.basename(self.current_file) == old_name:
                    self.current_file = path
                    self._remember_last_file()
                self._log("log_renamed", old=old_name, new=new_base)
        self._reopen_menu()

    def _do_copy(self, src_name: str, new_name: str | None) -> None:
        if new_name:
            path, err = files.copy_file(self.projects_dir, src_name, new_name)
            if err:
                self._log_file_error(err, new_name)
            else:
                self._log("log_copied", old=src_name, new=os.path.basename(path))
        self._reopen_menu()

    # ------------------------------------------------------
    # кнопки
    # ------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open_menu_btn":
            self.action_open_menu()
        elif event.button.id == "run_btn":
            self.action_run()
        elif event.button.id == "settings_btn":
            self.action_settings()

    # ------------------------------------------------------
    # запуск
    # ------------------------------------------------------
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
            self.editor.hide_popup()
            self.log_box.clear()
            self.save_current_file()
            source = self.current_file
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
            try:
                self.editor.focus()
            except Exception:  # noqa: BLE001
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

    # ------------------------------------------------------


def main() -> None:
    PascalTUI().run()
