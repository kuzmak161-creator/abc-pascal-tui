"""Шаблоны новых файлов: data/templates.json (+ ~/.config/abc-pascal-tui/templates.json)."""
from __future__ import annotations

from . import paths
from .jsonio import read_json

_FALLBACK = {
    "hello": {"title": {"ru": "Hello World", "en": "Hello World"},
              "code": "begin\n writeln('Hello World');\nend."},
    "empty": {"title": {"ru": "Пустой", "en": "Empty"}, "code": "begin\n \nend."},
}


def load_templates() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in (paths.DATA_DIR / "templates.json", paths.USER_TEMPLATES_PATH):
        data = read_json(path, {})
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and isinstance(value.get("code"), str):
                    result[key] = value
    return result or dict(_FALLBACK)


def template_code(key: str) -> str:
    templates = load_templates()
    item = templates.get(key) or templates.get("empty") or next(iter(templates.values()))
    return item["code"]


def empty_code() -> str:
    return load_templates().get("empty", _FALLBACK["empty"])["code"]


def template_choices(lang: str) -> list[tuple[str, str]]:
    """[(подпись, ключ)] для Select в настройках."""
    choices = []
    for key, item in load_templates().items():
        title = item.get("title")
        label = key
        if isinstance(title, dict):
            label = title.get(lang) or title.get("en") or key
        choices.append((str(label), key))
    return choices
