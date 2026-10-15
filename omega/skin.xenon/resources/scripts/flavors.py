# SPDX-License-Identifier: GPL-2.0-or-later
"""Xenon settings-only preset switcher. Runs inside the skin via RunScript."""
import io
import json
import os
import time
import sys
import re
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcvfs

TITLE = 'Xenon Flavors'
CATALOG = 'https://raw.githubusercontent.com/Buildtexts69/omegabuilds/main/X2/Xenon_Flavors.xml'
ACTION = 'RunScript(special://skin/resources/scripts/flavors.py)'
LIMIT = 32 * 1024 * 1024


def parse_settings(data):
    if len(data) > 4 * 1024 * 1024 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsupported or oversized settings XML.')
    root = ET.fromstring(data)
    if root.tag != 'settings':
        raise ValueError('Expected a skin settings.xml file.')
    result = {}
    for node in root:
        key, kind = node.get('id', ''), node.get('type', '')
        if node.tag != 'setting' or (not key or any(ord(c) < 32 for c in key)) or kind not in ('bool', 'string'):
            raise ValueError('Unsupported skin setting: ' + key)
        value = node.text or ''
        if kind == 'bool':
            if value.lower() not in ('true', 'false'):
                raise ValueError('Invalid boolean: ' + key)
            value = value.lower() == 'true'
        elif 'plugin.program.diggzflavors' in value:
            suffix = key.lower().rsplit('.', 1)[-1]
            if suffix == 'list':
                value = ''  # This field is browsed as a directory, not executed.
            elif suffix == 'icon':
                value = 'special://home/addons/skin.xenon/resources/icon.png'
            elif suffix in ('fanart', 'thumb'):
                value = 'special://home/addons/skin.xenon/resources/fanart.jpg'
            elif suffix == 'path' or value.lower().startswith(('activatewindow(', 'runscript(', 'runaddon(', 'playmedia(')):
                value = ACTION
        # Kodi has independent boolean and string namespaces. Keep both.
        # Repeated entries within one namespace resolve to the last value.
        result[(key, kind)] = (kind, value)
    if not result:
        raise ValueError('The preset contains no settings.')
    return result


def settings_bytes(settings):
    root = ET.Element('settings')
    for (key, _), (kind, value) in sorted(settings.items()):
        ET.SubElement(root, 'setting', id=key, type=kind).text = str(value).lower() if kind == 'bool' else value
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def fetch(url):
    if urlparse(url).scheme != 'https':
        raise ValueError('Preset URLs must use HTTPS.')
    with urlopen(Request(url, headers={'User-Agent': 'Xenon-Flavors/1.0'}), timeout=30) as response:
        if urlparse(response.geturl()).scheme != 'https':
            raise ValueError('Insecure download redirect.')
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Download exceeds the 32 MB settings-only limit.')
    return data


def preset_settings(data):
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return parse_settings(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        matches = [n for n in archive.infolist() if not n.is_dir() and
                   (n.filename.replace('\\', '/').lower().endswith('/addon_data/skin.xenon/settings.xml')
                    or n.filename.lower() in ('settings.xml', 'skin.xenon/settings.xml'))]
        if len(matches) != 1:
            raise ValueError('ZIP must contain exactly one Xenon settings.xml.')
        if matches[0].file_size > 4 * 1024 * 1024:
            raise ValueError('Settings file is too large.')
        # Read the selected member only; never extract archive paths or other build files.
        return parse_settings(archive.read(matches[0]))


def catalog_entries(data, base):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsupported catalog XML.')
    root = ET.fromstring(data)
    def value(node, key):
        return (node.findtext(key) or node.get(key) or '').strip()
    entries = []
    for node in root:
        if node.tag in ('categories', 'sections'):
            entries.extend(catalog_entries(ET.tostring(node), base))
        elif node.tag in ('build', 'category', 'section'):
            name = value(node, 'name') or value(node, 'title') or node.get('id', 'Preset')
            url = value(node, 'url')
            children = catalog_entries(ET.tostring(node), base) if node.tag != 'build' else []
            if children or url:
                entries.append((name, children or urljoin(base, url), node.tag != 'build' or urlparse(url).path.lower().endswith('.xml'), {'id': value(node, 'id'), 'version': value(node, 'version')}))
    return entries


def xenon_catalog_entries(data, base):
    # The original skin shortcut used section=Xenon. Match that exact section,
    # with the visible Xenon Flavors name as a fallback; never match Xenon 2.
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsupported catalog XML.')
    root = ET.fromstring(data)
    nodes = [node for node in root.iter() if node.tag in ('category', 'section', 'build')]
    matches = [node for node in nodes if (node.get('id') or '').strip().casefold() == 'xenon']
    if not matches:
        matches = [node for node in nodes if
                   (node.findtext('name') or node.get('name') or node.findtext('title')
                    or node.get('title') or '').strip().casefold() == 'xenon flavors']
    if len(matches) != 1:
        raise ValueError('Could not identify the Xenon Flavors category in the online catalog.')
    category = matches[0]
    entries = catalog_entries(ET.tostring(category), base)
    if not entries:
        url = (category.findtext('url') or category.get('url') or '').strip()
        if url:
            source = urljoin(base, url)
            entries = catalog_entries(fetch(source), source)
    if not entries:
        raise ValueError('The Xenon Flavors category contains no presets.')
    return entries


def choose_online():
    entries = xenon_catalog_entries(fetch(CATALOG), CATALOG)
    for _ in range(10):
        index = xbmcgui.Dialog().select(TITLE, [item[0] for item in entries])
        if index < 0:
            return None
        name, source, folder, metadata = entries[index]
        if isinstance(source, list):
            entries = source
        elif folder:
            entries = catalog_entries(fetch(source), source)
        else:
            return name, preset_settings(fetch(source)), metadata
    raise ValueError('Catalog nesting is too deep.')


def active_skin_id():
    # getSkinDir() reflects the requested setting before GUI loading completes.
    # special://skin is the graphics context's currently loaded media directory.
    path = xbmcvfs.translatePath('special://skin/addon.xml')
    with open(path, 'rb') as stream:
        return ET.parse(stream).getroot().get('id', '')


def trace(message):
    xbmc.log('Xenon flavor switch: ' + message, xbmc.LOGINFO)
    path = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/'), 'flavor-switch.log')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as stream:
        stream.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')


def load_skin(skin_id):
    if active_skin_id() == skin_id and xbmc.getSkinDir() == skin_id:
        return
    trace('Request skin: ' + skin_id)
    monitor = xbmc.Monitor()
    # Match the working Diggz switcher: finish dialog teardown and enter Home.
    xbmc.executebuiltin('Dialog.Close(all,true)')
    if monitor.waitForAbort(0.15):
        raise RuntimeError('Kodi is shutting down')
    xbmc.executebuiltin('ActivateWindow(home)')
    if monitor.waitForAbort(0.15):
        raise RuntimeError('Kodi is shutting down')
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
               'params': {'setting': 'lookandfeel.skin', 'value': skin_id}}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if response.get('result') is not True:
        raise RuntimeError('Kodi refused to select ' + skin_id)
    deadline = time.monotonic() + 45
    monitor = xbmc.Monitor()
    accepted_prompt = False
    clicked_visible_prompt = False
    mismatch_since = None
    settled_since = None
    while time.monotonic() < deadline:
        loaded = active_skin_id() == skin_id
        prompt = any(xbmc.getCondVisibility(check) for check in (
            'Window.IsVisible(yesnodialog)', 'Window.IsVisible(DialogYesNo.xml)',
            'Window.IsVisible(YesNoDialog)'))
        if loaded and prompt:
            settled_since = None
            mismatch_since = None
            if not clicked_visible_prompt:
                if monitor.waitForAbort(0.08):
                    break
                # No Window/getControl handles: same builtin as script.diggzskins.
                # Send only during this requested skin change, once per visible prompt.
                xbmc.executebuiltin('SendClick(11)')
                trace('Sent Yes to skin confirmation: ' + skin_id)
                clicked_visible_prompt = True
                accepted_prompt = True
        elif not prompt:
            clicked_visible_prompt = False
            if loaded and accepted_prompt and xbmc.getSkinDir() == skin_id:
                mismatch_since = None
                if settled_since is None:
                    settled_since = time.monotonic()
                elif time.monotonic() - settled_since >= 2:
                    trace('Skin confirmed and settled: ' + skin_id)
                    return
            elif accepted_prompt:
                # Do not mistake a transient requested/loaded mismatch for rejection.
                settled_since = None
                if mismatch_since is None:
                    mismatch_since = time.monotonic()
                    trace('Waiting for skin state to settle: ' + skin_id)
                elif time.monotonic() - mismatch_since >= 5:
                    raise RuntimeError('Skin reverted after confirmation: ' + skin_id)
        if monitor.waitForAbort(0.1):
            break
    raise RuntimeError('Skin change did not finish: ' + skin_id)


def clean_flavor_name(name):
    name = re.sub(r'\[/?(?:B|I|COLOR[^\]]*)\]', '', name or '', flags=re.I)
    return ' '.join(name.split()).strip()[:120]


def read_flavor_state(profile):
    path = os.path.join(profile, 'flavor-state.json')
    if not os.path.isfile(path):
        return {'current': '', 'backups': {}}
    with open(path, encoding='utf-8') as stream:
        state = json.load(stream)
    if not isinstance(state, dict) or not isinstance(state.get('backups'), dict):
        raise ValueError('Invalid flavor backup index.')
    return state


def save_flavor_state(profile, state):
    atomic_save(os.path.join(profile, 'flavor-state.json'),
                json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))


def flavor_backup_filename(name, backups):
    slug = re.sub(r'[^A-Za-z0-9_-]+', '_', name).strip('_')[:80] or 'Flavor'
    filename = slug + '_backup.xml'
    used = {entry['file'].casefold(): key for key, entry in backups.items()}
    if filename.casefold() in used and used[filename.casefold()] != name.casefold():
        slug += '_' + hashlib.sha256(name.casefold().encode('utf-8')).hexdigest()[:8]
        filename = slug + '_backup.xml'
    return filename


def save_flavor_backup(profile, state, name, xml):
    name = clean_flavor_name(name) or 'Current setup'
    key = name.casefold()
    record = state['backups'].get(key)
    filename = record['file'] if record else flavor_backup_filename(name, state['backups'])
    if os.path.basename(filename) != filename or not filename.endswith('_backup.xml'):
        raise ValueError('Invalid flavor backup filename.')
    atomic_save(os.path.join(profile, 'flavor-backups', filename), xml)
    state['backups'][key] = {'name': name, 'file': filename,
                             'saved_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                             'installed': state.get('installed', {})}
    save_flavor_state(profile, state)
    trace('Updated backup for flavor: ' + name)


def backup_date(saved_at):
    try:
        date = time.strptime(saved_at[:10], '%Y-%m-%d')
        return '%d/%d/%d' % (date.tm_mon, date.tm_mday, date.tm_year)
    except (ValueError, TypeError):
        return 'Unknown date'


def restore_choices(profile, state):
    choices = []
    for record in sorted(state['backups'].values(), key=lambda item: item['name'].casefold()):
        filename = record['file']
        if os.path.basename(filename) != filename:
            continue
        path = os.path.join(profile, 'flavor-backups', filename)
        if os.path.isfile(path):
            label = '%s - Backed up %s' % (record['name'], backup_date(record['saved_at']))
            choices.append((label, record['name'], path))
    # Preserve the old restore option for installations predating named backups.
    legacy = os.path.join(profile, 'flavor-backup.xml')
    if not choices and os.path.isfile(legacy):
        stamp = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(legacy)))
        choices.append(('Previous setup - Backed up ' + backup_date(stamp), 'Previous setup', legacy))
    return choices


def switch_settings(profile, target, target_name=None, current_name=None):
    """Write only while another skin is active, after Xenon saves on unload."""
    path = os.path.join(profile, 'settings.xml')
    backup = os.path.join(profile, 'flavor-backup.xml')
    payload = settings_bytes(target)
    parse_settings(payload)  # Validate before leaving Xenon.
    if not xbmc.getCondVisibility('System.HasAddon(skin.estuary)'):
        raise RuntimeError('The built-in Estuary skin must be installed.')
    previous = None
    state = read_flavor_state(profile) if target_name else None
    try:
        load_skin('skin.estuary')
        # Loading Estuary flushes Xenon's current settings, including unsaved edits.
        if active_skin_id() != 'skin.estuary':
            raise RuntimeError('Xenon is still active; settings were not replaced.')
        with open(path, 'rb') as stream:
            previous = stream.read()
        parse_settings(previous)
        trace('Saving previous XML backup')
        atomic_save(backup, previous)
        trace('Replacing Xenon settings XML')
        atomic_save(path, payload)
        trace('XML replacement complete')
        load_skin('skin.xenon')
        if state is not None:
            state['current'] = clean_flavor_name(target_name)
            save_flavor_state(profile, state)
    except Exception as error:
        trace('Switch exception: ' + str(error))
        if previous is not None:
            try:
                if active_skin_id() != 'skin.estuary':
                    load_skin('skin.estuary')
                atomic_save(path, previous)
                load_skin('skin.xenon')
            except Exception as restore_error:
                raise RuntimeError('Switch failed: %s. Restore also failed: %s. '
                                   'Your previous settings remain in flavor-backup.xml.'
                                   % (error, restore_error)) from error
        else:
            # Failure before the settings write: return to Xenon if possible.
            try:
                if active_skin_id() != 'skin.xenon':
                    load_skin('skin.xenon')
            except Exception:
                pass
        raise


def backup_current_flavor(profile, name):
    """Copy Kodi's saved settings without unloading or reloading the skin."""
    state = read_flavor_state(profile)
    monitor = xbmc.Monitor()
    # Kodi 21 saves skin edits on a 500 ms timer. The launcher has already
    # exited; allow that delayed write to finish without touching the GUI.
    if monitor.waitForAbort(1.0):
        raise RuntimeError('Kodi is shutting down')
    path = os.path.join(profile, 'settings.xml')
    deadline = time.monotonic() + 5
    while True:
        try:
            with open(path, 'rb') as stream:
                xml = stream.read()
            parse_settings(xml)
            break
        except (OSError, ET.ParseError):
            # Retry if the file is momentarily locked or being written.
            if time.monotonic() >= deadline or monitor.waitForAbort(0.1):
                raise
    save_flavor_backup(profile, state, name, xml)
    state['current'] = clean_flavor_name(name)
    save_flavor_state(profile, state)


def atomic_save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.tmp', 'wb') as stream:
        stream.write(data)
    os.replace(path + '.tmp', path)


def main(open_online=False):
    dialog = xbmcgui.Dialog()
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
    lock = os.path.join(profile, 'flavor-switch.lock')
    if xbmc.getSkinDir() != 'skin.xenon':
        return
    os.makedirs(profile, exist_ok=True)
    if os.path.exists(lock):
        # If Kodi crashed, a new script run can clear the stale lock after 2 minutes.
        if time.time() - os.path.getmtime(lock) < 120:
            dialog.ok(TITLE, 'A flavor switch is already pending. Choose Yes on Kodi skin confirmations.')
            return
        os.unlink(lock)
    with open(lock, 'w') as stream:
        stream.write(str(time.time()))
    scheduled = False
    try:
        profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
        state = read_flavor_state(profile)
        option = 0 if open_online else dialog.select(TITLE, ['Choose Xenon Flavor', 'Backup Current Flavor', 'Restore Flavor Backup'])
        if option < 0:
            return
        if option == 1:
            name = clean_flavor_name(dialog.input('Name this flavor backup', defaultt=state.get('current') or 'Current setup'))
            if not name:
                return
            job = {'mode': 'backup', 'name': name}
        else:
            if option == 0:
                chosen = choose_online()
                if not chosen:
                    return
                name, target, metadata = chosen
            else:
                choices = restore_choices(profile, state)
                if not choices:
                    dialog.ok(TITLE, 'No saved flavor backups yet. Use Backup Current Flavor to save one.')
                    return
                selected = dialog.select('Restore Flavor Backup', [entry[0] for entry in choices])
                if selected < 0:
                    return
                _, name, path = choices[selected]
                metadata = next((record.get('installed', {}) for record in state['backups'].values() if record.get('name') == name), {})
                with open(path, 'rb') as stream:
                    target = preset_settings(stream.read())
            name = clean_flavor_name(name)
            if not name:
                return
            if not dialog.yesno(TITLE, 'Apply %s? Kodi will briefly show Estuary, then return to Xenon. Skin confirmations will be accepted automatically.' % name):
                return
            atomic_save(os.path.join(profile, 'flavor-pending.xml'), settings_bytes(target))
            job = {'mode': 'switch', 'target_name': name, 'metadata': metadata}
        atomic_save(os.path.join(profile, 'flavor-pending.json'), json.dumps(job).encode('utf-8'))
        trace('Job staged; launcher exiting before worker starts')
        del dialog
        xbmc.executebuiltin('AlarmClock(XenonFlavorApply,RunScript(special://home/addons/skin.xenon/resources/scripts/flavors.py,apply),00:00:02,silent)', True)
        scheduled = True
    except Exception as error:
        xbmc.log('Xenon flavor switch: %s' % error, xbmc.LOGERROR)
        xbmcgui.Dialog().ok(TITLE, 'Could not stage this setup.\n' + str(error))
    finally:
        if not scheduled and os.path.exists(lock):
            os.unlink(lock)


def apply_pending():
    # Separate invocation: no Window, Control or Dialog handles across skin reloads.
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
    pending = os.path.join(profile, 'flavor-pending.xml')
    try:
        trace('Worker started')
        if active_skin_id() != 'skin.xenon':
            raise RuntimeError('Start the switch with Xenon active.')
        job_path = os.path.join(profile, 'flavor-pending.json')
        with open(job_path, encoding='utf-8') as stream:
            job = json.load(stream)
        if job.get('mode') == 'backup':
            backup_current_flavor(profile, job['name'])
            trace('Manual flavor backup completed')
            xbmc.executebuiltin('Notification(Xenon Flavors,Flavor backup saved,5000)')
        else:
            with open(pending, 'rb') as stream:
                target = parse_settings(stream.read())
            if job.get('update'):
                backup_current_flavor(profile, read_flavor_state(profile).get('current') or 'Before flavor update')
            switch_settings(profile, target, job['target_name'])
            state = read_flavor_state(profile)
            state['installed'] = job.get('metadata') or {}
            save_flavor_state(profile, state)
            os.unlink(pending)
            trace('Switch completed')
            xbmc.executebuiltin('Notification(Xenon Flavors,Setup applied,5000)')
        os.unlink(job_path)
    except Exception as error:
        trace('Worker failed: ' + str(error))
        xbmc.executebuiltin('Notification(Xenon Flavors,Switch failed - see flavor-switch.log,10000)')
    finally:
        lock = os.path.join(profile, 'flavor-switch.lock')
        if os.path.exists(lock):
            os.unlink(lock)




def version_key(value):
    # Numeric versions only: 1, 2, 1.10, 2.0.1. No alphabetical comparison.
    value = str(value).strip()
    if not re.fullmatch(r'\d+(?:\.\d+)*', value):
        return None
    parts = [int(part) for part in value.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def all_online_flavors(entries, depth=0):
    if depth > 10:
        raise ValueError('Catalog nesting is too deep.')
    result = []
    for name, source, folder, metadata in entries:
        if isinstance(source, list):
            result.extend(all_online_flavors(source, depth + 1))
        elif folder:
            result.extend(all_online_flavors(catalog_entries(fetch(source), source), depth + 1))
        else:
            result.append((name, source, metadata))
    return result


def find_online_flavor(entries, flavor_id, depth=0):
    return [entry for entry in all_online_flavors(entries, depth)
            if entry[2].get('id') == flavor_id]


def wait_for_notice(monitor, lock):
    deadline = time.monotonic() + 120
    while not (xbmc.getSkinDir() == 'skin.xenon' and
               xbmc.getCondVisibility('Window.IsActive(Home)') and
               not xbmc.getCondVisibility('System.HasActiveModalDialog') and
               not xbmc.Player().isPlaying()):
        if time.monotonic() >= deadline or monitor.waitForAbort(1):
            return False
    return not os.path.exists(lock)


def notify_new_flavors(profile, flavors, monitor, lock):
    # Keep a cumulative set: temporarily removing/re-adding an ID is not new.
    by_id = {}
    for name, source, metadata in flavors:
        flavor_id = metadata.get('id')
        if not flavor_id:
            continue
        if flavor_id in by_id:
            raise ValueError('Duplicate flavor ID in catalog: ' + flavor_id)
        by_id[flavor_id] = name
    if not by_id:
        return False  # An empty/malformed catalog must not establish a baseline.
    state = read_flavor_state(profile)
    known = state.get('known_flavor_ids')
    if known is None:
        state['known_flavor_ids'] = sorted(by_id)
        save_flavor_state(profile, state)
        return False
    added = sorted(set(by_id) - set(known))
    if not added or not wait_for_notice(monitor, lock):
        return False
    names = '\n'.join(by_id[flavor_id] for flavor_id in added)
    opened = xbmcgui.Dialog().yesno(
        TITLE, 'A New Xenon Flavor is available:\n' + names,
        nolabel='Dismiss', yeslabel='Open Flavors')
    state = read_flavor_state(profile)
    state['known_flavor_ids'] = sorted(set(state.get('known_flavor_ids', [])) | set(by_id))
    save_flavor_state(profile, state)
    if opened:
        # Start a separate launcher only after this dialog has closed.
        xbmc.executebuiltin('RunScript(special://home/addons/skin.xenon/resources/scripts/flavors.py,browse)')
        return True
    return False


def check_updates():
    """One background check per Kodi session; never infer an installed version."""
    home = xbmcgui.Window(10000)
    if home.getProperty('Xenon.FlavorUpdateChecked'):
        return
    home.setProperty('Xenon.FlavorUpdateChecked', 'true')
    del home  # No native window handle is retained across a skin switch.
    monitor = xbmc.Monitor()
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
    lock = os.path.join(profile, 'flavor-switch.lock')
    try:
        if os.path.exists(lock):
            return
        flavors = all_online_flavors(xenon_catalog_entries(fetch(CATALOG), CATALOG))
        if notify_new_flavors(profile, flavors, monitor, lock):
            return
        state = read_flavor_state(profile)
        installed = state.get('installed') or {}
        flavor_id = installed.get('id')
        current = version_key(installed.get('version', ''))
        if not flavor_id or current is None or state.get('ignored_updates', {}).get(flavor_id):
            return
        if os.path.exists(lock):
            return
        matches = [entry for entry in flavors if entry[2].get('id') == flavor_id]
        if len(matches) != 1:
            return  # A duplicate/missing ID must never select the wrong flavor.
        name, url, metadata = matches[0]
        remote = version_key(metadata.get('version', ''))
        if remote is None or remote <= current:
            return
        if not wait_for_notice(monitor, lock):
            return
        if os.path.exists(lock) or read_flavor_state(profile).get('installed') != installed:
            return
        answer = xbmcgui.Dialog().yesnocustom(
            TITLE, 'An update is available for %s (version %s → %s). '
            'Updating replaces your skin settings. Your current setup will be backed up first.'
            % (name, installed['version'], metadata['version']),
            nolabel='Not Now', yeslabel='Yes', customlabel="Don't Ask Again")
        if answer == 2:
            state = read_flavor_state(profile)
            state.setdefault('ignored_updates', {})[flavor_id] = True
            save_flavor_state(profile, state)
            return
        if answer != 1:
            return
        target = preset_settings(fetch(url))
        if (xbmc.getSkinDir() != 'skin.xenon' or os.path.exists(lock) or
                read_flavor_state(profile).get('installed') != installed):
            return
        # Acquire the same lock as the manual switcher, without overwriting it.
        os.makedirs(profile, exist_ok=True)
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        scheduled = False
        try:
            atomic_save(os.path.join(profile, 'flavor-pending.xml'), settings_bytes(target))
            job = {'mode': 'switch', 'target_name': clean_flavor_name(name),
                   'metadata': metadata, 'update': True}
            atomic_save(os.path.join(profile, 'flavor-pending.json'), json.dumps(job).encode('utf-8'))
            xbmc.executebuiltin('AlarmClock(XenonFlavorApply,RunScript(special://home/addons/skin.xenon/resources/scripts/flavors.py,apply),00:00:02,silent)', True)
            scheduled = True
        finally:
            if not scheduled and os.path.exists(lock):
                os.unlink(lock)
    except Exception as error:
        xbmc.log('Xenon flavor update check: ' + str(error), xbmc.LOGWARNING)


def reset_update_prompts():
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
    if os.path.exists(os.path.join(profile, 'flavor-switch.lock')):
        return
    state = read_flavor_state(profile)
    state['ignored_updates'] = {}
    save_flavor_state(profile, state)
    xbmcgui.Dialog().ok(TITLE, 'Flavor update prompts have been enabled again.')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'apply':
        apply_pending()
    elif len(sys.argv) > 1 and sys.argv[1] == 'browse':
        main(open_online=True)
    elif len(sys.argv) > 1 and sys.argv[1] == 'checkupdates':
        check_updates()
    elif len(sys.argv) > 1 and sys.argv[1] == 'resetupdates':
        reset_update_prompts()
    else:
        main()
