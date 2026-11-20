# -*- coding: utf-8 -*-
"""
Find sign-ins the user already made inside their addons, and offer to adopt them.

Diggz Account Manager has always been push-only: it sends credentials out and never looks
at what is already there. So someone who signed into OffCloud inside Umbrella
and then opened Diggz Account Manager saw a blank tab and a red dashboard, and concluded
it did not work. This is the other direction.

Rules, earned from the two partial importers that came before this one
(settings_display's YouTube import, lastfm_sync reading the scrobbler):
  - scan unconditionally, not behind an unrelated toggle
  - never adopt silently: show what was found and ask
  - protect existing manager sign-ins and ask when add-ons offer multiple logins
  - when asked explicitly, say what was checked even if nothing was found

WHERE to look comes from import_map, generated from the sync code's own
writes. WHAT counts as a complete credential, and which services can be
adopted at all, is policy and lives here.
"""
import hashlib
import pathlib
import re
import sqlite3

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from reauthorize.modules import control
from reauthorize.modules import import_map

LOG_TAG = '[Diggz Account Manager Import]'
DECLINED_SETTING = 'import.declined'

# (service, label, required keys, optional keys).
# Every required key must be found in the SAME addon. Half a Real-Debrid login -
# a token without its refresh token, client id and secret - works until it
# expires and then cannot be renewed, which is worse than not adopting it.
ADOPTABLE = (
    ('realdebrid', 'Real-Debrid',
     ('realdebrid.token', 'realdebrid.refresh', 'realdebrid.client_id', 'realdebrid.secret'),
     ('realdebrid.username',)),
    ('premiumize', 'Premiumize', ('premiumize.token',), ('premiumize.username',)),
    ('alldebrid', 'AllDebrid', ('alldebrid.token',), ('alldebrid.username',)),
    ('torbox', 'TorBox', ('torbox.token',), ()),
    ('easydebrid', 'Easy Debrid', ('easydebrid.token',), ()),
    ('offcloud', 'OffCloud', ('offcloud.token',), ()),
    ('easynews', 'Easynews', ('easynews.username', 'easynews.password'), ()),
    ('linksnappy', 'Linksnappy', ('linksnappy.username', 'linksnappy.password'), ()),
    ('filepursuit', 'FilePursuit', ('filepursuit.api.key',), ()),
    ('torrentclaw', 'TorrentClaw API key', ('torrentclaw.api.key',), ()),
    ('tmdb', 'TMDb API key', ('tmdb.api.key',), ()),
    ('fanart', 'Fanart.tv API key', ('fanart.tv.api.key',), ()),
    ('omdb', 'OMDb API key', ('omdb.api.key',), ()),
    ('tvdb', 'TVDb API key', ('tvdb.api.key',), ()),
    ('mdblist', 'MDBList API key', ('mdb.api.key',), ()),
    ('youtube', 'YouTube API keys',
     ('youtube.api.key', 'youtube.api.id', 'youtube.api.secret'), ()),
)

# A login made inside an addon belongs to that addon's own registered app: the
# token is only valid alongside that app's client id, so ReAuthorize can neither
# share it nor refresh it. Report these; never adopt them.
REPORT_ONLY = (
    ('trakt', 'Trakt', 'trakt.token'),
    ('simkl', 'Simkl', 'simkl.token'),
)

_PLACEHOLDERS = ('', 'none', 'null', 'empty_setting', '0', '-1', 'true', 'false')

# Optional keys are display names. Only take them from a setting whose name
# says it holds one, rather than treating unrelated identifier fields as usernames.
_NAME_LIKE = re.compile(r'user|account|login|name', re.I)

_SETTING_BLOCK = re.compile(r'<setting\b([^>]*?)(?:/>|>(.*?)</setting>)', re.S)
_ID_ATTR = re.compile(r'\bid="([^"]+)"')
_DEFAULT_ATTR = re.compile(r'\bdefault="([^"]*)"')
_DEFAULT_ELEM = re.compile(r'<default>(.*?)</default>', re.S)
_COLOR_TAGS = re.compile(r'\[/?(?:COLOR|B|I|UPPERCASE|LOWERCASE)[^\]]*\]', re.I)


class Option(object):
    """One distinct login for a service, and every addon it was found in."""
    __slots__ = ('values', 'addons')

    def __init__(self, values, addon_id):
        self.values = dict(values)
        self.addons = [addon_id]


class Finding(object):
    """
    status:
      'new'      - Diggz Account Manager has nothing for this service; one login found
      'conflict' - Diggz Account Manager has nothing; different logins in different addons
      'report'   - found, but it cannot be adopted (see REPORT_ONLY)
    """
    __slots__ = ('service', 'label', 'status', 'options', 'required', 'optional')

    def __init__(self, service, label, status, options, required=(), optional=()):
        self.service, self.label, self.status = service, label, status
        self.options, self.required, self.optional = options, required, optional


# --- reading --------------------------------------------------------------

def _log(msg):
    xbmc.log('%s %s' % (LOG_TAG, msg), xbmc.LOGINFO)


def _is_value(value):
    return value is not None and str(value).strip().lower() not in _PLACEHOLDERS


def _installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def _unescape(text):
    return (text.replace('&lt;', '<').replace('&gt;', '>')
                .replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&'))


def _shipped_defaults(addon_id):
    """
    {setting_id: default} from the addon's own resources/settings.xml, in either
    the old format (default="...") or the new one (<default>...</default>).

    An unchanged setting reads back as its default, and several addons ship
    their own TMDb or Fanart key that way. That is the addon's key, not the
    user's, and must never be offered as a sign-in.
    """
    path = xbmcvfs.translatePath('special://home/addons/%s/resources/settings.xml' % addon_id)
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
    except Exception:
        return {}
    defaults = {}
    for match in _SETTING_BLOCK.finditer(text):
        attrs, body = match.group(1), match.group(2) or ''
        setting_id = _ID_ATTR.search(attrs)
        if not setting_id:
            continue
        element = _DEFAULT_ELEM.search(body)
        attribute = _DEFAULT_ATTR.search(attrs)
        if element:
            defaults[setting_id.group(1)] = _unescape(element.group(1).strip())
        elif attribute:
            defaults[setting_id.group(1)] = _unescape(attribute.group(1).strip())
    return defaults


def _read_settings(addon_id, setting_ids):
    try:
        addon = xbmcaddon.Addon(addon_id)
    except Exception:
        return {}              # disabled or broken: nothing we can read
    defaults = _shipped_defaults(addon_id)
    found = {}
    for setting_id in setting_ids:
        try:
            value = addon.getSetting(setting_id)
        except Exception:
            continue
        if _is_value(value) and value != defaults.get(setting_id):
            found[setting_id] = value
    return found


def _read_database(addon_id, spec):
    """Read-only, and skips any row still holding its own default."""
    path = xbmcvfs.translatePath('special://profile/addon_data/%s/%s' % (addon_id, spec['file']))
    if not xbmcvfs.exists(path):
        return {}
    found = {}
    try:
        conn = sqlite3.connect(pathlib.Path(path).as_uri() + '?mode=ro', uri=True, timeout=5)
    except Exception as e:
        _log('could not open %s: %s' % (path, e))
        return {}
    try:
        columns = [row[1] for row in conn.execute('PRAGMA table_info(settings)')]
        select = 'SELECT setting_value%s FROM settings WHERE setting_id = ?' % (
            ', setting_default' if 'setting_default' in columns else '')
        for setting_id in spec['keys']:
            row = conn.execute(select, (setting_id,)).fetchone()
            if not row:
                continue
            value = '' if row[0] is None else str(row[0])
            default = str(row[1]) if len(row) > 1 and row[1] is not None else None
            if _is_value(value) and value != default:
                found[setting_id] = value
    except Exception as e:
        _log('could not read %s: %s' % (path, e))
    finally:
        conn.close()
    return found


def addon_name(addon_id):
    try:
        name = xbmcaddon.Addon(addon_id).getAddonInfo('name')
        return _COLOR_TAGS.sub('', name).strip() or addon_id
    except Exception:
        return addon_id


def _collect():
    """
    Every installed addon the map knows about, and what each one holds:
    {addon_id: {reauthorize_key: {value: addon_setting_id}}}
    """
    collected = {}
    for addon_id in sorted(set(import_map.SETTINGS) | set(import_map.DATABASES)):
        if not _installed(addon_id):
            continue
        held = {}
        mapping = import_map.SETTINGS.get(addon_id, {})
        if mapping:
            for setting_id, value in _read_settings(addon_id, list(mapping)).items():
                if addon_id == 'script.diggzportal' and setting_id == 'tmdb_session' and xbmcaddon.Addon(addon_id).getSetting('tmdb_session_client') == 'v4-compatible':
                    continue
                held.setdefault(mapping[setting_id], {})[value] = setting_id
        spec = import_map.DATABASES.get(addon_id)
        if spec:
            for setting_id, value in _read_database(addon_id, spec).items():
                held.setdefault(spec['keys'][setting_id], {})[value] = setting_id
        collected[addon_id] = held
    from reauthorize.modules.sync import aniverse_sync
    if _installed(aniverse_sync.ADDON_ID):
        try:
            data = aniverse_sync.read_rd()
        except OSError:
            data = {}
        if aniverse_sync.rd_configured(data):
            held = collected.setdefault(aniverse_sync.ADDON_ID, {})
            for field, key in aniverse_sync.RD_FIELDS.items():
                held.setdefault(key, {})[data[field]] = 'realdebrid.json.' + field
    # Trakt is a JSON bundle; scalar settings mappings cannot express it.
    import json
    addon_id = 'script.module.tmdbhelper.sync.trakt'
    if _installed(addon_id):
        try:
            raw = xbmcaddon.Addon(addon_id).getSetting('token')
            token = json.loads(raw) if raw else {}
            held = collected.setdefault(addon_id, {})
            for source, target in (('access_token', 'trakt.token'), ('refresh_token', 'trakt.refresh')):
                value = token.get(source)
                if isinstance(value, str) and _is_value(value):
                    held.setdefault(target, {})[value] = 'token.' + source
        except (ValueError, TypeError, AttributeError, RuntimeError):
            pass
    return collected


# --- deciding -------------------------------------------------------------

def _login_in(held, addon_id, required, optional):
    """The complete login for one service in one addon, or None."""
    values = {}
    for key in required:
        candidates = held.get(key, {})
        if len(candidates) > 1:
            # Two different values for the same credential inside one addon:
            # we cannot tell which is live, so we adopt neither.
            _log('%s holds two different values for %s - skipped' % (addon_id, key))
            return None
        if not candidates:
            return None
        values[key] = next(iter(candidates))
    for key in optional:
        names = [value for value, setting_id in held.get(key, {}).items()
                 if _NAME_LIKE.search(setting_id)]
        if len(names) == 1:
            values[key] = names[0]
    return values


def _has_login(service, required):
    if all(_is_value(control.setting(key)) for key in required):
        return True
    # These services can be signed in through a separate account flow.
    account_key = {
        'tmdb': 'tmdb.session_id',
        'mdblist': 'mdblist.oauth.token',
        'youtube': 'youtube.tokens',
    }.get(service)
    return bool(account_key and _is_value(control.setting(account_key)))


def scan():
    """
    Look, change nothing. Returns (checked, findings):
      checked  - ids of every installed addon that was looked at
      findings - one Finding per service found anywhere
    """
    collected = _collect()
    findings = []

    for service, label, required, optional in ADOPTABLE:
        if _has_login(service, required):
            continue
        options = []
        for addon_id, held in collected.items():
            values = _login_in(held, addon_id, required, optional)
            if values is None:
                continue
            key = tuple(values[k] for k in required)
            match = next((o for o in options
                          if tuple(o.values[k] for k in required) == key), None)
            if match:
                match.addons.append(addon_id)
                for k in optional:
                    if k in values and k not in match.values:
                        match.values[k] = values[k]
            else:
                options.append(Option(values, addon_id))
        if options:
            status = 'new' if len(options) == 1 else 'conflict'
            findings.append(Finding(service, label, status, options, required, optional))

    for service, label, key in REPORT_ONLY:
        if _has_login(service, (key,)):
            continue
        where = [addon_id for addon_id, held in collected.items() if held.get(key)]
        if where:
            option = Option({}, where[0])
            option.addons = where
            findings.append(Finding(service, label, 'report', [option]))

    return sorted(collected), findings


# --- remembering 'not now' -------------------------------------------------

def _fingerprint(finding):
    """Identifies what was found without storing any of it."""
    parts = [finding.service, finding.status]
    for option in finding.options:
        parts.append('|'.join(option.values.get(k, '') for k in finding.required))
        parts.append(','.join(sorted(option.addons)))
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()[:16]


def _declined():
    return set(filter(None, control.setting(DECLINED_SETTING).split(',')))


def _remember(findings):
    seen = _declined() | set(_fingerprint(f) for f in findings)
    control.setSetting(DECLINED_SETTING, ','.join(sorted(seen)))


# --- asking ---------------------------------------------------------------

def _describe(values, finding):
    """Which account, without showing a secret: a username, or a key's last 4."""
    for key in tuple(finding.optional) + tuple(finding.required):
        if ('user' in key or 'name' in key) and values.get(key):
            return values[key]
    first = values.get(finding.required[0], '') if finding.required else ''
    return 'key ending ...%s' % first[-4:] if first else ''


def _where(option):
    return ', '.join(addon_name(a) for a in option.addons)


def _summary(adoptable, reports):
    lines = []
    for f in adoptable:
        if f.status == 'new':
            lines.append('[B]%s[/B] - in %s' % (f.label, _where(f.options[0])))
        elif f.status == 'conflict':
            lines.append('[B]%s[/B] - two different sign-ins found, you will pick one' % f.label)
    # A login made inside an add-on belongs to that add-on's own app and cannot be copied
    # across. Kept short: the old two-line wording ran past the bottom of a skin's small OK
    # dialog (a builder's screenshot, 2026-10-01).
    for f in reports:
        lines.append('[B]%s[/B] is signed in inside %s, not in Diggz Account Manager.' % (f.label, _where(f.options[0])))
    if reports:
        lines.append('Sign in to %s through Diggz Account Manager to share it with all your add-ons.'
                     % ' and '.join(f.label for f in reports))
    return '[CR]'.join(lines)


def _choose(finding):
    """The values to adopt for one finding, or None to leave it."""
    if finding.status == 'new':
        return finding.options[0].values
    dialog = xbmcgui.Dialog()
    heading = '%s - which sign-in should Diggz Account Manager use?' % finding.label
    labels = ['%s (in %s)' % (_describe(o.values, finding), _where(o)) for o in finding.options]
    labels.append('Skip %s for now' % finding.label)
    pick = dialog.select(heading, labels)
    if 0 <= pick < len(finding.options):
        return finding.options[pick].values
    return None


def adopt(chosen):
    """
    Take the chosen logins into Diggz Account Manager, then treat them exactly as a fresh
    sign-in would be: push to every addon, refresh the status lines, back up.
    Returns the services adopted and the services whose push failed.
    """
    adopted = set()
    for service, _, required, _ in ADOPTABLE:
        if service not in chosen or _has_login(service, required):
            continue
        for key, value in chosen[service].items():
            control.setSetting(key, value)
        adopted.add(service)
    if not adopted:
        return adopted, []

    from reauthorize.modules.sync_all import run_all_syncs
    include_trakt = control.setting('trakt.auto_push.consent') != 'false'
    failed = run_all_syncs(include_trakt=include_trakt)

    try:
        from reauthorize.modules import settings_display
        settings_display.sync_authorized_display_values()
    except Exception as e:
        _log('status refresh failed: %s' % e)

    from reauthorize.modules import vault, server
    vault.backup()
    server.backup()
    return adopted, failed


def _nothing_found(checked):
    names = ', '.join(addon_name(a) for a in checked)
    if not checked:
        text = ('None of the add-ons Diggz Account Manager works with are installed yet, '
                'so there was nothing to check.')
    else:
        text = 'Checked %s.[CR][CR]No sign-ins were found for services missing credentials in Diggz Account Manager.' % names
    xbmcgui.Dialog().ok('Diggz Account Manager', text)


def run(explicit=False):
    """
    explicit=True  - the user pressed the button: show everything, including
                     things they said 'not now' to before, and say so when
                     nothing was found.
    explicit=False - Diggz Account Manager was opened: speak up only about findings the
                     user has not already turned down.
    Returns True if anything was adopted.
    """
    checked, findings = scan()
    declined = set() if explicit else _declined()
    waiting = [f for f in findings
               if _fingerprint(f) not in declined]
    if not waiting:
        if explicit:
            _nothing_found(checked)
        return False

    adoptable = [f for f in waiting if f.status != 'report']
    reports = [f for f in waiting if f.status == 'report']
    dialog = xbmcgui.Dialog()
    intro = 'Diggz Account Manager found sign-ins you made inside your add-ons:[CR][CR]%s' % _summary(adoptable, reports)

    if not adoptable:
        dialog.ok('Diggz Account Manager', _summary([], reports))
        _remember(reports)
        return False

    question = (intro + '[CR][CR]Add them to Diggz Account Manager, so they are backed up and '
                'shared with your other add-ons?')
    if not dialog.yesno('Diggz Account Manager', question, nolabel='Not now', yeslabel='Add them'):
        _remember(waiting)
        return False

    chosen, skipped = {}, list(reports)
    for finding in adoptable:
        values = _choose(finding)
        if values:
            chosen[finding.service] = values
        else:
            skipped.append(finding)
    _remember(skipped)
    if not chosen:
        return False

    adopted, failed = adopt(chosen)
    if not adopted:
        return False
    labels = [f.label for f in adoptable if f.service in adopted]
    message = 'Added %s' % ', '.join(labels)
    if getattr(failed, 'has_issues', bool(failed)):
        from reauthorize.modules.sync_all import show_result
        show_result(failed)
        message += ' - see synchronization report'
    control.notification(message=message)
    return True
