# -*- coding: utf-8 -*-
"""Multi-language support for XStream Player UI."""

import json
import os
import time
import xbmc
import xbmcvfs
import xbmcaddon

# Language mapping
LANG_CODES = {
    "English": "en",
    "Hrvatski": "hr",
    "Deutsch": "de",
    "Français": "fr",
    "Español": "es",
    "Italiano": "it",
    "Português": "pt",
    "Русский": "ru",
    "Polski": "pl",
    "Arabian": "ar",
    "Čeština": "cs",
    "Nederlands": "nl",
    "Ελληνικά": "el",
    "Magyar": "hu",
    "Română": "ro",
    "Svenska": "sv",
}

# Fallback chain for each language
FALLBACK_CHAIN = {
    "en": [],  # English is base, no fallback
    "hr": ["en"],  # Croatian → English
    "de": ["en"],  # German → English
    "fr": ["en"],  # French → English
    "es": ["en"],  # Spanish → English
    "it": ["en"],  # Italian → English
    "pt": ["en", "es"],  # Portuguese → English, Spanish
    "ru": ["en"],  # Russian → English
    "pl": ["en"],  # Polish → English
    "ar": ["en"],  # Arabic → English
    "cs": ["en"],  # Czech → English
    "nl": ["en"],  # Dutch → English
    "el": ["en"],  # Greek → English
    "hu": ["en"],  # Hungarian → English
    "ro": ["en"],  # Romanian → English
    "sv": ["en"],  # Swedish → English
}

# Cache for loaded translations
_translations_cache = {}
_current_lang = None
_cached_lang_code = None
_last_settings_check = 0


def _get_lang_code():
    """Get current language code from settings. Cached for 5s to avoid repeated getSetting calls."""
    global _cached_lang_code, _last_settings_check
    now = time.time()
    if _cached_lang_code is not None and (now - _last_settings_check) < 5:
        return _cached_lang_code
    try:
        addon = xbmcaddon.Addon()
        setting = addon.getSetting("interface_language") or "English"
        _cached_lang_code = LANG_CODES.get(setting, "en")
        _last_settings_check = now
        return _cached_lang_code
    except Exception:
        return "en"


def _load_translations(lang_code):
    """Load translations for a language, with fallback support."""
    if lang_code in _translations_cache:
        return _translations_cache[lang_code]

    addon_path = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("path"))
    lang_file = os.path.join(addon_path, "resources", "lang", f"{lang_code}.json")

    translations = {}

    # Load primary language and surface parse errors.
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
            # Convert string keys to int (JSON requires string keys)
            translations = {int(k): v for k, v in translations.items()}
    except FileNotFoundError:
        xbmc.log(f"[XStream Player] lang file missing: {lang_file}", xbmc.LOGWARNING)
    except (json.JSONDecodeError, ValueError) as e:
        xbmc.log(
            f"[XStream Player] lang file parse error ({lang_file}): {e}", xbmc.LOGERROR
        )
    except Exception as e:
        xbmc.log(
            f"[XStream Player] lang file load error ({lang_file}): {e}", xbmc.LOGERROR
        )

    # Load fallback languages — fill any missing keys (and load entirely if primary failed)
    for fallback in FALLBACK_CHAIN.get(lang_code, []):
        fallback_file = os.path.join(
            addon_path, "resources", "lang", f"{fallback}.json"
        )
        try:
            with open(fallback_file, "r", encoding="utf-8") as f:
                fallback_trans = json.load(f)
                fallback_trans = {int(k): v for k, v in fallback_trans.items()}
                # Fill missing strings from fallback
                for k, v in fallback_trans.items():
                    if k not in translations or not translations[k]:
                        translations[k] = v
        except FileNotFoundError:
            xbmc.log(
                f"[XStream Player] fallback lang file missing: {fallback_file}",
                xbmc.LOGWARNING,
            )
        except (json.JSONDecodeError, ValueError) as e:
            xbmc.log(
                f"[XStream Player] fallback lang parse error ({fallback_file}): {e}",
                xbmc.LOGERROR,
            )
        except Exception as e:
            xbmc.log(
                f"[XStream Player] fallback lang load error ({fallback_file}): {e}",
                xbmc.LOGERROR,
            )

    _translations_cache[lang_code] = translations
    return translations


def _t(string_id, *args):
    """Get translated string by ID.

    Args:
        string_id: Numeric ID (e.g., 30001)
        *args: Optional format arguments

    Returns:
        Translated string (formatted if args provided)
    """
    global _current_lang

    # Get current language
    lang = _get_lang_code()

    # Reload if language changed
    if lang != _current_lang:
        _current_lang = lang
        _translations_cache.clear()

    # Load translations
    translations = _load_translations(lang)

    # Get text (fallback to empty string if not found)
    text = translations.get(string_id, "")

    # If still empty, try English as last resort
    if not text and lang != "en":
        en_trans = _load_translations("en")
        text = en_trans.get(string_id, "")

    # Format if args provided
    if args:
        try:
            return text.format(*args)
        except Exception:
            return text
    return text
