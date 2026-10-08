"""Пути: автоопределение окружения (обычный Linux / Termux)."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "abc-pascal-tui"
COMPILER_FILE = "pabcnetc.exe"

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PACKAGE_DIR.parent  # папка, где лежит tui.py

TERMUX_PREFIX = os.environ.get("PREFIX", "")
IS_TERMUX = bool(TERMUX_PREFIX) and "com.termux" in TERMUX_PREFIX


def candidate_share_dirs() -> list[str]:
    """Возможные места, где может лежать компилятор/проекты."""
    candidates: list[str] = []
    if IS_TERMUX:
        candidates.append(os.path.join(TERMUX_PREFIX, "share", APP_DIR_NAME))
    candidates += [
        "/usr/local/share/" + APP_DIR_NAME,
        "/usr/share/" + APP_DIR_NAME,
        os.path.join(os.path.expanduser("~"), ".local", "share", APP_DIR_NAME),
        str(ROOT_DIR),  # «переносная» версия рядом со скриптом
    ]
    return candidates


def find_share_dir() -> str:
    """Первая share-директория, где реально лежит компилятор."""
    for d in candidate_share_dirs():
        if os.path.exists(os.path.join(d, COMPILER_FILE)):
            return d
    if IS_TERMUX:
        return os.path.join(TERMUX_PREFIX, "share", APP_DIR_NAME)
    return str(ROOT_DIR)


def find_resource_dir() -> Path:
    """Где лежат locales/, themes/, data/ (рядом с кодом или в share)."""
    for d in [ROOT_DIR] + [Path(x) for x in candidate_share_dirs()]:
        if (d / "locales").is_dir():
            return d
    return ROOT_DIR


def _config_dir() -> Path:
    path = Path.home() / ".config" / APP_DIR_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


CONFIG_DIR = _config_dir()
SETTINGS_PATH = CONFIG_DIR / "settings.json"

# Пользовательские расширения (кладите свои файлы сюда)
USER_THEMES_DIR = CONFIG_DIR / "themes"
USER_LOCALES_DIR = CONFIG_DIR / "locales"
USER_COMPLETIONS_PATH = CONFIG_DIR / "completions.json"
USER_TEMPLATES_PATH = CONFIG_DIR / "templates.json"

RES_DIR = find_resource_dir()
DATA_DIR = RES_DIR / "data"
LOCALES_DIR = RES_DIR / "locales"
THEMES_DIR = RES_DIR / "themes"

DEFAULT_SHARE_DIR = find_share_dir()
DEFAULT_COMPILER_PATH = os.path.join(DEFAULT_SHARE_DIR, COMPILER_FILE)
DEFAULT_PROJECTS_DIR = os.path.join(DEFAULT_SHARE_DIR, "Projects")
