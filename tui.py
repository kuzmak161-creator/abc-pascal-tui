import subprocess
import os
import shutil
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Button, TextArea, RichLog, RadioSet, RadioButton, Label, ListView, ListItem, Input
from textual.containers import Horizontal, Vertical

TEMPLATE_HELLO_WORLD = "begin\n  writeln('Hello World');\nend."
TEMPLATE_EMPTY = "begin\n  \nend."

# ==========================================================
# ДИНАМИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПУТЕЙ
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILER_PATH = os.path.join(BASE_DIR, "pabcnetc.exe")
PROJECTS_DIR = os.path.join(BASE_DIR, "Projects")
# ==========================================================

RUNTIME_CONFIG_TEMPLATE = """{
  "runtimeOptions": {
    "tfm": "net472",
    "framework": {
      "name": "Microsoft.NETCore.App",
      "version": "8.0.0"
    }
  }
}"""

def get_project_files() -> list[str]:
    if not os.path.exists(PROJECTS_DIR):
        return []
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(".pas")]
    files.sort()
    return files

def create_runtime_config(exe_path: str) -> None:
    config_path = exe_path.replace(".exe", ".runtimeconfig.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(RUNTIME_CONFIG_TEMPLATE)
    except Exception as e:
        print(f"[Ошибка создания конфига]: {e}")

def get_auto_filename() -> str:
    """Автоматически генерирует имя project_N"""
    count = 1
    while os.path.exists(os.path.join(PROJECTS_DIR, f"project_{count}.pas")):
        count += 1
    return f"project_{count}"

# ==========================================================
# ДИАЛОГ ВВОДА ИМЕНИ ФАЙЛА (для создания и переименования)
# ==========================================================
class InputDialog(ModalScreen):
    """Простой диалог с полем ввода"""

    CSS = """
    InputDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #dialog_container {
        width: 50;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }
    #dialog_input {
        margin-top: 1;
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: 3;
    }
    .dialog_btn {
        margin-right: 1;
    }
    """

    def __init__(self, title: str, placeholder: str = "", default: str = ""):
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_container"):
            yield Label(self._title)
            yield Input(
                value=self._default,
                placeholder=self._placeholder,
                id="dialog_input"
            )
            with Horizontal(id="dialog_buttons"):
                yield Button("✅ ОК", variant="success", id="dialog_ok", classes="dialog_btn")
                yield Button("❌ Отмена", variant="default", id="dialog_cancel", classes="dialog_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dialog_ok":
            value = self.query_one("#dialog_input", Input).value.strip()
            self.dismiss(value if value else None)
        elif event.button.id == "dialog_cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value if value else None)


# ==========================================================
# ГЛАВНЫЙ ФАЙЛОВЫЙ МЕНЕДЖЕР
# ==========================================================
class FileMenuScreen(ModalScreen):
    """Улучшенный файловый менеджер"""

    CSS = """
    FileMenuScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #menu_container {
        width: 48;
        height: 80%;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }
    #search_input {
        margin-bottom: 1;
    }
    #menu_file_list {
        background: $surface;
        border: solid $primary;
        height: 1fr;
        margin-bottom: 1;
    }
    .menu_btn {
        width: 100%;
        margin-bottom: 1;
    }
    #btn_row1 {
        height: 3;
        margin-bottom: 1;
    }
    #btn_row2 {
        height: 3;
        margin-bottom: 1;
    }
    .half_btn {
        width: 1fr;
        margin-right: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._all_files = get_project_files()

    def compose(self) -> ComposeResult:
        with Vertical(id="menu_container"):
            yield Label("📁 ФАЙЛОВЫЙ МЕНЕДЖЕР:")
            yield Input(placeholder="🔍 Поиск...", id="search_input")

            items = [
                ListItem(Label(f" 📄 {f}"), id=f"file_idx_{i}")
                for i, f in enumerate(self._all_files)
            ]
            yield ListView(*items, id="menu_file_list")

            with Horizontal(id="btn_row1"):
                yield Button("➕ Новый файл", variant="primary", id="menu_create_btn", classes="half_btn")
                yield Button("📋 Копировать", variant="default", id="menu_copy_btn", classes="half_btn")

            with Horizontal(id="btn_row2"):
                yield Button("✏️ Переименовать", variant="warning", id="menu_rename_btn", classes="half_btn")
                yield Button("🗑️ Удалить", variant="error", id="menu_delete_btn", classes="half_btn")

            yield Button("❌ Закрыть меню", variant="default", id="menu_close_btn", classes="menu_btn")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Живой поиск по файлам"""
        if event.input.id != "search_input":
            return
        query = event.value.lower().strip()

        filtered = [
            f for f in self._all_files
            if query in f.lower()
        ] if query else self._all_files

        async def rebuild():
            file_list = self.query_one("#menu_file_list", ListView)
            await file_list.clear()
            for f in filtered:
                orig_idx = self._all_files.index(f)
                await file_list.append(ListItem(Label(f" 📄 {f}"), id=f"file_idx_{orig_idx}"))

        self.call_after_refresh(rebuild)

    def _get_highlighted_id(self) -> str | None:
        file_list = self.query_one("#menu_file_list", ListView)
        if file_list.highlighted_child and file_list.highlighted_child.id:
            return file_list.highlighted_child.id
        return None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id:
            self.dismiss(("select", event.item.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "menu_close_btn":
            self.dismiss(None)

        elif event.button.id == "menu_create_btn":
            self.dismiss(("create", True))

        elif event.button.id == "menu_delete_btn":
            hid = self._get_highlighted_id()
            if hid:
                self.dismiss(("delete", hid))

        elif event.button.id == "menu_rename_btn":
            hid = self._get_highlighted_id()
            if hid:
                self.dismiss(("rename", hid))

        elif event.button.id == "menu_copy_btn":
            hid = self._get_highlighted_id()
            if hid:
                self.dismiss(("copy", hid))


# ==========================================================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ==========================================================
class PascalTUI(App):
    BINDINGS = [
        ("q", "quit", "Выйти"),
        ("o", "open_menu", "Открыть меню проектов"),
        ("s", "toggle_settings", "Настройки")
    ]

    CSS = """
    #main_layout {
        layout: vertical;
    }
    #workspace {
        height: 1fr;
    }
    #buttons_container {
        height: 3;
        margin-top: 1;
        margin-bottom: 1;
    }
    Button {
        margin-right: 1;
    }
    #settings_panel {
        border: solid green;
        background: $surface;
        padding: 1;
        display: none;
        height: auto;
        margin-bottom: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.code_backup = ""
        self.current_file = os.path.join(PROJECTS_DIR, "main.pas")
        self.use_dotnet = False

        if not os.path.exists(PROJECTS_DIR):
            os.makedirs(PROJECTS_DIR)

        if not os.listdir(PROJECTS_DIR):
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(TEMPLATE_HELLO_WORLD)

    def load_start_code(self) -> str:
        if os.path.exists(self.current_file):
            with open(self.current_file, "r", encoding="utf-8") as f:
                return f.read()
        return TEMPLATE_HELLO_WORLD

    def save_current_file(self) -> None:
        if hasattr(self, 'current_file') and self.current_file:
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.editor.text)
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="main_layout"):
            with Vertical(id="workspace"):
                yield Label("Активен: " + os.path.basename(self.current_file), id="cur_file_lbl")

                start_code = self.load_start_code()
                self.editor = TextArea(start_code, language="pascal")
                yield self.editor

                with Horizontal(id="buttons_container"):
                    yield Button("📁 Проекты (O)", variant="primary", id="open_menu_btn")
                    yield Button("Запустить", variant="success", id="run_btn")
                    yield Button("Настройки", variant="default", id="settings_btn")

                with Vertical(id="settings_panel"):
                    yield RadioSet(
                        RadioButton("Стартовать с Hello World", id="set_hello", value=True),
                        RadioButton("Стартовать с пустого шаблона", id="set_empty", value=False),
                        id="template_radio"
                    )
                    yield RadioSet(
                        RadioButton("Запуск через Mono", id="runtime_mono", value=True),
                        RadioButton("Запуск через Dotnet", id="runtime_dotnet", value=False),
                        id="runtime_radio"
                    )
                    with Horizontal():
                        yield Button("Стереть весь код", variant="error", id="clear_btn")
                        yield Button("Восстановить", variant="warning", id="undo_btn")

                self.log_box = RichLog()
                yield self.log_box
        yield Footer()

    def action_open_menu(self) -> None:
        self.save_current_file()
        self.push_screen(FileMenuScreen(), self.handle_menu_result)

    def handle_menu_result(self, result) -> None:
        if not result:
            return

        action_type, data = result
        files = get_project_files()

        # ===== ОТКРЫТЬ ФАЙЛ =====
        if action_type == "select":
            idx = int(data.split("_")[-1])
            if idx < len(files):
                filename = files[idx]
                self.current_file = os.path.join(PROJECTS_DIR, filename)
                with open(self.current_file, "r", encoding="utf-8") as f:
                    self.editor.text = f.read()
                self.query_one("#cur_file_lbl").update("Активен: " + filename)
                self.log_box.write(f"[Открыт файл: {filename}]\n")

        # ===== СОЗДАТЬ ФАЙЛ =====
        elif action_type == "create":
            auto_name = get_auto_filename()
            self.push_screen(
                InputDialog(
                    title="📝 Введите имя файла (без .pas):",
                    placeholder=auto_name,
                    default=""
                ),
                lambda name: self._do_create(name, auto_name)
            )

        # ===== УДАЛИТЬ ФАЙЛ =====
        elif action_type == "delete":
            idx = int(data.split("_")[-1])
            if idx < len(files):
                filename = files[idx]
                target_path = os.path.join(PROJECTS_DIR, filename)

                if os.path.exists(target_path):
                    os.remove(target_path)
                    for ext in [".exe", ".runtimeconfig.json"]:
                        p = os.path.splitext(target_path)[0] + ext
                        if os.path.exists(p):
                            os.remove(p)

                    self.log_box.write(f"[Файл {filename} удален]\n")

                    remaining = get_project_files()
                    if remaining:
                        self.current_file = os.path.join(PROJECTS_DIR, remaining[0])
                    else:
                        self.current_file = os.path.join(PROJECTS_DIR, "main.pas")
                        with open(self.current_file, "w", encoding="utf-8") as f:
                            f.write(TEMPLATE_HELLO_WORLD)

                    with open(self.current_file, "r", encoding="utf-8") as f:
                        self.editor.text = f.read()
                    self.query_one("#cur_file_lbl").update("Активен: " + os.path.basename(self.current_file))
            self.action_open_menu()

        # ===== ПЕРЕИМЕНОВАТЬ ФАЙЛ =====
        elif action_type == "rename":
            idx = int(data.split("_")[-1])
            if idx < len(files):
                old_name = files[idx]
                old_base = os.path.splitext(old_name)[0]
                self.push_screen(
                    InputDialog(
                        title=f"✏️ Переименовать '{old_name}':",
                        placeholder="новое_имя",
                        default=old_base
                    ),
                    lambda new_name, on=old_name: self._do_rename(on, new_name)
                )

        # ===== КОПИРОВАТЬ ФАЙЛ =====
        elif action_type == "copy":
            idx = int(data.split("_")[-1])
            if idx < len(files):
                src_name = files[idx]
                src_base = os.path.splitext(src_name)[0]
                auto_copy = f"{src_base}_copy"
                self.push_screen(
                    InputDialog(
                        title=f"📋 Копия файла '{src_name}':",
                        placeholder=auto_copy,
                        default=auto_copy
                    ),
                    lambda new_name, sn=src_name: self._do_copy(sn, new_name)
                )

    def _do_create(self, name: str | None, auto_name: str) -> None:
        """Создаёт новый файл"""
        filename = (name if name else auto_name) + ".pas"
        # Убираем .pas если пользователь сам написал расширение
        if filename.endswith(".pas.pas"):
            filename = filename[:-4]

        self.current_file = os.path.join(PROJECTS_DIR, filename)
        radio_hello = self.query_one("#set_hello", RadioButton)
        chosen_template = TEMPLATE_HELLO_WORLD if radio_hello.value else TEMPLATE_EMPTY

        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(chosen_template)

        self.editor.text = chosen_template
        self.query_one("#cur_file_lbl").update("Активен: " + filename)
        self.log_box.write(f"[Создан файл: {filename}]\n")
        self.action_open_menu()

    def _do_rename(self, old_name: str, new_name: str | None) -> None:
        """Переименовывает файл"""
        if not new_name:
            self.action_open_menu()
            return

        if not new_name.endswith(".pas"):
            new_name += ".pas"

        old_path = os.path.join(PROJECTS_DIR, old_name)
        new_path = os.path.join(PROJECTS_DIR, new_name)

        if os.path.exists(new_path):
            self.log_box.write(f"[Ошибка: файл {new_name} уже существует]\n")
            self.action_open_menu()
            return

        os.rename(old_path, new_path)

        # Переименовываем .exe и конфиг если есть
        for ext in [".exe", ".runtimeconfig.json"]:
            old_p = os.path.splitext(old_path)[0] + ext
            new_p = os.path.splitext(new_path)[0] + ext
            if os.path.exists(old_p):
                os.rename(old_p, new_p)

        # Если переименован текущий файл — обновляем путь
        if self.current_file == old_path:
            self.current_file = new_path
            self.query_one("#cur_file_lbl").update("Активен: " + new_name)

        self.log_box.write(f"[Переименован: {old_name} → {new_name}]\n")
        self.action_open_menu()

    def _do_copy(self, src_name: str, new_name: str | None) -> None:
        """Копирует файл"""
        if not new_name:
            self.action_open_menu()
            return

        if not new_name.endswith(".pas"):
            new_name += ".pas"

        src_path = os.path.join(PROJECTS_DIR, src_name)
        dst_path = os.path.join(PROJECTS_DIR, new_name)

        if os.path.exists(dst_path):
            self.log_box.write(f"[Ошибка: файл {new_name} уже существует]\n")
            self.action_open_menu()
            return

        shutil.copy2(src_path, dst_path)
        self.log_box.write(f"[Скопирован: {src_name} → {new_name}]\n")
        self.action_open_menu()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open_menu_btn":
            self.action_open_menu()

        elif event.button.id == "run_btn":
            self.log_box.clear()
            self.save_current_file()

            base_name = os.path.splitext(self.current_file)[0]
            exe_path = base_name + ".exe"

            if os.path.exists(exe_path):
                try:
                    os.remove(exe_path)
                except Exception:
                    pass

            self.log_box.write(f"Компиляция {os.path.basename(self.current_file)}...\n")

            if not os.path.exists(COMPILER_PATH):
                self.log_box.write(f"[ОШИБКА] Компилятор не найден по пути:\n{COMPILER_PATH}\n")
                return

            res = subprocess.run(["mono", COMPILER_PATH, self.current_file], capture_output=True, text=True)

            if res.returncode == 0 and os.path.exists(exe_path):
                self.log_box.write("[Скомпилировано успешно! Запуск...]\n")

                runtime_mono = self.query_one("#runtime_mono", RadioButton)
                self.use_dotnet = not runtime_mono.value

                if self.use_dotnet:
                    create_runtime_config(exe_path)
                    self.log_box.write("[Создан .runtimeconfig.json для Dotnet]\n")

                with self.suspend():
                    import os as native_os
                    native_os.system('clear')
                    print(f"=== ЗАПУСК ПРОГРАММЫ ===")
                    print(f"Выполняется файл: {os.path.basename(exe_path)}\n------------------------")

                    try:
                        if self.use_dotnet:
                            subprocess.run(["dotnet", exe_path])
                        else:
                            subprocess.run(["mono", exe_path])
                    except Exception as e:
                        print(f"\n[Ошибка запуска процесса]: {e}")

                    print("\n------------------------")
                    input("Программа завершена. Нажмите Enter, чтобы вернуться в IDE...")

            else:
                self.log_box.write("[Ошибка компиляции!]\n")
                if res.stdout:
                    self.log_box.write(res.stdout)
                if res.stderr:
                    self.log_box.write(res.stderr)

        elif event.button.id == "settings_btn":
            self.action_toggle_settings()
        elif event.button.id == "clear_btn":
            self.code_backup = self.editor.text
            self.editor.text = "begin\n  \nend."
        elif event.button.id == "undo_btn":
            if self.code_backup:
                self.editor.text = self.code_backup

    def action_toggle_settings(self) -> None:
        panel = self.query_one("#settings_panel")
        panel.styles.display = "none" if panel.styles.display == "block" else "block"

if __name__ == "__main__":
    PascalTUI().run()
