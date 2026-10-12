"""Движок автодополнения Pascal (без UI): словарь из data/completions.json."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from . import paths
from .jsonio import read_json

KIND_ORDER = {"keyword": 0, "type": 1, "function": 2, "snippet": 3, "word": 4}
KIND_MARK = {"keyword": "k", "type": "t", "function": "f", "snippet": "s", "word": "w"}

_WORD_RE = re.compile(r"[^\W\d]\w*", re.UNICODE)
_OPENER_RE = re.compile(
    r"\b(begin|then|do|else|of|repeat|try|finally|except|record)\s*$", re.IGNORECASE
)


@dataclass(frozen=True)
class Completion:
    trigger: str   # по чему ищем
    label: str     # что показываем
    insert: str    # что вставляем ($0 — позиция курсора)
    kind: str      # keyword | type | function | snippet | word
    detail: str = ""


# ----------------------------------------------------------
# разбор строки
# ----------------------------------------------------------
def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def current_prefix(line: str, col: int) -> tuple[int, str]:
    """Слово слева от курсора -> (начальная_колонка, префикс)."""
    col = max(0, min(col, len(line)))
    start = col
    while start > 0 and _is_word_char(line[start - 1]):
        start -= 1
    prefix = line[start:col]
    if prefix and prefix[0].isdigit():
        return col, ""
    return start, prefix


def scan_context(before: str) -> str:
    """Где находится конец строки `before`: 'code' | 'string' | 'comment' (в пределах строки)."""
    state = "code"
    i, n = 0, len(before)
    while i < n:
        ch = before[i]
        if state == "code":
            if ch == "'":
                state = "string"
            elif ch == "{":
                state = "brace"
            elif ch == "/" and before.startswith("//", i):
                return "comment"
            elif ch == "(" and before.startswith("(*", i):
                state = "paren"
                i += 1
        elif state == "string":
            if ch == "'":
                state = "code"
        elif state == "brace":
            if ch == "}":
                state = "code"
        elif state == "paren":
            if ch == "*" and before.startswith("*)", i):
                state = "code"
                i += 1
        i += 1
    if state == "string":
        return "string"
    return "code" if state == "code" else "comment"


def code_part(line: str) -> str:
    """Строка без комментариев (строки в кавычках сохраняются)."""
    out: list[str] = []
    state = "code"
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if state == "code":
            if ch == "'":
                state = "string"
                out.append(ch)
            elif ch == "{":
                state = "brace"
            elif ch == "/" and line.startswith("//", i):
                break
            elif ch == "(" and line.startswith("(*", i):
                state = "paren"
                i += 1
            else:
                out.append(ch)
        elif state == "string":
            out.append(ch)
            if ch == "'":
                state = "code"
        elif state == "brace":
            if ch == "}":
                state = "code"
        elif state == "paren":
            if ch == "*" and line.startswith("*)", i):
                state = "code"
                i += 1
        i += 1
    return "".join(out)


def leading_indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def opens_block(before: str) -> bool:
    """Заканчивается ли строка словом begin/then/do/else/... (нужен доп. отступ)."""
    return bool(_OPENER_RE.search(code_part(before).rstrip()))


def expand_snippet(code: str, indent: str, unit: str) -> tuple[str, int, int]:
    """Разворачивает шаблон.

    \\t -> unit (ширина отступа из настроек), после каждого перевода строки добавляется `indent`.
    Возвращает (текст, строка_курсора_относительно_начала, колонка_курсора).
    Для rel_row == 0 колонка относительна начала вставки, иначе — абсолютная в строке.
    """
    code = code.replace("\t", unit)
    pos = code.find("$0")
    if pos < 0:
        before = code
        body = code
    else:
        before = code[:pos]
        body = code[:pos] + code[pos + 2:]
    text = ("\n" + indent).join(body.split("\n"))
    before_lines = before.split("\n")
    rel_row = len(before_lines) - 1
    rel_col = len(before_lines[-1]) + (len(indent) if rel_row > 0 else 0)
    return text, rel_row, rel_col


# ----------------------------------------------------------
# движок
# ----------------------------------------------------------
def _merge_data(base: dict, extra: dict) -> dict:
    out = {k: list(v) if isinstance(v, list) else v for k, v in base.items()}
    for key in ("keywords", "types", "functions"):
        if isinstance(extra.get(key), list):
            out.setdefault(key, []).extend(extra[key])
    if isinstance(extra.get("snippets"), list):
        by_trigger = {s.get("trigger"): s for s in out.get("snippets", []) if isinstance(s, dict)}
        for s in extra["snippets"]:
            if isinstance(s, dict) and s.get("trigger"):
                by_trigger[s["trigger"]] = s  # пользовательский перекрывает
        out["snippets"] = list(by_trigger.values())
    return out


class CompletionEngine:
    def __init__(self, data: dict | None = None):
        self._items: list[Completion] = []
        self.load(data or {})

    @classmethod
    def from_files(cls) -> "CompletionEngine":
        data = read_json(paths.DATA_DIR / "completions.json", {}) or {}
        user = read_json(paths.USER_COMPLETIONS_PATH, {}) or {}
        if isinstance(user, dict):
            data = _merge_data(data, user)
        return cls(data)

    def load(self, data: dict) -> None:
        items: list[Completion] = []
        for word in data.get("keywords", []):
            if isinstance(word, str):
                items.append(Completion(word, word, word, "keyword"))
        for word in data.get("types", []):
            if isinstance(word, str):
                items.append(Completion(word, word, word, "type"))
        for entry in data.get("functions", []):
            if isinstance(entry, str):
                items.append(Completion(entry, entry, entry, "function"))
            elif isinstance(entry, list) and entry and isinstance(entry[0], str):
                name = entry[0]
                detail = entry[1] if len(entry) > 1 and isinstance(entry[1], str) else ""
                insert = entry[2] if len(entry) > 2 and isinstance(entry[2], str) else name
                items.append(Completion(name, name, insert, "function", detail))
        for snip in data.get("snippets", []):
            if isinstance(snip, dict) and snip.get("trigger") and isinstance(snip.get("code"), str):
                trigger = str(snip["trigger"])
                items.append(
                    Completion(trigger, str(snip.get("label", trigger)), snip["code"], "snippet")
                )
        items.sort(key=lambda c: (KIND_ORDER[c.kind], len(c.trigger), c.trigger.lower()))
        self._items = items

    def word_sets(self):
        """Слова для подсветки: (ключевые слова, типы, функции) в нижнем регистре."""
        from .highlight import WordSets

        sets = WordSets()
        for c in self._items:
            low = c.trigger.lower()
            if c.kind == "keyword":
                sets.keywords.add(low)
            elif c.kind == "type":
                sets.types.add(low)
            elif c.kind == "function":
                sets.functions.add(low)
        return sets

    def suggest(
        self,
        prefix: str,
        text: str = "",
        *,
        max_items: int = 8,
        use_buffer: bool = True,
        use_snippets: bool = True,
    ) -> list[Completion]:
        p = prefix.lower()
        if not p:
            return []
        out: list[Completion] = []
        known: set[str] = set()
        for c in self._items:
            if c.kind == "snippet" and not use_snippets:
                continue
            t = c.trigger.lower()
            known.add(t)
            if not t.startswith(p):
                continue
            # полностью набранное слово не предлагаем, а шаблон с таким же именем — да
            if t == p and c.kind != "snippet":
                continue
            out.append(c)
        if use_buffer and text:
            counts = Counter(_WORD_RE.findall(text))
            words = []
            for word, cnt in counts.items():
                lw = word.lower()
                if len(word) >= 3 and lw.startswith(p) and lw != p and lw not in known:
                    words.append((-cnt, len(word), lw, word))
            seen: set[str] = set()
            for _, _, lw, word in sorted(words):
                if lw in seen:
                    continue
                seen.add(lw)
                out.append(Completion(word, word, word, "word"))
        return out[: max(1, max_items)]
