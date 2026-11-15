"""
Gears keeps its settings in databases/settings.db, like Red Light (both are Fen Light
forks; see redlight_db.py). This is the same push for Gears, used by the Simkl sync (1.3.9):
only existing rows are updated, an empty value is skipped, and a wipe (control.wiping())
puts every row back to Gears' own default for it.

Gears reads a row again at its next start, the same as the debrid and Trakt rows the older
code writes.
"""
import sqlite3

import xbmc
import xbmcvfs
from libs.common import var
from reauthorize.modules import control


def available():
    return xbmcvfs.exists(var.chk_gears_video) and xbmcvfs.exists(var.chkset_gears)


def push(values, require_first=True):
    """Write (setting_id, value) pairs. Returns the number of rows that changed."""
    if not available():
        return 0
    wiping = control.wiping()
    if not wiping and require_first and not values[0][1]:
        return 0
    changed = 0
    conn = sqlite3.connect(var.gears_settings_db, timeout=10)
    try:
        with conn:
            for setting_id, value in values:
                if wiping:
                    cur = conn.execute('UPDATE settings SET setting_value = setting_default '
                                       'WHERE setting_id = ? AND setting_value IS NOT setting_default', (setting_id,))
                elif value:
                    cur = conn.execute('UPDATE settings SET setting_value = ? '
                                       'WHERE setting_id = ? AND setting_value IS NOT ?', (value, setting_id, value))
                else:
                    continue
                changed += cur.rowcount
    except Exception as e:
        xbmc.log('%s: Gears settings.db write failed: %s' % (var.amgr, e), xbmc.LOGINFO)
        raise
    finally:
        conn.close()
    return changed
