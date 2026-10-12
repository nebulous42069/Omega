# Bundled Xenon Cast Helper configuration, migrated from the supplied Diggz add-on.
import json
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

CONFIG = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/casthelper.json')
DEFAULTS = {'tmdb_api_key': 'f5608fba6ab49e9985828b35d5653321', 'tmdb_bearer_token': 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmNTYwOGZiYTZhYjQ5ZTk5ODU4MjhiMzVkNTY1MzMyMSIsIm5iZiI6MTUzMDI2NzI0OS44NDcwMDAxLCJzdWIiOiI1YjM2MDY3MTkyNTE0MTNjOTMwMjkzZDMiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.sY0aCEb0tkFBHMJIxNRMbjYEmBu1aQF7z-uzRhu_134', 'language': 'en-US', 'max_cast': '20'}  # Populated from the supplied add-on settings at packaging time.


def save(values):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG + '.tmp', 'w', encoding='utf-8') as stream:
        json.dump(values, stream)
    os.replace(CONFIG + '.tmp', CONFIG)


def read():
    if os.path.isfile(CONFIG):
        with open(CONFIG, encoding='utf-8') as stream:
            return dict(DEFAULTS, **json.load(stream))
    values = dict(DEFAULTS)
    if xbmc.getCondVisibility('System.HasAddon(script.xenon.casthelper)'):
        old = xbmcaddon.Addon('script.xenon.casthelper')
        for key in DEFAULTS:
            values[key] = old.getSetting(key)
    save(values)
    return values


def configure():
    values = read()
    fields = [('tmdb_api_key', 'TMDb v3 key or v4 token'),
              ('tmdb_bearer_token', 'TMDb bearer token (takes priority)'),
              ('language', 'Language, e.g. en-US'), ('max_cast', 'Max cast members (1-50)')]
    dialog = xbmcgui.Dialog()
    index = dialog.select('Xenon Cast Helper settings', [label for _, label in fields])
    if index < 0:
        return
    key, label = fields[index]
    keyboard = xbmc.Keyboard(values.get(key, ''), label, key.startswith('tmdb_'))
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return
    value = keyboard.getText().strip()
    if key == 'max_cast':
        if not value.isdigit() or not 1 <= int(value) <= 50:
            dialog.ok('Xenon Cast Helper', 'Enter a number from 1 to 50.')
            return
    values[key] = value
    save(values)
