"""Online flavor updates for Xenon Setup."""
import datetime
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

# Paste the public HTTPS URL of flavors.json between these quotes.
MANIFEST_URL = 'https://raw.githubusercontent.com/Buildtexts69/omegabuilds/main/Xenon_Flavors/flavors.json'

DAY = 86400
MAX_ARCHIVE = 8 * 1024 * 1024
PREFIX = 'script.skinshortcuts/'
ACTIVE = 'Xenon2.Setup.Flavor'
TITLE = 'Xenon Flavor Update'


def _https(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None:
        raise ValueError('Expected a public HTTPS URL')
    return url


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _https(newurl))


def _download(url, limit):
    opener = urllib.request.build_opener(HTTPSRedirect())
    with opener.open(_https(url), timeout=5) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Download exceeds size limit')
    return data


def load_flavors():
    if not MANIFEST_URL:
        raise ValueError('Set MANIFEST_URL in xenon_flavor_updates.py to the HTTPS address of flavors.json.')
    manifest = json.loads(_download(MANIFEST_URL, 64 * 1024))
    if manifest['schema'] != 1 or not isinstance(manifest.get('flavors'), dict):
        raise ValueError('Unsupported flavor manifest')
    flavors = {}
    for flavor_id, release in manifest['flavors'].items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', flavor_id) or not isinstance(release, dict):
            raise ValueError('Invalid flavor ID or entry: ' + flavor_id)
        name, mode = release.get('name'), release.get('mode')
        labels = release.get('always_labels', [])
        if (not isinstance(name, str) or not name.strip() or mode not in ('free', 'debrid')
                or not isinstance(labels, list)
                or any(not isinstance(label, str) or not label.strip() for label in labels)):
            raise ValueError('Invalid name, mode, or always_labels for flavor: ' + flavor_id)
        flavor = dict(release, id=flavor_id, name=name.strip(), always_labels=labels)
        for key in ('addon', 'icon'):
            if not isinstance(flavor.get(key, ''), str):
                raise ValueError('Invalid %s for flavor: %s' % (key, flavor_id))
        _validate_release(flavor)
        flavors[flavor_id] = flavor
    return flavors


def _validate_release(release):
    version = release['version']
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', version):
        raise ValueError('Use YYYY-MM-DD for flavor versions')
    datetime.date.fromisoformat(version)
    _https(release['url'])
    if not re.fullmatch(r'[a-fA-F0-9]{64}', release['sha256']):
        raise ValueError('Invalid flavor SHA-256')


def _write_extracted_file(path, data):
    """Write through Kodi's VFS, with native I/O as a compatibility fallback."""
    vfs_error = None
    stream = None
    try:
        stream = xbmcvfs.File(path, 'wb')
        if stream is None:
            raise IOError('Kodi VFS could not open the destination')
        result = stream.write(data)
        if result is False:
            raise IOError('Kodi VFS could not write the destination')
    except Exception as exc:
        vfs_error = exc
    finally:
        if stream is not None:
            stream.close()

    if vfs_error is not None:
        try:
            with open(path, 'wb') as stream:
                stream.write(data)
                stream.flush()
        except Exception as native_error:
            raise IOError(
                'Kodi VFS write failed (%s); native write failed (%s)'
                % (vfs_error, native_error)
            )

    if not os.path.isfile(path) or os.path.getsize(path) != len(data):
        raise IOError('Extracted file failed its size check: ' + os.path.basename(path))


def _extract(release, destination):
    data = _download(release['url'], MAX_ARCHIVE)
    if hashlib.sha256(data).hexdigest() != release['sha256'].lower():
        raise ValueError('Flavor checksum mismatch')
    os.makedirs(destination, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(files) > 250 or sum(entry.file_size for entry in files) > MAX_ARCHIVE:
            raise ValueError('Flavor ZIP exceeds extraction limits')
        seen = set()
        for entry in files:
            if not entry.filename.startswith(PREFIX):
                raise ValueError('Unexpected flavor ZIP layout')
            name = entry.filename[len(PREFIX):]
            if not re.fullmatch(
                    r'(?:skin\.xenon2-[a-zA-Z0-9_.-]+\.DATA\.xml|skin\.xenon2\.properties|settings\.xml)',
                    name):
                raise ValueError('Unexpected flavor filename')
            if name.casefold() in seen:
                raise ValueError('Duplicate flavor filename')
            seen.add(name.casefold())

            # Refuse special ZIP records masquerading as ordinary files.
            file_type = (entry.external_attr >> 16) & 0o170000
            if file_type not in (0, 0o100000):
                raise ValueError('Flavor ZIP contains a non-regular file: ' + name)

            output_path = os.path.join(destination, name)
            payload = archive.read(entry)
            try:
                _write_extracted_file(output_path, payload)
            except Exception as exc:
                xbmc.log(
                    'Xenon Flavor Update: could not write %s (%s): %s'
                    % (name, type(exc).__name__, str(exc)),
                    xbmc.LOGERROR
                )
                raise


def download_flavor(flavor, destination):
    """Download the selected release into a private, empty directory."""
    _extract(flavor, destination)
    return flavor['version']


def _skin_string(name):
    return xbmc.getInfoLabel('Skin.String(%s)' % name)


def _save(name, value):
    xbmc.executebuiltin('Skin.SetString(%s,%s)' % (name, value))


def check(setup, manual=False):
    dialog = xbmcgui.Dialog()
    if not MANIFEST_URL:
        if manual:
            dialog.ok(TITLE, 'Set MANIFEST_URL in xenon_flavor_updates.py to enable online updates.')
        return
    monitor = xbmc.Monitor()
    if not manual:
        if monitor.waitForAbort(15) or not xbmc.getCondVisibility(
                'Window.IsActive(home) + !System.HasModalDialog + !Player.HasMedia'):
            return
    flavor_id = _skin_string(ACTIVE)
    if not flavor_id:
        if manual:
            dialog.ok(TITLE, 'Select a flavor in Xenon Setup first.')
        return
    lock = setup.WizardSessionLock(os.path.join(setup.PROFILE, 'wizard-session.lock'))
    if not lock.acquire():
        return
    try:
        _check_active(setup, dialog, monitor, flavor_id, manual)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError,
            zipfile.BadZipFile, setup.ET.ParseError) as exc:
        xbmc.log('Xenon Flavor Update failed (%s).' % type(exc).__name__, xbmc.LOGWARNING)
        if manual:
            dialog.ok(TITLE, 'Could not check for a flavor update. See kodi.log.')
    finally:
        lock.release()


def _check_active(setup, dialog, monitor, flavor_id, manual):
    installed_key = 'Xenon2.Setup.FlavorVersion'
    skip_key = 'Xenon2.Setup.FlavorSkip.' + flavor_id
    later_key = 'Xenon2.Setup.FlavorLater.' + flavor_id
    if not manual and time.time() < int(_skin_string(later_key) or '0'):
        return
    release = load_flavors().get(flavor_id)
    if release is None:
        if manual:
            dialog.ok(TITLE, 'The active flavor is missing from the online manifest.')
        return
    flavor = release
    installed = _skin_string(installed_key)
    if release['version'] <= installed:
        if manual:
            dialog.ok(TITLE, 'No newer online version is listed for %s.' % flavor['name'])
        return
    version = release['version']
    if (not manual and _skin_string(skip_key) == version) or monitor.abortRequested():
        return
    if not manual and not xbmc.getCondVisibility(
            'Window.IsActive(home) + !System.HasModalDialog + !Player.HasMedia'):
        return
    display = datetime.date.fromisoformat(version).strftime('%m/%d/%y')
    message = ('An update to the %s flavor is available (%s).[CR][CR]'
               'You can review your Home menu selections before saving.[CR][CR]'
               'Saving replaces your Home menus, shortcuts and widget assignments, '
               'including customizations to them. A copy of your current shortcuts is saved first.'
               % (flavor['name'], display))
    choice = dialog.yesnocustom(TITLE, message, customlabel="Don't Ask Again",
                               nolabel='Remind Me Later', yeslabel='Update Flavor Now')
    if choice == 2:
        _save(skip_key, version)
        return
    if choice == 0:
        _save(later_key, str(int(time.time()) + DAY))
        return
    if choice != 1:
        return
    try:
        with tempfile.TemporaryDirectory(prefix='flavor-update-', dir=setup.PROFILE) as source:
            progress = xbmcgui.DialogProgressBG()
            progress.create(TITLE, 'Downloading and checking the flavor update')
            try:
                _extract(release, source)
            finally:
                progress.close()
            if monitor.abortRequested() or _skin_string(ACTIVE) != flavor_id:
                return
            selected = setup.choose_update_menus(flavor, source)
            if selected is None or monitor.abortRequested() or _skin_string(ACTIVE) != flavor_id:
                return
            setup.apply_flavor(flavor, selected, source=source, version=version, keep_backup=True)
    except Exception as exc:
        xbmc.log('Xenon Flavor Update apply failed (%s).' % type(exc).__name__, xbmc.LOGWARNING)
        dialog.ok(TITLE, 'The flavor update could not finish. See kodi.log.')
