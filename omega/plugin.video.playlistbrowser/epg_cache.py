"""URL-keyed XMLTV cache shared by Kodi plugin and service invocations."""
import gzip
import hashlib
import io
import os
import tempfile
import time
import zlib
import xml.etree.ElementTree as ET
from contextlib import contextmanager


def cache_paths(profile, epg):
    # Preserve case, query strings and Kodi URL headers: different locators may
    # identify different guides/accounts. Only surrounding whitespace is ignored.
    key = hashlib.sha256(epg.strip().encode('utf-8')).hexdigest()
    xml = os.path.join(profile, 'epg_shared_' + key + '.xml')
    return xml, xml + '.gz'


def legacy_paths(profile, indices):
    for idx in sorted(set(int(i) for i in indices)):
        xml = os.path.join(profile, 'epg_%d.xml' % idx)
        yield xml
        yield xml + '.gz'


@contextmanager
def cache_lock(xml):
    # A filesystem lock also serializes separate Kodi Python interpreters.
    lock = xml + '.lock'
    deadline = time.monotonic() + 180
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                # Recover a lock left by a killed process. Normal fetches use
                # a 90-second socket timeout; allow ample time for slow feeds.
                if time.time() - os.path.getmtime(lock) > 900:
                    os.remove(lock)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError('Timed out waiting for the shared EPG cache')
            time.sleep(0.1)
            continue
        try:
            os.write(fd, str(os.getpid()).encode('ascii'))
            os.close(fd)
            yield
        finally:
            try:
                os.remove(lock)
            except FileNotFoundError:
                pass
        break


def xmltv_bytes(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    # Validate the complete document without retaining its programme tree.
    first = True
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        if first:
            if element.tag.rsplit('}', 1)[-1].lower() != 'tv':
                raise ValueError('EPG response is not XMLTV')
            first = False
        if event == 'end':
            element.clear()
    if first:
        raise ValueError('Empty EPG response')
    return data


def atomic_write(path, data, mtime=None):
    fd, temporary = tempfile.mkstemp(prefix='.epg-', suffix='.tmp', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        if mtime is not None:
            os.utime(temporary, (mtime, mtime))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _remove(paths, log):
    for path in paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            log('Could not remove old EPG cache: %s' % type(exc).__name__)


def read_epg(profile, epg, indices, download, ttl_hours=24, force=False, log=lambda message: None):
    """Return (XML bytes, downloaded); retain a working cache on fetch failure."""
    xml, unused_gz = cache_paths(profile, epg)
    os.makedirs(profile, exist_ok=True)
    old_paths = list(legacy_paths(profile, indices))
    with cache_lock(xml):
        cached = None
        if os.path.isfile(xml):
            with open(xml, 'rb') as stream:
                cached = stream.read()
        else:
            # Promote the newest *valid* old source cache. Preserve its age so
            # migration cannot turn expired guide data into a fresh cache.
            candidates = [path for path in old_paths if os.path.isfile(path)]
            def modified(path):
                try:
                    return os.path.getmtime(path)
                except OSError:
                    return 0
            for path in sorted(candidates, key=modified, reverse=True):
                try:
                    stamp = os.path.getmtime(path)
                    with open(path, 'rb') as stream:
                        cached = xmltv_bytes(stream.read())
                    atomic_write(xml, cached, stamp)
                    log('Migrated source EPG data to shared cache')
                    break
                except (OSError, ValueError, EOFError, zlib.error, ET.ParseError):
                    cached = None
        due = force or cached is None or time.time() - os.path.getmtime(xml) > max(1, ttl_hours) * 3600
        downloaded = False
        if due:
            try:
                data = xmltv_bytes(download())
                atomic_write(xml, data)
                cached = data
                downloaded = True
                log('Shared EPG cache updated')
            except Exception as exc:
                log('EPG update failed; retaining any previous cache: %s' % type(exc).__name__)
                if cached is None:
                    raise
        # Remove duplicates only after a usable shared copy exists. The shared
        # cache stores XML only, not a second compressed copy of the same guide.
        if cached is not None:
            _remove(old_paths + [unused_gz], log)
        return cached, downloaded


def clear_epg(profile, epg, indices, log=lambda message: None):
    xml, gz = cache_paths(profile, epg)
    os.makedirs(profile, exist_ok=True)
    with cache_lock(xml):
        _remove([xml, gz] + list(legacy_paths(profile, indices)), log)
