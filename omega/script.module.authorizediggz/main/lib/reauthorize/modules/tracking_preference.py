"""Apply an explicit tracking preference to verified add-on settings."""
import json
import os
import re
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from reauthorize.modules import control, importer, sync_support, tmdbh_compat

PREFERENCE = 'tracking.preferred'
PROVIDERS = ('trakt', 'mdblist', 'simkl', 'punchplay')
LABELS = ('Trakt', 'MDBList', 'Simkl', 'PunchPlay')
TMDB_HELPER = 'plugin.video.themoviedb.helper'
POV = 'plugin.video.pov'
FEATURES = ('watched', 'watchlist', 'collection', 'scrobbling')


def _enabled(addon_id):
    return xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % addon_id)


def _helper_fields(addon, provider):
    if provider not in ('trakt', 'mdblist'):
        return (), 'selected provider is unavailable'
    provider_id = tmdbh_compat.TRAKT if provider == 'trakt' else tmdbh_compat.MDBLIST
    if not _enabled(provider_id):
        return (), 'enable the %s provider module' % LABELS[PROVIDERS.index(provider)]
    receiver = xbmcaddon.Addon(provider_id)
    if provider == 'trakt':
        try:
            token = json.loads(receiver.getSetting('token') or '{}')
            ready = isinstance(token, dict) and bool(token.get('access_token'))
        except ValueError:
            ready = False
    else:
        ready = bool(receiver.getSetting('apikey').strip())
    if not ready:
        return (), 'sync the selected service to its provider module first'
    schema = sync_support.declared_settings(addon) or {}
    fields = tuple(('sync_provider_' + feature, provider) for feature in FEATURES
                   if schema.get('sync_provider_' + feature) == 'string')
    return fields, 'no supported provider settings in this version'


def _pov_fields(addon, provider):
    if provider not in ('trakt', 'mdblist'):
        return (), 'selected provider is unavailable'
    path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')), 'resources', 'settings.xml')
    node = ET.parse(path).find(".//setting[@id='watched_indicators']")
    if node is None or node.get('type') != 'enum' or node.get('values') != 'POV|Trakt|MDBList':
        return (), 'no supported watched-status setting in this version'
    keys = ('trakt.token', 'trakt_user') if provider == 'trakt' else ('mdblist.token', 'mdblist_user')
    if not all(addon.getSetting(key).strip() for key in keys):
        return (), 'sync the selected service to POV first'
    return (('watched_indicators', str(PROVIDERS.index(provider) + 1)),), ''


def _gratis_fields(addon, provider):
    if provider == 'punchplay':
        return (), 'selected provider is unavailable'
    schema = sync_support.declared_settings(addon) or {}
    fields = ('indicators.alt', 'bookmarks.source', 'indicators.alt.name')
    if not all(schema.get(key) == 'text' for key in fields):
        return (), 'no supported watched-status settings in this version'
    keys, value = {
        'trakt': (('trakt.token', 'trakt.refresh', 'trakt.user'), '1'),
        'simkl': (('simkl.token', 'simkl.user'), '2'),
        'mdblist': (('mdblist.token', 'mdblist.refresh', 'mdblist.user'), '3'),
    }[provider]
    if not all(addon.getSetting(key).strip() for key in keys):
        return (), 'authorize the selected service in Gratis Red first'
    return tuple(zip(fields, (value, value, LABELS[PROVIDERS.index(provider)]))), ''


def _genocide_fields(addon, provider):
    if provider != 'trakt':
        return (), 'only the Trakt selector is verified'
    path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')), 'resources', 'settings.xml')
    node = ET.parse(path).find(".//setting[@id='indicators.alt']")
    if node is None or node.get('type') != 'enum' or node.get('lvalues') != '32314|32315':
        return (), 'no supported watched-status setting in this version'
    if not all(addon.getSetting(key).strip() for key in ('trakt.token', 'trakt.refresh', 'trakt.username')):
        return (), 'sync Trakt to Genocide first'
    return (('indicators.alt', '1'),), ''


def _settings_xml(addon):
    path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')), 'resources', 'settings.xml')
    return ET.parse(path)


def _has_fields(addon, keys):
    return all(importer._is_value(addon.getSetting(key)) for key in keys)


def _crew_fields(addon, provider):
    if provider not in ('trakt', 'simkl'):
        return (), 'supports Trakt and Simkl'
    schema = _settings_xml(addon)
    selector = schema.find(".//setting[@id='tracker.service']")
    if selector is None or selector.get('type') != 'enum' or selector.get('lvalues') != '90294|90295':
        return (), 'no verified tracker selector in this version'
    if provider == 'simkl':
        if not _has_fields(addon, ('simkl.token',)):
            return (), 'sync Simkl to The Crew first'
        return (('tracker.service', '1'),), ''
    if not _has_fields(addon, ('trakt.user', 'trakt.token', 'trakt.refresh')) or addon.getSetting('trakt.revoked') == 'true':
        return (), 'sync Trakt to The Crew first'
    fields = [('tracker.service', '0')]
    indicator = schema.find(".//setting[@id='indicators.alt']")
    if indicator is not None and indicator.get('lvalues') == '32314|32315':
        fields.append(('indicators.alt', '1'))
    return fields, ''


def _movies_fields(addon, provider):
    node = _settings_xml(addon).find(".//setting[@id='watched_status_provider']")
    if node is None or node.get('type') != 'enum':
        return (), 'no verified watched-status selector in this version'
    options = re.sub(r'\[[^\]]*\]', '', node.get('values', '')).split('|')
    if options != ['Kodi (Local) (no account needed)', 'Trakt', 'MDBList', 'Simkl', 'PunchPlay']:
        return (), 'unrecognized watched-status choices'
    token_keys = {
        'trakt': ('trakt_access_token',),
        'mdblist': ('mdblist_access_token', 'mdblist_api'),
        'simkl': ('simkl_access_token',),
        'punchplay': ('punchplay_access_token',),
    }[provider]
    if not any(importer._is_value(addon.getSetting(key)) for key in token_keys):
        return (), 'sync the selected service to TMDb Movies first'
    return (('watched_status_provider', str(PROVIDERS.index(provider) + 1)),), ''


def _umbrella_fields(addon, provider):
    schema = _settings_xml(addon)
    value, label_id, keys = {
        'trakt': ('1', '32315', ('trakt.user.name', 'trakt.user.token', 'trakt.refreshtoken')),
        'simkl': ('2', '40342', ('simkltoken',)),
        'mdblist': ('3', '40621', ('mdblist.token',)),
        'punchplay': ('7', '40800', ('punchplay.accesstoken',)),
    }[provider]
    fields = []
    label = LABELS[PROVIDERS.index(provider)]
    for key, display in (('indicators.alt', 'indicators'), ('scrobble.source', 'scrobble')):
        node = schema.find(".//setting[@id='%s']" % key)
        if node is not None and node.get('type') == 'integer' and any(
            option.get('label') == label_id and option.text == value
            for option in node.findall('./constraints/options/option')
        ):
            fields.extend(((key, value), (display, label)))
    if not fields:
        return (), 'no verified provider selectors in this version'
    if not _has_fields(addon, keys):
        return (), 'sync the selected service to Umbrella first'
    if provider == 'punchplay':
        from reauthorize.modules.sync import punchplay_sync
        state = punchplay_sync._umbrella_state()
        if (addon.getSetting('punchplay.isauthed') != 'true'
                or state.get('access_token') != addon.getSetting('punchplay.accesstoken')
                or state.get('reauth_required')):
            return (), 'sync PunchPlay to Umbrella first'
    return fields, ''


def _apply_redlight(provider):
    from reauthorize.modules.db import redlight_db
    from reauthorize.modules.sync.mdblist_oauth_sync import _redlight_rows

    value, keys = {
        'trakt': ('1', ('trakt.user', 'trakt.token')),
        'simkl': ('2', ('simkl.user', 'simkl.token')),
        'mdblist': ('3', ('mdblist.user', 'mdblist.token', 'mdblist.refresh')),
        'punchplay': ('4', ('punchplay.token',)),
    }[provider]
    field = 'watched_indicators'
    rows = _redlight_rows(field, *keys)
    if field not in rows:
        return 'open Red Light once to initialize its settings'
    if not all(importer._is_value(rows.get(key)) for key in keys):
        return 'sync the selected service to Red Light first'
    label = LABELS[PROVIDERS.index(provider)]
    changed = redlight_db.push([(field, value), (field + '_name', label)], reload_settings=False)
    if str(_redlight_rows(field).get(field)) != value:
        raise RuntimeError('Provider setting did not save')
    # The settings panel reads a Home window property. Republish it even if
    # the database already had the requested provider from an earlier apply.
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.redlight/?mode=sync_settings'
                        '&silent=true&load_properties=true&force=true)')
    return 'updated' if changed else 'refreshed'


def apply(provider):
    results = []
    for addon_id, name, fields_for in (
        (TMDB_HELPER, 'TMDb Helper', _helper_fields), (POV, 'POV', _pov_fields),
        ('plugin.video.gratisred', 'Gratis Red', _gratis_fields),
        ('plugin.video.genocide', 'Genocide', _genocide_fields),
        ('plugin.video.thecrew', 'The Crew', _crew_fields),
        ('plugin.video.tmdbmovies', 'TMDb Movies', _movies_fields),
        ('plugin.video.umbrella', 'Umbrella', _umbrella_fields),
        ('plugin.video.redlight', 'Red Light', None),
    ):
        if not _enabled(addon_id):
            continue
        try:
            if fields_for is None:
                results.append('%s · %s' % (name, _apply_redlight(provider)))
                continue
            addon = xbmcaddon.Addon(addon_id)
            fields, reason = fields_for(addon, provider)
            if not fields:
                results.append('%s · %s' % (name, reason))
                continue
            changed = []
            for key, value in fields:
                current = addon.getSetting(key)
                if current in (value, 'never'):
                    continue
                addon.setSetting(key, value)
                if xbmcaddon.Addon(addon_id).getSetting(key) != value:
                    raise RuntimeError('Provider setting did not save')
                changed.append(key)
            if addon_id == TMDB_HELPER:
                for key in changed:
                    feature = key[len('sync_provider_'):]
                    if feature != 'scrobbling':
                        xbmc.executebuiltin('RunScript(%s,invalidate_sync=%s)' % (TMDB_HELPER, feature))
            if addon_id == 'plugin.video.tmdbmovies' and changed:
                xbmc.executebuiltin('RunPlugin(plugin://plugin.video.tmdbmovies/?mode=clear_provider_cache)')
            results.append('%s · %s' % (name, 'updated' if changed else 'already set or disabled'))
        except Exception as exc:
            xbmc.log('[Diggz Account Manager] Tracking preference failed for %s (%s).' %
                     (addon_id, type(exc).__name__), xbmc.LOGWARNING)
            results.append('%s · could not verify all settings. See kodi.log.' % name)
    return results


def authorized_providers():
    keys = {
        'trakt': ('trakt.token',),
        'mdblist': ('mdblist.oauth.token', 'mdb.api.key'),
        'simkl': ('simkl.token',),
        'punchplay': ('punchplay.token',),
    }
    return [provider for provider in PROVIDERS
            if any(importer._is_value(control.setting(key)) for key in keys[provider])]


def apply_from_wizard():
    providers = authorized_providers()
    if not providers:
        return
    provider = providers[0]
    if len(providers) > 1:
        current = control.setting(PREFERENCE)
        labels = [LABELS[PROVIDERS.index(value)] for value in providers]
        pick = xbmcgui.Dialog().select(
            'Choose a tracking provider for your add-ons', labels,
            preselect=providers.index(current) if current in providers else -1)
        if pick < 0:
            return
        provider = providers[pick]
    control.setSetting(PREFERENCE, provider)
    for result in apply(provider):
        xbmc.log('[Diggz Account Manager] Xenon setup tracking preference: ' + result, xbmc.LOGINFO)


def choose_and_apply():
    dialog = xbmcgui.Dialog()
    current = control.setting(PREFERENCE)
    index = dialog.select('Preferred tracking service', list(LABELS),
                          preselect=PROVIDERS.index(current) if current in PROVIDERS else -1)
    if index < 0:
        return
    provider = PROVIDERS[index]
    if provider not in authorized_providers():
        dialog.ok('Preferred tracking service', 'Authorize %s in Diggz Account Manager first.' % LABELS[index])
        return
    if not dialog.yesno('Preferred tracking service',
                        'Use %s for supported tracking features in compatible add-ons?' % LABELS[index],
                        nolabel='Cancel', yeslabel='Apply'):
        return
    control.setSetting(PREFERENCE, provider)
    results = apply(provider)
    dialog.ok('Preferred tracking service', '[CR]'.join(results) if results else
              'Preference saved. Enable a compatible add-on and apply it again.')
