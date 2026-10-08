"""Операции с файлами проектов (без UI). Ошибки возвращаются кодами, а не исключениями."""
from __future__ import annotations

import os
import shutil

SIDECAR_EXTS = (".exe", ".runtimeconfig.json")
_BAD_CHARS = set('/\\\0:*?"<>|')


def project_files(projects_dir: str) -> list[str]:
    if not os.path.isdir(projects_dir):
        return []
    return sorted(f for f in os.listdir(projects_dir) if f.endswith(".pas"))


def auto_filename(projects_dir: str) -> str:
    """Автоматически генерирует имя project_N (без расширения)."""
    count = 1
    while os.path.exists(os.path.join(projects_dir, f"project_{count}.pas")):
        count += 1
    return f"project_{count}"


def normalize_filename(name: str) -> tuple[str | None, str | None]:
    """-> (имя_с_.pas, None) или (None, 'bad_name')."""
    name = (name or "").strip()
    if name.lower().endswith(".pas"):
        name = name[:-4]
    name = name.strip().strip(".")
    if not name or any(ch in _BAD_CHARS for ch in name):
        return None, "bad_name"
    return name + ".pas", None


def read_text(path: str) -> tuple[str, str | None]:
    """Читает файл: utf-8, потом cp1251 (старые файлы Windows). -> (текст, ошибка)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        return "", str(e)
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), None


def write_text(path: str, text: str) -> str | None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        return str(e)
    return None


def create_file(projects_dir: str, name: str, code: str) -> tuple[str | None, str | None]:
    """-> (полный_путь, None) или (None, код_ошибки). Существующий файл НЕ перезаписывается."""
    filename, err = normalize_filename(name)
    if err:
        return None, err
    path = os.path.join(projects_dir, filename)
    if os.path.exists(path):
        return None, "exists"
    err = write_text(path, code)
    return (None, f"io:{err}") if err else (path, None)


def rename_file(projects_dir: str, old_name: str, new_name: str) -> tuple[str | None, str | None]:
    filename, err = normalize_filename(new_name)
    if err:
        return None, err
    old_path = os.path.join(projects_dir, old_name)
    new_path = os.path.join(projects_dir, filename)
    if os.path.exists(new_path):
        return None, "exists"
    try:
        os.rename(old_path, new_path)
        for ext in SIDECAR_EXTS:
            old_p = os.path.splitext(old_path)[0] + ext
            new_p = os.path.splitext(new_path)[0] + ext
            if os.path.exists(old_p):
                os.rename(old_p, new_p)
    except OSError as e:
        return None, f"io:{e}"
    return new_path, None


def copy_file(projects_dir: str, src_name: str, new_name: str) -> tuple[str | None, str | None]:
    filename, err = normalize_filename(new_name)
    if err:
        return None, err
    src = os.path.join(projects_dir, src_name)
    dst = os.path.join(projects_dir, filename)
    if os.path.exists(dst):
        return None, "exists"
    try:
        shutil.copy2(src, dst)
    except OSError as e:
        return None, f"io:{e}"
    return dst, None


def delete_file(projects_dir: str, name: str) -> str | None:
    path = os.path.join(projects_dir, name)
    try:
        if os.path.exists(path):
            os.remove(path)
        for ext in SIDECAR_EXTS:
            p = os.path.splitext(path)[0] + ext
            if os.path.exists(p):
                os.remove(p)
    except OSError as e:
        return f"io:{e}"
    return None
