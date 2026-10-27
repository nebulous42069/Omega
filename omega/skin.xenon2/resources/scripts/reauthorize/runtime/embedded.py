# Xenon embedded integration adapter; distributed under GPL-3.0-or-later.
"""Per-invocation Kodi adapters for embedded ReAuthorize. Other add-ons use Kodi normally."""
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
MAIN_ID = 'script.module.reauthorize'
CORE_ID = 'script.module.reauthorize-core'
OWN = {MAIN_ID: os.path.join(ROOT, 'main'), CORE_ID: os.path.join(ROOT, 'core')}
_LOCK = threading.RLock()
_UI_OPEN = False
_SUPPRESS_SETTINGS = False
_CORE_ITEMS = None
_SERVICE_MODE = False


def mapped(path):
    if not isinstance(path, str):
        return path
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
    path = os.path.join(OWN[id], 'resources', 'settings.xml')
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
        info = {'id': self.id, 'name': 'ReAuthorize (Xenon Embedded)', 'version': '1.4.5',
                'path': OWN[self.id], 'profile': profile(self.id),
                'icon': os.path.join(OWN[self.id], 'icon.png'),
                'fanart': os.path.join(OWN[self.id], 'fanart.jpg'), 'author': 'Hermit Murman'}
        return info.get(name, '')

    def getSetting(self, key):
        with _LOCK, file_lock(os.path.join(profile(self.id), 'embedded-settings.lock')):
            return read_values(self.id).get(key, defaults(self.id).get(key, ''))

    def setSetting(self, key, value):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        with _LOCK, file_lock(os.path.join(profile(self.id), 'embedded-settings.lock')):
            values = read_values(self.id)
            values[key] = str(value)
            root = ET.Element('settings', {'version': '2'})
            for id, text in sorted(values.items()):
                ET.SubElement(root, 'setting', {'id': id}).text = text
            path = os.path.join(profile(self.id), 'settings.xml')
            temp = path + '.embedded-tmp'
            with open(temp, 'wb') as stream:
                stream.write(ET.tostring(root, encoding='utf-8', xml_declaration=True))
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, path)

    def getLocalizedString(self, number):
        # Upstream's menu definitions predominantly use literal labels.
        candidates = [os.path.join(OWN[id], 'resources', 'language', language, 'strings.po')
                      for id in (self.id, MAIN_ID) for language in ('resource.language.en_gb', 'English')]
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
        if not _SUPPRESS_SETTINGS and not _UI_OPEN:
            open_settings()

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
    if params.get('action') == 'wizardRestore':
        from wizard_support import restore_and_sync
        return restore_and_sync()
    if params.get('action') == 'wizardStatus':
        from wizard_support import show_status
        return show_status()
    if params.get('action') == 'viewAuthorizations':
        return view_authorizations(params.get('mode', ''))
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
    global _SUPPRESS_SETTINGS
    stripped = command.strip()
    if re.match(r'^Addon.OpenSettings\(\s*["\']?script\.module\.reauthorize(?:-core)?["\']?\s*\)$', stripped, re.I):
        Addon(MAIN_ID).openSettings(); return
    if stripped.lower().startswith('runscript('):
        inner = stripped[len('RunScript('):-1]
        parts = [p.strip() for p in inner.split(',')]
        if parts[0].strip('"\'') in OWN:
            run_main(parts[1:]); return
    if 'plugin://script.module.reauthorize-core' in stripped:
        match = re.search(r'plugin://script\.module\.reauthorize-core/\?([^\s"\)]*)', stripped)
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
    REAL_XBMC.log('[Embedded ReAuthorize R3] %s: %s | %s' %
                  (stage, type(exc).__name__, trace), REAL_XBMC.LOGERROR)


def view_authorizations(mode):
    global _CORE_ITEMS
    methods = {
        'realdebrid': 'debrid_menu', 'premiumize': 'premiumize_menu',
        'alldebrid': 'alldebrid_menu', 'torbox': 'torbox_menu',
        'easydebrid': 'easydebrid_menu', 'offcloud': 'offcloud_menu',
        'easynews': 'easynews_menu', 'filepursuit': 'filepursuit_menu',
        'trakt': 'trakt_menu',
    }
    if mode not in methods:
        GUI.Dialog().ok('ReAuthorize', 'This authorization viewer is not supported.')
        return
    from libs.gui import menu
    from libs.common import directory
    original = directory._add_menu_item
    previous_items = _CORE_ITEMS
    _CORE_ITEMS = []
    def capture(display, params, *args, **kwargs):
        # Only informational account rows. No plugin links, settings links,
        # separators, or legacy management routes are executed by this viewer.
        if params and params.get('name') and not params.get('mode'):
            _CORE_ITEMS.append(str(display))
    directory._add_menu_item = capture
    try:
        getattr(menu, methods[mode])()
        labels = list(_CORE_ITEMS)
    finally:
        directory._add_menu_item = original
        _CORE_ITEMS = previous_items
    if not labels:
        GUI.Dialog().ok('ReAuthorize - Authorizations', 'No supported installed add-ons were found for this service.')
        return
    while GUI.Dialog().select('ReAuthorize - Authorizations', labels) >= 0:
        pass  # Read-only; selecting a status cannot invoke another action.


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
    return view_authorizations(params.get('mode', ''))


def text_label(value):
    value = value or ''
    if value.isdigit():
        return Addon().getLocalizedString(int(value))
    return value


def setting_condition(expression, rows, index, addon):
    expression = (expression or 'true').strip()
    if expression.lower() in ('true', 'false'):
        return expression.lower() == 'true'
    if ' + ' in expression:
        return all(setting_condition(p, rows, index, addon) for p in expression.split(' + '))
    if ' | ' in expression:
        return any(setting_condition(p, rows, index, addon) for p in expression.split(' | '))
    if expression.startswith('!'):
        return not setting_condition(expression[1:], rows, index, addon)
    match = re.fullmatch(r'(eq|gt|lt)\((-?\d+),(.*)\)', expression)
    if match:
        position = index + int(match.group(2))
        if not 0 <= position < len(rows):
            return False
        other = rows[position]
        value = addon.getSetting(other.get('id', ''))
        expected = match.group(3)
        if match.group(1) == 'eq': return value == expected
        try:
            return float(value) > float(expected) if match.group(1) == 'gt' else float(value) < float(expected)
        except ValueError:
            return False
    return own_condition(expression)


def open_settings():
    """Persistent Xenon-style settings window with source-defined categories."""
    global _UI_OPEN
    if _UI_OPEN or _SUPPRESS_SETTINGS:
        return
    from settings_window import SettingsWindow
    categories = ET.parse(os.path.join(OWN[MAIN_ID], 'resources', 'settings.xml')).getroot().findall('category')
    state = {'category': 0, 'row': 0, 'focus': 'categories'}
    _UI_OPEN = True
    try:
        while True:
            window = SettingsWindow('XenonReAuthorizeSettings.xml', ROOT, 'Default', '1080i')
            window.configure(categories, state)
            window.doModal()
            action = window.request
            del window
            if not action:
                return
            try:
                execute(action)
            except Exception as exc:
                report_error(exc, 'settings action')
                GUI.Dialog().ok('Embedded ReAuthorize',
                                'The action could not finish. Look for [Embedded ReAuthorize R3] in kodi.log.')
    finally:
        _UI_OPEN = False
        GUI.Window(10000).clearProperty('accountmgr.active')


class SkinMonitor:
    def __init__(self):
        self.real = REAL_XBMC.Monitor()
    def abortRequested(self):
        return self.real.abortRequested() or (_SERVICE_MODE and (REAL_XBMC.getSkinDir() != 'skin.xenon2' or GUI.Window(10000).getProperty('Xenon.ReAuthorize.Resetting') == 'true'))
    def waitForAbort(self, timeout):
        deadline = time.monotonic() + timeout
        while not self.abortRequested():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if self.real.waitForAbort(min(remaining, 0.5)):
                return True
        return True
    def __getattr__(self, name):
        return getattr(self.real, name)


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


def install(suppress_settings=False, service=False):
    global _SUPPRESS_SETTINGS, _SERVICE_MODE
    _SUPPRESS_SETTINGS = suppress_settings
    _SERVICE_MODE = service
    add_python_dependencies('script.module.requests')
    sys.path.insert(0, os.path.join(OWN[MAIN_ID], 'lib'))
    sys.path.insert(0, os.path.join(OWN[CORE_ID], 'resources'))
    api = types.ModuleType('xbmcaddon')
    api.Addon = Addon
    api.__getattr__ = lambda name: getattr(REAL_ADDON, name)
    sys.modules['xbmcaddon'] = api
    kodi = types.ModuleType('xbmc')
    kodi.Monitor = SkinMonitor
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
