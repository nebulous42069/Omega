# ReAuthorize compatibility adapter; distributed under GPL-3.0-or-later.
"""Per-invocation adapters for the bundled Diggz Account Manager engine. Other add-ons use Kodi normally."""
import contextlib
import json
import os
import re
import runpy
import sys
import threading
import time
import types
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, urlsplit, urlencode

import xbmc as REAL_XBMC
import xbmcaddon as REAL_ADDON
import xbmcgui as GUI
import xbmcplugin as REAL_PLUGIN
import xbmcvfs as REAL_VFS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ID = 'script.module.authorizediggz'
CORE_ID = 'script.module.authorizediggz-core'
OWN = {MAIN_ID: os.path.join(ROOT, 'main'), CORE_ID: os.path.join(ROOT, 'core')}
_LOCK = threading.RLock()
_SUPPRESS_SETTINGS = False
_CORE_ITEMS = None


def mapped(path):
    if not isinstance(path, str):
        return path
    main_schema = os.path.join(OWN[MAIN_ID], 'resources', 'settings.xml')
    if path in (main_schema, 'special://home/addons/' + MAIN_ID + '/resources/settings.xml'):
        return os.path.join(ROOT, 'resources', 'settings.xml')
    for id, root in sorted(OWN.items(), key=lambda p: -len(p[0])):
        prefix = 'special://home/addons/' + id
        if path == prefix or path.startswith(prefix + '/'):
            return root + path[len(prefix):]
    return path


def profile(id=MAIN_ID):
    return REAL_VFS.translatePath('special://profile/addon_data/' + id + '/')


@contextlib.contextmanager
def file_lock(path, blocking=True):
    """Kernel locks release on process exit, including Kodi crashes."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stream = open(path, 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if os.path.getsize(path) == 0:
                stream.write(b'0'); stream.flush()
            deadline = time.monotonic() + (30 if blocking else 0)
            while True:
                try:
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        yield
    finally:
        stream.close()


def defaults(id):
    base = ROOT if id == MAIN_ID else OWN[id]
    path = os.path.join(base, 'resources', 'settings.xml')
    if not os.path.exists(path):
        return {}
    return {s.get('id'): s.get('default', '') for s in ET.parse(path).iter('setting') if s.get('id')}


def read_values(id):
    path = os.path.join(profile(id), 'settings.xml')
    if not os.path.exists(path):
        return {}
    # Do not erase malformed data. Upstream settings_health handles repair.
    root = ET.parse(path).getroot()
    return {s.get('id'): s.get('value', s.text or '') for s in root.iter('setting') if s.get('id')}


class EmbeddedAddon:
    def __init__(self, id):
        self.id = id

    def getAddonInfo(self, name):
        info = {'id': self.id, 'name': 'Diggz Account Manager', 'version': REAL_ADDON.Addon(MAIN_ID).getAddonInfo('version'),
                'path': OWN[self.id], 'profile': profile(self.id),
                'icon': os.path.join(OWN[self.id], 'icon.png'),
                'fanart': os.path.join(OWN[self.id], 'fanart.jpg'), 'author': 'Hermit Murman'}
        return info.get(name, '')

    def getSetting(self, key):
        with _LOCK, file_lock(os.path.join(profile(self.id), 'embedded-settings.lock')):
            if self.id == MAIN_ID:
                return REAL_ADDON.Addon(MAIN_ID).getSetting(key)
            return read_values(self.id).get(key, defaults(self.id).get(key, ''))

    def setSetting(self, key, value):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        with _LOCK, file_lock(os.path.join(profile(self.id), 'embedded-settings.lock')):
            if self.id == MAIN_ID:
                return REAL_ADDON.Addon(MAIN_ID).setSetting(key, str(value))
            values = read_values(self.id)
            values[key] = str(value)
            root = ET.Element('settings', {'version': '2'})
            for id, text in sorted(values.items()):
                ET.SubElement(root, 'setting', {'id': id}).text = text
            path = os.path.join(profile(self.id), 'settings.xml')
            temp = path + '.embedded-tmp'
            with open(temp, 'wb') as stream:
                stream.write(ET.tostring(root, encoding='utf-8', xml_declaration=True))
                stream.flush()
                fsync = getattr(os, 'fsync', None)
                if fsync is not None:
                    fsync(stream.fileno())
            os.replace(temp, path)

    def getLocalizedString(self, number):
        # Upstream's menu definitions predominantly use literal labels.
        candidates = [os.path.join(ROOT, 'resources', 'language',
                                   'resource.language.en_gb', 'strings.po')]
        for path in candidates:
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf-8-sig') as stream:
                text = stream.read()
            match = re.search(r'msgctxt "#' + str(number) + r'"\s+msgid "(.*?)"\s+msgstr "(.*?)"', text, re.S)
            if match:
                return match.group(2) or match.group(1)
        return REAL_XBMC.getLocalizedString(int(number))

    def openSettings(self):
        if not _SUPPRESS_SETTINGS:
            REAL_XBMC.executebuiltin('Addon.OpenSettings(%s)' % MAIN_ID)

    def getSettingBool(self, key): return self.getSetting(key).lower() == 'true'
    def getSettingInt(self, key): return int(float(self.getSetting(key) or '0'))
    def getSettingNumber(self, key): return float(self.getSetting(key) or '0')
    getSettingString = getSetting
    setSettingBool = setSetting
    setSettingInt = setSetting
    setSettingNumber = setSetting
    setSettingString = setSetting


def Addon(id=None):
    id = id or MAIN_ID
    return EmbeddedAddon(id) if id in OWN else REAL_ADDON.Addon(id)


def run_main(arguments):
    # View-only actions must not run default.py's modal closing, sign-in
    # follow-ups, or the legacy Core router's management actions.
    params = dict(piece.strip().split('=', 1)
                  for arg in arguments for piece in arg.split('&') if '=' in piece)
    if params.get('action') == 'wizardTrackingPreference':
        from reauthorize.modules.tracking_preference import apply_from_wizard
        return apply_from_wizard()
    if params.get('action') == 'wizardRestore':
        from wizard_support import restore_and_sync
        return restore_and_sync()
    if params.get('action') in ('wizardStatus', 'statusDashboard', 'viewAuthorizations'):
        from wizard_support import show_status
        return show_status()
    previous = sys.argv
    try:
        sys.argv = [os.path.join(OWN[MAIN_ID], 'lib', 'default.py')] + list(arguments)
        runpy.run_path(sys.argv[0], run_name='__main__')
    finally:
        sys.argv = previous


def own_condition(condition):
    for id in OWN:
        if condition in ('System.HasAddon(%s)' % id, 'System.AddonIsEnabled(%s)' % id):
            return True
    return REAL_XBMC.getCondVisibility(condition)


def execute(command, wait=False):
    stripped = command.strip()
    if re.match(r'^Addon.OpenSettings\(\s*["\']?script\.module\.authorizediggz(?:-core)?["\']?\s*\)$', stripped, re.I):
        Addon(MAIN_ID).openSettings(); return
    if stripped.lower().startswith('runscript('):
        inner = stripped[len('RunScript('):-1]
        parts = [p.strip() for p in inner.split(',')]
        if parts[0].strip('"\'') in OWN:
            run_main(parts[1:]); return
    if 'plugin://script.module.authorizediggz-core' in stripped:
        match = re.search(r'plugin://script\.module\.authorizediggz-core/\?([^\s"\)]*)', stripped)
        if match:
            query = match.group(1)
            if query.endswith(',return'):
                query = query[:-7]
            query = query.rstrip(',')
            run_core(query); return
    if _CORE_ITEMS is not None and stripped.lower().startswith('container.'):
        return
    return REAL_XBMC.executebuiltin(command, wait)


def add_directory_item(handle, url, listitem, isFolder=False, **kwargs):
    if _CORE_ITEMS is not None:
        _CORE_ITEMS.append((url, listitem.getLabel(), isFolder))
        return True
    return REAL_PLUGIN.addDirectoryItem(handle, url, listitem, isFolder, **kwargs)


def report_error(exc, stage):
    import traceback
    frames = traceback.extract_tb(exc.__traceback__)
    # Frame locations only: never print exception text, source lines, locals,
    # query strings, usernames, tokens, or request URLs.
    trace = ' > '.join('%s:%d:%s' % (os.path.basename(f.filename), f.lineno, f.name) for f in frames)
    REAL_XBMC.log('[Diggz Account Manager] %s: %s | %s' %
                  (stage, type(exc).__name__, trace), REAL_XBMC.LOGERROR)


def run_core(query):
    params = dict(parse_qsl(query))
    if params.get('mode') == 'wipeclean' and params.get('name') == 'all':
        # Explicitly confirmed legacy reset, not an account-viewer request.
        # Keep management modes out of the read-only viewer.
        previous = sys.argv
        try:
            sys.argv = ['plugin://' + CORE_ID + '/', '-1', '?' + query]
            from libs.common.router import Router
            return Router().dispatch(-1, query)
        finally:
            sys.argv = previous
    # Legacy account-viewer links open the same dashboard as Manage > View Status.
    from wizard_support import show_status
    return show_status()


def add_python_dependencies(addon_id, visited=None):
    visited = visited if visited is not None else set()
    if addon_id in visited or addon_id.startswith('xbmc.'):
        return
    visited.add(addon_id)
    path = REAL_ADDON.Addon(addon_id).getAddonInfo('path')
    manifest = ET.parse(os.path.join(path, 'addon.xml')).getroot()
    for extension in manifest.findall('extension'):
        if extension.get('point') == 'xbmc.python.module':
            for library in extension.get('library', '').split('|'):
                module_path = os.path.join(path, library)
                if library and module_path not in sys.path:
                    sys.path.insert(0, module_path)
    for dependency in manifest.findall('./requires/import'):
        if dependency.get('optional', 'false') != 'true':
            add_python_dependencies(dependency.get('addon', ''), visited)


def install(suppress_settings=False):
    global _SUPPRESS_SETTINGS
    _SUPPRESS_SETTINGS = suppress_settings
    add_python_dependencies('script.module.requests')
    sys.path.insert(0, os.path.join(OWN[MAIN_ID], 'lib'))
    sys.path.insert(0, os.path.join(OWN[CORE_ID], 'resources'))
    api = types.ModuleType('xbmcaddon')
    api.Addon = Addon
    api.__getattr__ = lambda name: getattr(REAL_ADDON, name)
    sys.modules['xbmcaddon'] = api
    kodi = types.ModuleType('xbmc')
    kodi.executebuiltin = execute
    kodi.getCondVisibility = own_condition
    kodi.__getattr__ = lambda name: getattr(REAL_XBMC, name)
    sys.modules['xbmc'] = kodi
    vfs = types.ModuleType('xbmcvfs')
    vfs.translatePath = lambda path: REAL_VFS.translatePath(mapped(path))
    for name in ('File', 'exists', 'mkdir', 'mkdirs', 'delete', 'rmdir', 'listdir', 'Stat'):
        if hasattr(REAL_VFS, name):
            real = getattr(REAL_VFS, name)
            setattr(vfs, name, lambda path, *a, _real=real, **kw: _real(mapped(path), *a, **kw))
    for name in ('copy', 'rename'):
        if hasattr(REAL_VFS, name):
            real = getattr(REAL_VFS, name)
            setattr(vfs, name, lambda src, dst, *a, _real=real: _real(mapped(src), mapped(dst), *a))
    vfs.__getattr__ = lambda name: getattr(REAL_VFS, name)
    sys.modules['xbmcvfs'] = vfs
    plugin = types.ModuleType('xbmcplugin')
    plugin.addDirectoryItem = add_directory_item
    def noop_or_real(name):
        def call(*a, **kw):
            return True if _CORE_ITEMS is not None else getattr(REAL_PLUGIN, name)(*a, **kw)
        return call
    for name in ('endOfDirectory', 'setContent', 'setResolvedUrl', 'addSortMethod'):
        setattr(plugin, name, noop_or_real(name))
    plugin.__getattr__ = lambda name: getattr(REAL_PLUGIN, name)
    sys.modules['xbmcplugin'] = plugin
