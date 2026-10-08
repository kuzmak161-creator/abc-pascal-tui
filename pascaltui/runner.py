"""Компиляция и запуск программ (без UI)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class CompileResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None  # "no_mono" | "timeout" | "os:<текст>"


def exe_path(source: str) -> str:
    return os.path.splitext(source)[0] + ".exe"


def compile_pascal(compiler: str, source: str, timeout: int = 60) -> CompileResult:
    """Блокирующая функция — вызывать из потока (asyncio.to_thread)."""
    if shutil.which("mono") is None:
        return CompileResult(False, error="no_mono")
    exe = exe_path(source)
    if os.path.exists(exe):
        try:
            os.remove(exe)
        except OSError:
            pass
    try:
        res = subprocess.run(
            ["mono", compiler, source],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CompileResult(False, error="timeout")
    except OSError as e:
        return CompileResult(False, error=f"os:{e}")
    ok = res.returncode == 0 and os.path.exists(exe)
    return CompileResult(ok, res.stdout or "", res.stderr or "")


def write_runtime_config(exe: str, template: dict) -> str | None:
    config_path = os.path.splitext(exe)[0] + ".runtimeconfig.json"
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)
    except OSError as e:
        return str(e)
    return None


def run_program(exe: str, runtime: str) -> str | None:
    """Запускает exe в текущем терминале. Возвращает текст ошибки или None."""
    tool = "dotnet" if runtime == "dotnet" else "mono"
    if shutil.which(tool) is None:
        return f"no_{tool}"
    try:
        subprocess.run([tool, exe])
    except OSError as e:
        return str(e)
    return None
