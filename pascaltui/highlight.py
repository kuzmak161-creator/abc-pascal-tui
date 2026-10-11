"""Подсветка синтаксиса Pascal (без tree-sitter, чистый Python).

tokenize() возвращает для каждой строки список (начало, конец, имя_стиля).
Имена стилей совпадают с темами TextArea: keyword, type, string, comment,
number, function.call, boolean.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_TOKEN = re.compile(
    r"//[^\n]*"                      # комментарий до конца строки
    r"|\{|\(\*"                      # начало { } или (* *)
    r"|'(?:[^']|'')*'?"              # строка ('' — экранированная кавычка)
    r"|\$[0-9A-Fa-f]+"               # hex-число
    r"|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"  # число
    r"|[^\W\d]\w*"                   # идентификатор / слово
)

_BOOLEANS = {"true", "false", "nil"}


@dataclass
class WordSets:
    keywords: set = field(default_factory=set)
    types: set = field(default_factory=set)
    functions: set = field(default_factory=set)


def classify(word: str, sets: WordSets) -> str | None:
    low = word.lower()
    if low in _BOOLEANS:
        return "boolean"
    if low in sets.keywords:
        return "keyword"
    if low in sets.types:
        return "type"
    if low in sets.functions:
        return "function.call"
    return None


def tokenize(lines: list[str], sets: WordSets) -> list[list[tuple[int, int, str]]]:
    """Подсвечивает весь документ; многострочные комментарии переносятся между строками."""
    result: list[list[tuple[int, int, str]]] = []
    state: str | None = None  # None | "brace" | "paren"
    for line in lines:
        spans: list[tuple[int, int, str]] = []
        n = len(line)
        pos = 0
        while pos < n:
            if state is not None:
                closer = "}" if state == "brace" else "*)"
                end = line.find(closer, pos)
                if end < 0:
                    spans.append((pos, n, "comment"))
                    pos = n
                else:
                    end += len(closer)
                    spans.append((pos, end, "comment"))
                    pos = end
                    state = None
                continue
            m = _TOKEN.search(line, pos)
            if not m:
                break
            start, end = m.span()
            text = m.group()
            if text.startswith("//"):
                spans.append((start, n, "comment"))
                pos = n
            elif text == "{" or text == "(*":
                closer = "}" if text == "{" else "*)"
                close_at = line.find(closer, end)
                if close_at < 0:
                    spans.append((start, n, "comment"))
                    state = "brace" if text == "{" else "paren"
                    pos = n
                else:
                    spans.append((start, close_at + len(closer), "comment"))
                    pos = close_at + len(closer)
            elif text[0] == "'":
                spans.append((start, end, "string"))
                pos = end
            elif text[0].isdigit() or text[0] == "$":
                spans.append((start, end, "number"))
                pos = end
            else:
                kind = classify(text, sets)
                if kind:
                    spans.append((start, end, kind))
                pos = end
        result.append(spans)
    return result
