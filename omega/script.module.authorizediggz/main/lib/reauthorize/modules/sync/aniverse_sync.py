"""AniVerse's native Real-Debrid token store and TorBox setting."""
import json
import math
import os
import tempfile

import xbmcvfs

from reauthorize.modules import control, sync_support

ADDON_ID = 'plugin.video.aniverse'
RD_FIELDS = {
    'client_id': 'realdebrid.client_id',
    'client_secret': 'realdebrid.secret',
    'refresh_token': 'realdebrid.refresh',
    'access_token': 'realdebrid.token',
}


def _rd_path():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/realdebrid.json' % ADDON_ID)


def read_rd():
    try:
        with open(_rd_path(), encoding='utf-8') as stream:
            data = json.load(stream)
    except (FileNotFoundError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _expiry(value):
    try:
        seconds = float(value)
        return seconds if math.isfinite(seconds) and seconds > 0 else 0
    except (TypeError, ValueError):
        return 0


def rd_configured(data):
    return all(isinstance(data.get(field), str) and data[field].strip() for field in RD_FIELDS)


def clear_rd():
    path = _rd_path()
    for candidate in (path, path + '.tmp'):
        try:
            os.remove(candidate)
        except FileNotFoundError:
            pass


def _same_device(data, settings):
    return all(data.get(field) and data[field] == settings.get(RD_FIELDS[field])
               for field in ('client_id', 'client_secret'))


def clear_matching_rd(before):
    if _same_device(read_rd(), before):
        clear_rd()


def _write_rd():
    settings = {key: control.setting(key) for key in RD_FIELDS.values()}
    data = {field: settings[key] for field, key in RD_FIELDS.items()}
    if not rd_configured(data):
        return
    data['expires_at'] = _expiry(control.setting('realdebrid.expires'))
    previous = read_rd()
    if _same_device(previous, settings) and rd_configured(previous):
        # AniVerse can refresh on its own. Keep newer credentials for this device.
        if _expiry(previous.get('expires_at')) > data['expires_at']:
            return
        if all(previous.get(key) == value for key, value in data.items()):
            return
        data = {**previous, **data}
    path = _rd_path()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.reauthorize-rd-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def send(tag):
    if tag not in ('rd', 'torbox') or not sync_support.installed(ADDON_ID):
        return
    if tag == 'torbox':
        value = '' if control.wiping() else control.setting('torbox.token')
        sync_support.put(ADDON_ID, [('torbox_api_key', value)], control.wiping())
    elif control.wiping():
        clear_rd()
    else:
        _write_rd()
