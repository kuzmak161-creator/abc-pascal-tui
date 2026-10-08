"""Настройки: значения по умолчанию лежат в data/defaults.json."""
from __future__ import annotations

from . import paths
from .jsonio import read_json, write_json_atomic

_MINIMAL = {
    "language": "ru",
    "theme": "pascal-dark",
    "editor_theme": "auto",
    "start_template": "hello",
    "runtime": "mono",
}

INT_LIMITS = {
    "tab_width": (1, 8),
    "autocomplete_min_chars": (1, 6),
    "autocomplete_max_items": (3, 20),
    "compile_timeout": (5, 600),
}

# строки, которые могут быть пустыми
_ALLOW_EMPTY = {"last_file"}


def _defaults_file() -> dict:
    data = read_json(paths.DATA_DIR / "defaults.json", {})
    return data if isinstance(data, dict) else {}


def default_settings() -> dict:
    result = dict(_MINIMAL)
    raw = _defaults_file().get("settings", {})
    if isinstance(raw, dict):
        result.update(raw)
    result.setdefault("compiler_path", paths.DEFAULT_COMPILER_PATH)
    result.setdefault("projects_dir", paths.DEFAULT_PROJECTS_DIR)
    result.setdefault("last_file", "")
    return result


def sanitize(raw: dict, base: dict) -> dict:
    """Оставляет только известные ключи и приводит значения к типу значения по умолчанию."""
    out = dict(base)
    if not isinstance(raw, dict):
        return out
    for key, default in base.items():
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(default, bool):
            if isinstance(value, bool):
                out[key] = value
        elif isinstance(default, int):
            if isinstance(value, int) and not isinstance(value, bool):
                lo, hi = INT_LIMITS.get(key, (None, None))
                if lo is not None:
                    value = max(lo, min(hi, value))
                out[key] = value
        elif isinstance(default, str):
            if isinstance(value, str) and (value.strip() or key in _ALLOW_EMPTY):
                out[key] = value
    return out


def load_settings() -> dict:
    raw = read_json(paths.SETTINGS_PATH, {})
    return sanitize(raw, default_settings())


def save_settings(settings: dict) -> str | None:
    """Возвращает текст ошибки или None."""
    return write_json_atomic(paths.SETTINGS_PATH, settings)


def runtime_config() -> dict:
    cfg = _defaults_file().get("runtime_config")
    if isinstance(cfg, dict):
        return cfg
    return {
        "runtimeOptions": {
            "tfm": "net472",
            "framework": {"name": "Microsoft.NETCore.App", "version": "8.0.0"},
        }
    }
