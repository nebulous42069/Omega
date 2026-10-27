"""Remove known account fields from retained data of uninstalled add-ons.

Never deletes a data folder, guesses field names, or opens a missing database.
"""
import glob
import json
import os
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs


def _atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.reauthorize-wipe-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, os.stat(path).st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def scrub_xml(path, fields):
    if not os.path.isfile(path):
        return
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(path, parser=parser)
    changed = False
    for setting in tree.getroot().iter('setting'):
        key = setting.get('id')
        if key not in fields:
            continue
        wanted = fields[key]
        current = setting.get('value', setting.text or '')
        if current != wanted or 'default' in setting.attrib:
            setting.attrib.pop('default', None)
            if 'value' in setting.attrib:
                setting.set('value', wanted)
            else:
                setting.text = wanted
            changed = True
    if changed:
        _atomic_write(path, ET.tostring(tree.getroot(), encoding='utf-8', xml_declaration=True))


def scrub_database(path, fields):
    if not os.path.isfile(path):
        return
    conn = sqlite3.connect(path, timeout=10)
    try:
        columns = {row[1] for row in conn.execute('PRAGMA table_info(settings)')}
        if not {'setting_id', 'setting_value'}.issubset(columns):
            raise ValueError('Unsupported retained settings database schema')
        with conn:
            for key, value in fields.items():
                # A credential saved as a row default could otherwise return
                # the next time an add-on resets that row.
                if 'setting_default' in columns:
                    conn.execute('UPDATE settings SET setting_value=?, setting_default=? WHERE setting_id=?', (value, value, key))
                else:
                    conn.execute('UPDATE settings SET setting_value=? WHERE setting_id=?', (value, key))
    finally:
        conn.close()


def scrub_youtube(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as stream:
        data = json.load(stream)
    changed = [False]
    def blank(node):
        if isinstance(node, dict):
            if 'access_token' in node or 'refresh_token' in node:
                for key, value in (('access_token', ''), ('refresh_token', ''), ('token_expires', -1)):
                    if key in node and node[key] != value:
                        node[key] = value
                        changed[0] = True
            for value in node.values():
                blank(value)
        elif isinstance(node, list):
            for value in node:
                blank(value)
    blank(data)
    if changed[0]:
        _atomic_write(path, json.dumps(data, indent=4).encode('utf-8'))


def installed(addon_id):
    return (xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id)
            or xbmcvfs.exists('special://home/addons/%s/' % addon_id)
            or xbmcvfs.exists('special://xbmc/addons/%s/' % addon_id))


def wipe_retained_data():
    from reauthorize.modules import import_map, vault
    from reauthorize.modules.sync import trakt_wipe, crew_trakt, youtube_sync
    def mapped(fields):
        return {field: ('0' if source == 'trakt.expires' else '')
                for field, source in fields.items()
                if source in vault.CREDENTIAL_KEYS and vault.is_credential_key(source)}
    targets = {addon: mapped(fields) for addon, fields in import_map.SETTINGS.items()}
    for extra in (trakt_wipe._JSON_SETTINGS, trakt_wipe._ALSO_BLANK):
        for addon, fields in extra.items():
            targets.setdefault(addon, {}).update({key: '' for key in fields})
    crew_fields = targets.setdefault('plugin.video.thecrew', {})
    for key in crew_trakt._signin_ids():
        crew_fields.setdefault(key, '0' if key in ('trakt.expires', 'trakt.expires_at') else '')
    targets['plugin.video.thecrew']['trakt.revoked'] = 'true'
    targets.setdefault(youtube_sync.YT_ADDON_ID, {}).update({key: '' for key in youtube_sync.API_KEYS})
    addons = set(targets) | set(import_map.DATABASES)
    failed = []
    def attempt(addon, action, path, fields=None):
        try:
            action(path) if fields is None else action(path, fields)
        except Exception as exc:
            if addon not in failed:
                failed.append(addon)
            # Never log file contents, credential values or exception text.
            xbmc.log('[ReAuthorize Wipe] Retained data cleanup failed for %s / %s (%s)' %
                     (addon, os.path.basename(path), type(exc).__name__), xbmc.LOGWARNING)
    for addon in sorted(addons):
        if installed(addon):
            continue  # Keep Kodi's settings API responsible for live add-ons.
        folder = xbmcvfs.translatePath('special://profile/addon_data/%s/' % addon)
        fields = targets.get(addon, {})
        paths = {os.path.join(folder, 'settings.xml'), os.path.join(folder, 'settings.xml.bak')}
        paths.update(glob.glob(os.path.join(folder, 'settings.xml.health_backup_*')))
        paths.update(glob.glob(os.path.join(folder, 'settings*.bak')))
        if addon == 'plugin.video.thecrew':
            paths.update(crew_trakt.backup_files())
        if fields:
            for path in sorted(paths):
                attempt(addon, scrub_xml, path, fields)
        spec = import_map.DATABASES.get(addon)
        if spec:
            attempt(addon, scrub_database, os.path.join(folder, spec['file']), mapped(spec['keys']))
        if addon == youtube_sync.YT_ADDON_ID:
            attempt(addon, scrub_youtube, os.path.join(folder, 'access_manager.json'))
    return failed
