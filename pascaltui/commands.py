"""Настройки в палитре команд (F2 / Ctrl+P).

Без запроса показываются только разделы (окна). При вводе текста ищутся и разделы,
и быстрые команды (язык, шаблон, Mono/Dotnet, пути).
"""
from __future__ import annotations

from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from . import templates
from .i18n import available_languages, tr


class SettingsCommands(Provider):
    def _sections(self):
        app = self.app
        L = app.lang
        return [
            (tr(L, "cmd_themes"), tr(L, "cmd_themes_help"), app.action_open_themes),
            (tr(L, "cmd_autocomplete"), tr(L, "cmd_autocomplete_help"), app.action_open_autocomplete),
            (tr(L, "cmd_general"), tr(L, "cmd_general_help"), app.action_open_general),
            (tr(L, "cmd_run"), tr(L, "cmd_run_help"), app.action_open_run),
        ]

    def _quick(self):
        app = self.app
        L = app.lang
        e = []
        for label, key in templates.template_choices(L):
            e.append((tr(L, "cmd_template", name=label), tr(L, "cmd_template_help"),
                      partial(app.action_set_option, "start_template", key)))
        e += [
            (tr(L, "cmd_runtime_mono"), tr(L, "cmd_runtime_mono_help"),
             partial(app.action_set_option, "runtime", "mono")),
            (tr(L, "cmd_runtime_dotnet"), tr(L, "cmd_runtime_dotnet_help"),
             partial(app.action_set_option, "runtime", "dotnet")),
        ]
        for code, name in available_languages():
            e.append((tr(L, "cmd_lang", name=name), tr(L, "cmd_lang_help"),
                      partial(app.action_set_option, "language", code)))
        e += [
            (tr(L, "cmd_set_compiler"), tr(L, "cmd_set_compiler_help"), app.action_prompt_compiler_path),
            (tr(L, "cmd_set_projects"), tr(L, "cmd_set_projects_help"), app.action_prompt_projects_dir),
            (tr(L, "cmd_show_paths"), tr(L, "cmd_show_paths_help"), app.action_show_paths),
        ]
        return e

    async def discover(self) -> Hits:
        for name, help_text, callback in self._sections():
            yield DiscoveryHit(name, callback, help=help_text)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, callback in self._sections() + self._quick():
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), callback, help=help_text)
