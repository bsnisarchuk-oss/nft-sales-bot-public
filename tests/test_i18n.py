"""Tests for utils/i18n.py."""

from utils.i18n import SUPPORTED_LANGS, load_locale, t


def test_t_returns_ru_by_default():
    result = t("no_access")
    assert "доступа" in result.lower() or "⛔" in result


def test_t_returns_en():
    result = t("no_access", lang="en")
    assert "denied" in result.lower()


def test_t_with_kwargs():
    result = t("min_price_set", lang="en", val="2.5")
    assert "2.5" in result


def test_t_missing_key_returns_key():
    result = t("this_key_does_not_exist_xyz")
    assert result == "this_key_does_not_exist_xyz"


def test_t_unknown_lang_falls_back_to_ru():
    result = t("no_access", lang="zz")
    assert "доступа" in result.lower() or "⛔" in result


def test_load_locale_ru():
    strings = load_locale("ru")
    assert isinstance(strings, dict)
    assert "no_access" in strings


def test_load_locale_en():
    strings = load_locale("en")
    assert isinstance(strings, dict)
    assert "no_access" in strings


def test_all_ru_keys_exist_in_en():
    ru = load_locale("ru")
    en = load_locale("en")
    missing = set(ru.keys()) - set(en.keys())
    assert not missing, f"Keys in ru but not en: {missing}"


def test_all_en_keys_exist_in_ru():
    ru = load_locale("ru")
    en = load_locale("en")
    missing = set(en.keys()) - set(ru.keys())
    assert not missing, f"Keys in en but not ru: {missing}"


def test_supported_langs():
    assert "ru" in SUPPORTED_LANGS
    assert "en" in SUPPORTED_LANGS
