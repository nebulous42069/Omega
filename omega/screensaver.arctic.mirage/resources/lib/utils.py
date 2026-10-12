# -*- coding: utf-8 -*-
import os
import re
import shutil

import xbmc
import xbmcaddon
import xbmcgui

try:
    import xbmcvfs
except Exception:
    xbmcvfs = None

_addon = xbmcaddon.Addon()
_id = _addon.getAddonInfo('id')

PATH_SETTING = 'path'
NAME_SETTING = 'name'
SKIN_PATH_STRING = '{}.path'.format(_id)
SKIN_NAME_STRING = '{}.name'.format(_id)


def log(msg, level=xbmc.LOGDEBUG):
    message = '{}: {}'.format(_id, msg)
    xbmc.log(msg=message, level=level)


def get_setting_string(setting):
    try:
        return _addon.getSettingString(setting)
    except Exception:
        return '{}'.format(_addon.getSetting(setting))



def get_bool_setting(setting, default=False):
    value = get_setting_string(setting).lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    if value in ('false', '0', 'no', 'off'):
        return False
    return default

def set_setting_string(setting, value):
    value = value or ''
    try:
        return _addon.setSettingString(setting, value)
    except Exception:
        return _addon.setSetting(setting, value)


def get_skin_string(setting):
    # script.skinshortcuts stores widget choices in Skin.String(), not in the
    # add-on settings store. Read the same place it writes.
    return xbmc.getInfoLabel('Skin.String({})'.format(setting)) or ''


def set_skin_string(setting, value):
    # Keep this simple: Kodi's Skin.SetString builtin is the supported path for
    # skin strings. Most widget paths are plugin:// URLs and are safe here.
    value = value or ''
    return xbmc.executebuiltin('Skin.SetString({},{})'.format(setting, value), wait=True)


def get_saved_widget_path():
    return (
        get_setting_string(PATH_SETTING)
        or get_setting_string(SKIN_PATH_STRING)
        or get_skin_string(SKIN_PATH_STRING)
        or ''
    )


def get_saved_widget_name():
    return (
        get_setting_string(NAME_SETTING)
        or get_setting_string(SKIN_NAME_STRING)
        or get_skin_string(SKIN_NAME_STRING)
        or ''
    )


def save_widget_path(path):
    path = path or ''
    set_setting_string(PATH_SETTING, path)
    # Also keep the old full-id setting name populated for compatibility with
    # earlier builds of this add-on.
    set_setting_string(SKIN_PATH_STRING, path)


def save_widget_name(name):
    name = name or ''
    set_setting_string(NAME_SETTING, name)
    set_setting_string(SKIN_NAME_STRING, name)


def sync_addon_settings_from_skinstrings():
    """Copy Skin Shortcuts' Skin.String values into persistent add-on settings."""
    path = get_skin_string(SKIN_PATH_STRING)
    name = get_skin_string(SKIN_NAME_STRING)

    if path:
        save_widget_path(path)
        log('Saved widget path to add-on settings: {}'.format(path))
    else:
        log('No Skin.String widget path found to save')

    if name:
        save_widget_name(name)
        log('Saved widget name to add-on settings: {}'.format(name))

    return path, name


def sync_skinstrings_from_addon_settings():
    """Populate Skin.String values from add-on settings before XML loads."""
    path = get_saved_widget_path()
    name = get_saved_widget_name()

    if path:
        set_skin_string(SKIN_PATH_STRING, path)
        log('Synced widget path to Skin.String: {}'.format(path))
    if name:
        set_skin_string(SKIN_NAME_STRING, name)
        log('Synced widget name to Skin.String: {}'.format(name))

    return path, name


MIRAGE_FONT_FILES = ('Mirage-Regular.ttf', 'Mirage-Bold.ttf')

MIRAGE_FONT_SPECS = (
    ('Mirage_Title', 'Mirage-Bold.ttf', 72),
    ('Mirage_Body', 'Mirage-Regular.ttf', 36),
    ('Mirage_Small', 'Mirage-Regular.ttf', 40),
    ('Mirage_Button', 'Mirage-Bold.ttf', 64),
)

MIRAGE_FONT_NAMES = tuple(spec[0] for spec in MIRAGE_FONT_SPECS)


def _mirage_font_definition(name, filename, size):
    return """        <font>
            <name>{}</name>
            <filename>{}</filename>
            <size>{}</size>
        </font>""".format(name, filename, size)


def translate_path(path):
    if not path:
        return ''
    try:
        if xbmcvfs:
            return xbmcvfs.translatePath(path)
    except Exception:
        pass
    try:
        return xbmc.translatePath(path)
    except Exception:
        return path


def _dialog_ok(title, message):
    try:
        xbmcgui.Dialog().ok(title, message)
    except Exception:
        log('{}: {}'.format(title, message), xbmc.LOGINFO)


def _get_active_skin_id():
    try:
        return xbmc.getSkinDir()
    except Exception:
        return ''


def _get_active_skin_path():
    skin_id = _get_active_skin_id()
    if not skin_id:
        return '', ''

    try:
        skin_addon = xbmcaddon.Addon(skin_id)
        skin_path = translate_path(skin_addon.getAddonInfo('path'))
        return skin_id, skin_path
    except Exception as exc:
        log('Unable to resolve active skin path: {}'.format(exc), xbmc.LOGERROR)
        return skin_id, ''


def _find_active_skin_fontxml(skin_path):
    candidates = (
        os.path.join(skin_path, 'xml', 'Font.xml'),
        os.path.join(skin_path, '1080i', 'Font.xml'),
        os.path.join(skin_path, '1080p', 'Font.xml'),
        os.path.join(skin_path, '720p', 'Font.xml'),
        os.path.join(skin_path, '16x9', 'Font.xml'),
        os.path.join(skin_path, 'pal16x9', 'Font.xml'),
        os.path.join(skin_path, 'ntsc16x9', 'Font.xml'),
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ''


def _addon_font_path(filename):
    return os.path.join(
        translate_path(_addon.getAddonInfo('path')),
        'resources',
        'skins',
        'Default',
        'fonts',
        filename,
    )


def _inject_font_defs_into_fontxml(text):
    """Install Mirage font names into one fontset only.

    Most skins define multiple <fontset> sections so users can switch between
    Default, Arial, Large, etc. Earlier builds inserted Mirage_* into every
    fontset for maximum compatibility, but that makes the skin Font.xml noisy.

    This version prefers the fontset whose id="Default". If there is no Default
    fontset, it uses the first fontset in the file. It also removes Mirage_*
    font definitions from all other fontsets, so rerunning the installer cleans
    up the older multi-fontset behavior.
    """
    changed = False
    fontset_pattern = re.compile(
        r'(<fontset\b[^>]*>)(.*?)(</fontset>)',
        flags=re.IGNORECASE | re.DOTALL,
    )
    font_block_pattern = re.compile(
        r'\n?[ \t]*<font>\s*<name>\s*({})\s*</name>.*?</font>'.format('|'.join(MIRAGE_FONT_NAMES)),
        flags=re.IGNORECASE | re.DOTALL,
    )
    mirage_comment_pattern = re.compile(
        r'\n?[ \t]*<!--\s*Arctic Mirage custom fonts\s*-->',
        flags=re.IGNORECASE,
    )

    matches = list(fontset_pattern.finditer(text))
    if not matches:
        return text, False

    target_index = 0
    for index, match in enumerate(matches):
        opening = match.group(1)
        if re.search(r'\bid\s*=\s*(["\'])Default\1', opening, flags=re.IGNORECASE):
            target_index = index
            break

    def clean_mirage_blocks(body, keep_first):
        nonlocal changed
        seen = set()
        pieces = []
        last = 0

        for font_match in font_block_pattern.finditer(body):
            font_name = font_match.group(1)
            font_key = font_name.lower()
            pieces.append(body[last:font_match.start()])

            if keep_first and font_key not in seen:
                seen.add(font_key)
                pieces.append(font_match.group(0))
            else:
                changed = True

            last = font_match.end()

        pieces.append(body[last:])
        cleaned_body = ''.join(pieces)

        if not keep_first:
            cleaned_without_comment = mirage_comment_pattern.sub('', cleaned_body)
            if cleaned_without_comment != cleaned_body:
                changed = True
            cleaned_body = cleaned_without_comment

        return cleaned_body, seen

    rebuilt = []
    cursor = 0

    for index, match in enumerate(matches):
        opening, body, closing = match.groups()
        rebuilt.append(text[cursor:match.start()])

        is_target = index == target_index
        cleaned_body, seen = clean_mirage_blocks(body, keep_first=is_target)

        if is_target:
            present = set(name.lower() for name in MIRAGE_FONT_NAMES if name.lower() in seen)
            missing = [spec for spec in MIRAGE_FONT_SPECS if spec[0].lower() not in present]

            if missing:
                changed = True
                # If the old comment is already present, do not add another one.
                has_comment = bool(mirage_comment_pattern.search(cleaned_body))
                additions = [] if has_comment else ['        <!-- Arctic Mirage custom fonts -->']
                additions.extend(_mirage_font_definition(*spec) for spec in missing)
                cleaned_body = cleaned_body.rstrip() + '\n' + '\n'.join(additions) + '\n    '

        rebuilt.append(opening + cleaned_body + closing)
        cursor = match.end()

    rebuilt.append(text[cursor:])
    return ''.join(rebuilt), changed

def install_mirage_fonts_into_active_skin():
    """Copy Mirage font files and inject Mirage_* definitions into the active skin.

    Kodi's Python XML windows can use the add-on XML, but the font manager loads
    font definitions from the active skin. This helper bridges that limitation.
    """
    skin_id, skin_path = _get_active_skin_path()
    if not skin_path:
        _dialog_ok('Arctic Mirage', 'Could not locate the active skin folder.')
        return False

    fontxml = _find_active_skin_fontxml(skin_path)
    if not fontxml:
        _dialog_ok('Arctic Mirage', 'Could not find Font.xml in the active skin: {}'.format(skin_id))
        return False

    missing = [filename for filename in MIRAGE_FONT_FILES if not os.path.exists(_addon_font_path(filename))]
    if missing:
        _dialog_ok(
            'Arctic Mirage',
            'Missing font file(s) in this add-on:\n\n{}\n\nPlace them in resources/skins/Default/fonts/ first.'.format(
                '\n'.join(missing)
            )
        )
        return False

    skin_fonts_dir = os.path.join(skin_path, 'fonts')
    try:
        if not os.path.exists(skin_fonts_dir):
            os.makedirs(skin_fonts_dir)
        for filename in MIRAGE_FONT_FILES:
            shutil.copy2(_addon_font_path(filename), os.path.join(skin_fonts_dir, filename))
    except Exception as exc:
        log('Unable to copy Mirage fonts into active skin: {}'.format(exc), xbmc.LOGERROR)
        _dialog_ok('Arctic Mirage', 'Could not copy fonts into the active skin fonts folder:\n\n{}'.format(exc))
        return False

    backup = fontxml + '.arcticmirage.bak'
    try:
        if not os.path.exists(backup):
            shutil.copy2(fontxml, backup)

        with open(fontxml, 'r', encoding='utf-8') as handle:
            text = handle.read()

        updated, changed = _inject_font_defs_into_fontxml(text)
        if changed:
            with open(fontxml, 'w', encoding='utf-8') as handle:
                handle.write(updated)

    except Exception as exc:
        log('Unable to update active skin Font.xml: {}'.format(exc), xbmc.LOGERROR)
        _dialog_ok('Arctic Mirage', 'Could not update the active skin Font.xml:\n\n{}'.format(exc))
        return False

    if changed:
        message = (
            'Installed Mirage font definitions into:\n\n{}\n\n'
            'Restart Kodi or reload the skin for font changes to apply.\n\n'
            'Backup created:\n{}'
        ).format(fontxml, backup)
    else:
        message = (
            'Mirage font definitions already exist in:\n\n{}\n\n'
            'Restart Kodi or reload the skin if changes are not visible.'
        ).format(fontxml)

    _dialog_ok('Arctic Mirage', message)
    log('Installed Mirage fonts into active skin {} at {}'.format(skin_id, skin_path), xbmc.LOGINFO)
    return True


def restore_active_skin_fontxml_backup():
    skin_id, skin_path = _get_active_skin_path()
    if not skin_path:
        _dialog_ok('Arctic Mirage', 'Could not locate the active skin folder.')
        return False

    fontxml = _find_active_skin_fontxml(skin_path)
    if not fontxml:
        _dialog_ok('Arctic Mirage', 'Could not find Font.xml in the active skin: {}'.format(skin_id))
        return False

    backup = fontxml + '.arcticmirage.bak'
    if not os.path.exists(backup):
        _dialog_ok('Arctic Mirage', 'No Arctic Mirage Font.xml backup was found for this skin.')
        return False

    try:
        shutil.copy2(backup, fontxml)
    except Exception as exc:
        log('Unable to restore active skin Font.xml backup: {}'.format(exc), xbmc.LOGERROR)
        _dialog_ok('Arctic Mirage', 'Could not restore Font.xml backup:\n\n{}'.format(exc))
        return False

    _dialog_ok(
        'Arctic Mirage',
        'Restored Font.xml backup for the active skin.\n\nRestart Kodi or reload the skin for changes to apply.'
    )
    return True
