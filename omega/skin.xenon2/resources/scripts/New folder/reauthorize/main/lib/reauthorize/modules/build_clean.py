# -*- coding: utf-8 -*-
"""
    ReAuthorize - truncate the build's databases for zipping (1.4.3)

    The "Truncate tables too" half of Prepare This Build for Distribution: the same step as The
    Hermit's Wizard's TruncateTables, which until now only its own maker had (the user,
    2026-10-15). Both it and ReAuthorize's own clean-up need Kodi to close straight after and
    stay closed until the build is zipped, so one cannot be run after the other: hence one
    button that clears the sign-ins, truncates the tables, then closes Kodi. Builders were
    deleting files and database rows by hand instead, and one build shipped with ReAuthorize
    opening to an empty settings window.

      - every database in userdata/Database is emptied (watched history, TV guide, music
        library, view settings), table by table, keeping the 'version' table Kodi checks;
      - EXCEPT Kodi's add-on database (Addons*.db: which add-ons are installed and enabled,
        emptying it breaks builds) and the thumbnail index (Textures*.db), as the wizard does.

    Cache, thumbnails and packages are a wizard's job and are left alone. Run it just before
    Kodi quits: Kodi still has these databases open, so a table it has locked at that moment
    is reported and skipped, never forced.
"""

import os
import sqlite3

import xbmc
import xbmcvfs

KEEP_PREFIXES = ('addons', 'textures')     # Addons33.db, Textures13.db and other versions of them
KEEP_TABLES = ('version', 'sqlite_sequence')


def _log(message, level=xbmc.LOGINFO):
    xbmc.log('[ReAuthorize Build Clean] %s' % message, level)


def empty_database(path):
    """Empty every table but 'version'. (tables emptied, error or None)."""
    emptied = 0
    try:
        conn = sqlite3.connect(path, timeout=10)
    except Exception as e:
        return 0, str(e)
    try:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            if table.lower() in KEEP_TABLES:
                continue
            conn.execute('DELETE FROM "%s"' % table.replace('"', '""'))
            emptied += 1
        conn.commit()
        try:
            conn.execute('VACUUM')          # gives the space back; harmless if Kodi holds the file
        except Exception:
            pass
        return emptied, None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return emptied, str(e)
    finally:
        conn.close()


def clean():
    """Truncate every database but the kept ones. A report: {'databases': [...], 'skipped': [...], 'problems': [...]}."""
    report = {'databases': [], 'skipped': [], 'problems': []}
    db_dir = xbmcvfs.translatePath('special://database/')
    names = sorted(os.listdir(db_dir)) if os.path.isdir(db_dir) else []
    for name in names:
        if not name.lower().endswith('.db'):
            continue
        if name.lower().startswith(KEEP_PREFIXES):
            report['skipped'].append(name)
            continue
        emptied, error = empty_database(os.path.join(db_dir, name))
        if error:
            report['problems'].append('%s: %s' % (name, error))
            _log('%s: %s' % (name, error), xbmc.LOGWARNING)
        else:
            report['databases'].append(name)
            _log('%s emptied (%d tables)' % (name, emptied))
    return report


def summary(report):
    """Short lines for the closing dialog."""
    lines = ['Tables truncated: %s' % (', '.join(n[:-3] for n in report['databases']) or 'no databases')]
    if report['problems']:
        lines.append('[COLOR FFFF6666]Not truncated: %s[/COLOR]' % '; '.join(report['problems'][:3]))
    return '[CR]'.join(lines)
