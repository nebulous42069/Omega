import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from libs.common import var
from sqlite3 import Error


def create_conn(db_file):
    try:
        return sqlite3.connect(db_file)
    except Error as e:
        xbmc.log('%s: DB connect failed: %s' % (var.amgr, e), xbmc.LOGINFO)
        return None


def _restore_keys(src_db, dst_db, keys, label=''):
    """Copy a list of setting keys from src_db into dst_db."""
    try:
        src = create_conn(src_db)
        dst = create_conn(dst_db)
        sc, dc = src.cursor(), dst.cursor()
        for key in keys:
            sc.execute('SELECT setting_value FROM settings WHERE setting_id = ?', (key,))
            row = sc.fetchone()
            if row:
                dc.execute('UPDATE settings SET setting_value = ? WHERE setting_id = ?', (row[0], key))
        dst.commit()
        sc.close()
        dc.close()
    except Exception as e:
        xbmc.log('%s: %s restore failed: %s' % (var.amgr, label, e), xbmc.LOGINFO)


def _revoke_keys(db, pairs, label=''):
    """Write (value, key) pairs into db - used for revoke/reset."""
    try:
        conn = create_conn(db)
        with conn:
            for value, key in pairs:
                conn.execute('UPDATE settings SET setting_value = ? WHERE setting_id = ?', (value, key))
    except Exception as e:
        xbmc.log('%s: %s revoke failed: %s' % (var.amgr, label, e), xbmc.LOGINFO)


def _backup_db(src, backup_dir, dst, label=''):
    if os.path.exists(src) and os.path.exists(backup_dir):
        try:
            xbmcvfs.copy(src, dst)
        except Exception as e:
            xbmc.log('%s: %s backup failed: %s' % (var.amgr, label, e), xbmc.LOGINFO)


# ─── Credential key groups ────────────────────────────────────────────────────

_EMPTY = 'empty_setting'

_RD_KEYS   = ('rd.enabled', 'rd.token', 'rd.account_id', 'rd.client_id', 'rd.refresh', 'rd.secret')
_PM_KEYS   = ('pm.enabled', 'pm.token', 'pm.account_id')
_AD_KEYS   = ('ad.enabled', 'ad.token', 'ad.account_id')
_EASY_KEYS = ('provider.easynews', 'easynews_user', 'easynews_password')

_AFFEN_TRAKT_KEYS = ('trakt.token', 'trakt.user', 'trakt.refresh', 'trakt.expires',
                     'watched_indicators', 'watched_indicators_name')


# ─── afFENity RD ──────────────────────────────────────────────────────────────

def restore_affen_rd():
    _restore_keys(var.rd_backup_affen, var.affen_settings_db, _RD_KEYS, 'afFENity RD')

def revoke_affen_rd():
    _revoke_keys(var.affen_settings_db, [(_EMPTY, k) for k in _RD_KEYS], 'afFENity RD')

def backup_affen_rd():
    _backup_db(var.affen_settings_db, var.rd_backup, var.rd_backup_affen, 'afFENity RD')


# ─── afFENity PM ──────────────────────────────────────────────────────────────

def restore_affen_pm():
    _restore_keys(var.pm_backup_affen, var.affen_settings_db, _PM_KEYS, 'afFENity PM')

def revoke_affen_pm():
    _revoke_keys(var.affen_settings_db, [(_EMPTY, k) for k in _PM_KEYS], 'afFENity PM')

def backup_affen_pm():
    _backup_db(var.affen_settings_db, var.pm_backup, var.pm_backup_affen, 'afFENity PM')


# ─── afFENity AD ──────────────────────────────────────────────────────────────

def restore_affen_ad():
    _restore_keys(var.ad_backup_affen, var.affen_settings_db, _AD_KEYS, 'afFENity AD')

def revoke_affen_ad():
    _revoke_keys(var.affen_settings_db, [(_EMPTY, k) for k in _AD_KEYS], 'afFENity AD')

def backup_affen_ad():
    _backup_db(var.affen_settings_db, var.ad_backup, var.ad_backup_affen, 'afFENity AD')


# ─── afFENity Trakt ───────────────────────────────────────────────────────────

def restore_affen_trakt():
    _restore_keys(var.trakt_backup_affen, var.affen_settings_db, _AFFEN_TRAKT_KEYS, 'afFENity Trakt')

def revoke_affen_trakt():
    _revoke_keys(var.affen_settings_db, [
        (_EMPTY,     'trakt.token'),
        (_EMPTY,     'trakt.user'),
        (_EMPTY,     'trakt.refresh'),
        (_EMPTY,     'trakt.expires'),
        (0,          'watched_indicators'),
        ('afFENity', 'watched_indicators_name'),
    ], 'afFENity Trakt')

def backup_affen_trakt():
    _backup_db(var.affen_settings_db, var.trakt_backup, var.trakt_backup_affen, 'afFENity Trakt')


# ─── afFENity Easynews ────────────────────────────────────────────────────────

def restore_affen_easy():
    _restore_keys(var.easy_backup_affen, var.affen_settings_db, _EASY_KEYS, 'afFENity Easynews')

def revoke_affen_easy():
    _revoke_keys(var.affen_settings_db, [
        (_EMPTY, 'provider.easynews'),
        (_EMPTY, 'easynews_user'),
        (_EMPTY, 'easynews_password'),
    ], 'afFENity Easynews')

def backup_affen_easy():
    _backup_db(var.affen_settings_db, var.easy_backup, var.easy_backup_affen, 'afFENity Easynews')


# ─── afFENity Metadata ────────────────────────────────────────────────────────

def restore_affen_meta():
    _restore_keys(var.meta_backup_affen, var.affen_settings_db, ('omdb_api',), 'afFENity Metadata')

def revoke_affen_meta():
    _revoke_keys(var.affen_settings_db, [(_EMPTY, 'omdb_api')], 'afFENity Metadata')

def backup_affen_meta():
    _backup_db(var.affen_settings_db, var.meta_backup, var.meta_backup_affen, 'afFENity Metadata')
