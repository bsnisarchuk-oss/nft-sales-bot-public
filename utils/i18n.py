"""Lightweight i18n system — dict-based, no heavy deps."""

from __future__ import annotations

import importlib
from typing import Any

_locales: dict[str, dict[str, str]] = {}
_default_lang = "ru"
SUPPORTED_LANGS = ("ru", "en")


def load_locale(lang: str) -> dict[str, str]:
    if lang not in _locales:
        try:
            mod = importlib.import_module(f"locales.{lang}")
            _locales[lang] = mod.STRINGS
        except (ModuleNotFoundError, AttributeError):
            if lang != _default_lang:
                return load_locale(_default_lang)
            raise
    return _locales[lang]


def t(key: str, lang: str = "ru", **kwargs: Any) -> str:
    """Translate *key* into *lang*.

    Falls back to default locale, then to the key itself.
    Supports ``{var}`` substitution via **kwargs.
    """
    strings = load_locale(lang)
    template = strings.get(key)
    if template is None:
        fallback = load_locale(_default_lang)
        template = fallback.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return template
