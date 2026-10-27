"""
Red Light keeps its settings in its own databases/settings.db, not in Kodi's
addon settings.xml. Its get_setting() reads a window property, then that
database, and nothing else, so setSetting() on plugin.video.redlight lands in
a file Red Light never opens - which is where ReAuthorize used to send every
Red Light credential except Easynews.

Ids are stored without the 'redlight.' prefix (pm.token, not
redlight.pm.token). Only existing rows are updated: Red Light creates every
row it defines on first run, and a row it does not define would be purged by
its own sync_settings() anyway.

Red Light also caches settings in window properties, which win over the
database. After a write, the reload below re-applies the database to those
properties - the same call Red Light makes internally after a settings sync
(settings_cache.py), and a no-op when the properties are not in use.
"""
import sqlite3

import xbmc
import xbmcvfs
from libs.common import var
from reauthorize.modules import control

_RELOAD = ('RunPlugin(plugin://plugin.video.redlight/?mode=sync_settings'
           '&silent=true&load_properties=false&force=true)')

_batch = False
_pending = False


def available():
    return xbmcvfs.exists(var.chk_redlight) and xbmcvfs.exists(var.redlight_settings_db)


def push(values, require_first=True):
    """
    Write (setting_id, value) pairs into Red Light's settings.db.

    The first pair is the credential itself: with require_first, nothing is
    written unless it has a value, so a service is never switched on without
    its token. Empty values are always skipped rather than blanking whatever
    Red Light already holds. Returns the number of rows that changed.
    """
    if not available():
        return 0
    if control.wiping():
        return _reset(values)
    if require_first and not values[0][1]:
        return 0
    changed = 0
    conn = sqlite3.connect(var.redlight_settings_db, timeout=10)
    try:
        with conn:
            for setting_id, value in values:
                if not value:
                    continue
                cur = conn.execute('UPDATE settings SET setting_value = ? '
                                   'WHERE setting_id = ? AND setting_value IS NOT ?',
                                   (value, setting_id, value))
                changed += cur.rowcount
    except Exception as e:
        xbmc.log('%s: Red Light settings.db write failed: %s' % (var.amgr, e), xbmc.LOGINFO)
        raise
    finally:
        conn.close()
    if changed:
        _request_reload()
    return changed


def _reset(values):
    """
    A wipe (control.wiping()): put every row this service would have written back to
    Red Light's own default for it, instead of skipping blank values the way a normal
    push does. That is what makes a reset reach a token already sitting in Red Light.
    """
    conn = sqlite3.connect(var.redlight_settings_db, timeout=10)
    changed = 0
    try:
        with conn:
            for setting_id, _ in values:
                try:
                    cur = conn.execute('UPDATE settings SET setting_value = setting_default '
                                       'WHERE setting_id = ? AND setting_value IS NOT setting_default',
                                       (setting_id,))
                except sqlite3.OperationalError:          # a database with no default column
                    cur = conn.execute("UPDATE settings SET setting_value = 'empty_setting' "
                                       "WHERE setting_id = ? AND setting_value IS NOT 'empty_setting'",
                                       (setting_id,))
                changed += cur.rowcount
    except Exception as e:
        xbmc.log('%s: Red Light settings.db wipe failed: %s' % (var.amgr, e), xbmc.LOGINFO)
        raise
    finally:
        conn.close()
    if changed:
        _request_reload()
    return changed


def begin_batch():
    """Hold the reload until end_batch(), so a full sync reloads Red Light once."""
    global _batch, _pending
    _batch, _pending = True, False


def end_batch():
    global _batch, _pending
    if _pending:
        xbmc.executebuiltin(_RELOAD)
    _batch, _pending = False, False


def _request_reload():
    global _pending
    if _batch:
        _pending = True
    else:
        xbmc.executebuiltin(_RELOAD)
