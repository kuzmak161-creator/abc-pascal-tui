"""Подсветка синтаксиса Pascal (без tree-sitter, чистый Python)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Токенизатор
_TOKEN = re.compile(
    r"//[^\n]*"
    r"|\{|\}"
    r"|\(\*|\*\)"
    r"|'(?:[^']|'')*'?"
    r"|\$[0-9A-Fa-f]+"
    r"|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
    r"|[^\W\d]\w*"
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
    """Подсвечивает весь документ, аккуратно обходя ASCII-арт."""
    result: list[list[tuple[int, int, str]]] = []
    state = None

    for line in lines:
        spans: list[tuple[int, int, str]] = []
        n = len(line)
        pos = 0

        while pos < n:
            if state == "brace":
                end = line.find("}", pos)
                if end < 0:
                    spans.append((pos, n, "comment")); pos = n
                else:
                    spans.append((pos, end + 1, "comment")); pos = end + 1; state = None
                continue
            elif state == "paren":
                end = line.find("*)", pos)
                if end < 0:
                    spans.append((pos, n, "comment")); pos = n
                else:
                    spans.append((pos, end + 2, "comment")); pos = end + 2; state = None
                continue

            m = _TOKEN.search(line, pos)
            if not m:
                break

            start, end = m.span()
            text = m.group()

            if text.startswith("//"):
                spans.append((start, n, "comment")); pos = n
            elif text == "{":
                close_at = line.find("}", end)
                if close_at < 0:
                    spans.append((start, n, "comment")); state = "brace"; pos = n
                else:
                    spans.append((start, close_at + 1, "comment")); pos = close_at + 1
            elif text == "(*":
                close_at = line.find("*)", end)
                if close_at < 0:
                    spans.append((start, n, "comment")); state = "paren"; pos = n
                else:
                    spans.append((start, close_at + 2, "comment")); pos = close_at + 2
            elif text[0] == "'":
                # Защита от ASCII-арта: кавычка сразу после буквы/цифры строку не начинает
                if start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
                    pos = start + 1
                    continue
                # токен-регулярка уже захватила строку целиком (с '' внутри) до закрывающей кавычки;
                # если закрывающей нет — это не строка, оставляем без подсветки
                if len(text) >= 2 and text.endswith("'"):
                    spans.append((start, end, "string"))
                pos = end
            elif text[0].isdigit() or text[0] == "$":
                spans.append((start, end, "number")); pos = end
            else:
                kind = classify(text, sets)
                if kind:
                    spans.append((start, end, kind))
                pos = end

        result.append(spans)
    return result
