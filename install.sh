#!/bin/bash

# --- Выбор языка ---
echo "Select language / Выберите язык:"
echo "1) English"
echo "2) Русский"
echo "3) Українська"
read -p "Enter number / Введите номер: " LANG_CHOICE

case $LANG_CHOICE in
    1)
        MSG_WELCOME="Installing abc-pascal-tui..."
        MSG_CHECK="Error: File 'tui.py' not found in current directory."
        MSG_RUN_ROOT="Please run the script from the root of the abc-pascal-tui repository."
        MSG_MKDIR="Creating directories..."
        MSG_MKDIR_FAIL="Failed to create directory"
        MSG_COPY="Copying files to"
        MSG_RSYNC_FAIL="rsync not found, using cp -r"
        MSG_COPY_FAIL="Error: tui.py was not copied!"
        MSG_CREATE_CMD="Creating command pascal-tui..."
        MSG_SUCCESS="Installation completed successfully!"
        MSG_RUN_CMD="Now you can run the IDE with the command:"
        MSG_FILES_IN="All project files are located in:"
        MSG_CONFIG_IN="Configuration will be created in:"
        MSG_REMOVE="Removing installation script..."
        MSG_FAIL="Something went wrong. The executable file was not installed."
        ;;
    2)
        MSG_WELCOME="Установка abc-pascal-tui..."
        MSG_CHECK="Ошибка: Файл 'tui.py' не найден в текущей папке."
        MSG_RUN_ROOT="Пожалуйста, запустите скрипт из корня репозитория abc-pascal-tui."
        MSG_MKDIR="Создание директорий..."
        MSG_MKDIR_FAIL="Не удалось создать директорию"
        MSG_COPY="Копирование файлов в"
        MSG_RSYNC_FAIL="rsync не найден, используется cp -r"
        MSG_COPY_FAIL="Ошибка: tui.py не скопирован!"
        MSG_CREATE_CMD="Создание команды pascal-tui..."
        MSG_SUCCESS="Установка успешно завершена!"
        MSG_RUN_CMD="Теперь вы можете запустить IDE командой:"
        MSG_FILES_IN="Все файлы проекта находятся в:"
        MSG_CONFIG_IN="Конфиг будет создан в:"
        MSG_REMOVE="Удаление установочного скрипта..."
        MSG_FAIL="Что-то пошло не так. Исполняемый файл не был установлен."
        ;;
    3)
        MSG_WELCOME="Встановлення abc-pascal-tui..."
        MSG_CHECK="Помилка: Файл 'tui.py' не знайдено в поточній папці."
        MSG_RUN_ROOT="Будь ласка, запустіть скрипт з кореня репозиторію abc-pascal-tui."
        MSG_MKDIR="Створення директорій..."
        MSG_MKDIR_FAIL="Не вдалося створити директорію"
        MSG_COPY="Копіювання файлів до"
        MSG_RSYNC_FAIL="rsync не знайдено, використовується cp -r"
        MSG_COPY_FAIL="Помилка: tui.py не скопійовано!"
        MSG_CREATE_CMD="Створення команди pascal-tui..."
        MSG_SUCCESS="Встановлення успішно завершено!"
        MSG_RUN_CMD="Тепер ви можете запустити IDE командою:"
        MSG_FILES_IN="Всі файли проекту знаходяться в:"
        MSG_CONFIG_IN="Конфіг буде створено в:"
        MSG_REMOVE="Видалення встановлювального скрипта..."
        MSG_FAIL="Щось пішло не так. Виконуваний файл не було встановлено."
        ;;
    *)
        echo "Invalid choice / Неверный выбор / Невірний вибір"
        exit 1
        ;;
esac

# --- Определение переменных ---
PROJECT_NAME="abc-pascal-tui"
BIN_NAME="pascal-tui"
SOURCE_BIN="tui.py"

if [ -n "$PREFIX" ]; then
    BIN_DIR="$PREFIX/bin"
    SHARE_DIR="$PREFIX/share/$PROJECT_NAME"
else
    BIN_DIR="/usr/local/bin"
    SHARE_DIR="/usr/local/share/$PROJECT_NAME"
fi

echo ""
echo "$MSG_WELCOME"
echo ""

# --- Проверка исходных файлов ---
if [ ! -f "$SOURCE_BIN" ]; then
    echo "$MSG_CHECK"
    echo "$MSG_RUN_ROOT"
    exit 1
fi

# --- Создание целевых директорий ---
echo "$MSG_MKDIR"
mkdir -p "$BIN_DIR" || { echo "$MSG_MKDIR_FAIL $BIN_DIR"; exit 1; }
mkdir -p "$SHARE_DIR" || { echo "$MSG_MKDIR_FAIL $SHARE_DIR"; exit 1; }

# --- Копирование файлов ---
echo "$MSG_COPY $SHARE_DIR..."

rsync -av --exclude='install.sh' --exclude='uninstall.sh' --exclude='.git' ./ "$SHARE_DIR/" 2>/dev/null || {
    echo "$MSG_RSYNC_FAIL"
    find . -maxdepth 1 ! -name 'install.sh' ! -name 'uninstall.sh' ! -name '.git' -exec cp -r {} "$SHARE_DIR/" \;
}

if [ ! -f "$SHARE_DIR/tui.py" ]; then
    echo "$MSG_COPY_FAIL"
    exit 1
fi

# --- Создание исполняемого файла ---
echo "$MSG_CREATE_CMD"

cat > "$BIN_DIR/$BIN_NAME" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$PREFIX" ]; then
    SHARE_DIR="$PREFIX/share/abc-pascal-tui"
else
    SHARE_DIR="/usr/local/share/abc-pascal-tui"
fi

python3 "$SHARE_DIR/tui.py" "$@"
EOF

chmod +x "$BIN_DIR/$BIN_NAME"

# --- Проверка ---
if [ -f "$BIN_DIR/$BIN_NAME" ]; then
    echo ""
    echo "$MSG_SUCCESS"
    echo ""
    echo "$MSG_RUN_CMD"
    echo "   $BIN_NAME"
    echo ""
    echo "$MSG_FILES_IN"
    echo "   $SHARE_DIR"
    echo ""
    echo "$MSG_CONFIG_IN"
    echo "   ~/.config/abc-pascal-tui/settings.json"
    echo ""
else
    echo "$MSG_FAIL"
    exit 1
fi

# --- Самоудаление скрипта ---
echo "$MSG_REMOVE"
rm -- "$0"
