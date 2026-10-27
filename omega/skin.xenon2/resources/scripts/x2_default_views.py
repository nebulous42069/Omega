"""Xenon defaults integrated with Skin Variables' native per-add-on views."""
import json
import os
import sys
import tempfile
import xbmc
import xbmcgui
import xbmcvfs

PREFIX = 'Xenon2.DefaultView.'
DEFAULTS = {'movies': 57, 'tvshows': 57, 'seasons': 50, 'episodes': 507, 'videos': 50, 'files': 50, 'sets': 50, 'artists': 55, 'albums': 501, 'songs': 506, 'addons': 50, 'genres': 50, 'musicvideos': 57, 'games': 50, 'images': 504, 'none': 50, 'playlists': 50, 'actors': 50, 'directors': 50, 'studios': 50, 'years': 50, 'tags': 50, 'countries': 50, 'videoversions': 50}
LEGACY_CONTENT = ('movies', 'tvshows', 'seasons', 'episodes', 'videos', 'files')
TITLES = {'movies': 'Movies', 'tvshows': 'TV Shows', 'seasons': 'Seasons', 'episodes': 'Episodes', 'videos': 'Videos', 'files': 'Files', 'sets': 'Movie Sets', 'artists': 'Artists', 'albums': 'Albums', 'songs': 'Songs', 'addons': 'Addons', 'genres': 'Video Genres', 'musicvideos': 'Music Videos', 'games': 'Games', 'images': 'Images', 'none': 'Unspecified Content (other windows)', 'playlists': 'Playlists', 'actors': 'Actors', 'directors': 'Directors', 'studios': 'Studios', 'years': 'Years', 'tags': 'Tags', 'countries': 'Countries', 'videoversions': 'Video Versions'}
MANAGED = dict(DEFAULTS, **{'none-videos': 50})
VIEWS = {50: 'Panel', 51: 'Info Wall', 52: 'Landscape', 53: 'Showcase', 54: 'Square Showcase',
         55: 'Tri Panel', 56: 'Posters', 57: 'Fixedlist', 58: 'Banner Wall',
         59: 'Logo', 500: 'Icons', 501: 'Low List', 502: 'Episode',
         503: 'Wall', 504: 'Gallery', 505: 'Panel', 506: 'Right List',
         507: 'List', 508: 'Song List', 509: 'MyFlix', 591: 'Big Fan', 602: 'Fanart List', 603: 'Jukebox',
         609: 'Fullscreen Wall'}


def paths():
    if xbmc.getSkinDir() != 'skin.xenon2':
        raise ValueError('Xenon 2 is not active')
    return tuple(xbmcvfs.translatePath(path) for path in (
        'special://skin/shortcuts/skinviewtypes.json',
        'special://profile/addon_data/script.skinvariables/skin.xenon2-viewtypes.json',
        'special://profile/addon_data/skin.xenon2/default-views-native.json'))


def read_json(path, missing=None):
    if not os.path.exists(path):
        return {} if missing is None else missing
    with open(path, encoding='utf-8-sig') as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError('Invalid view configuration')
    return value


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.x2-views-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def label(view):
    return '%s (%d)' % (VIEWS.get(view, 'View'), view)


def valid_view(config, content, view):
    return str(view) in config['rules'][content]['viewtypes']


def global_view(config, data, content):
    value = data.get('plugins', {}).get(content, config['rules'][content].get('plugins', DEFAULTS[content]))
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULTS[content]
    return value if valid_view(config, content, value) else DEFAULTS[content]


def mirror_labels(config, data):
    for content in DEFAULTS:
        view = global_view(config, data, content)
        xbmc.executebuiltin('Skin.SetString(%s%s,%d)' % (PREFIX, content, view))
        xbmc.executebuiltin('Skin.SetString(%s%s.Label,"%s")' % (PREFIX, content, label(view)))


def apply_global(config, data, content, view):
    if content not in MANAGED or not valid_view(config, content, view):
        raise ValueError('Unsupported view for this content')
    for scope in ('library', 'plugins'):
        config['rules'][content][scope] = str(view)
        data.setdefault(scope, {})[content] = str(view)


def keep_none_fixed(config, data):
    rule = config['rules']['none-videos']
    rule['viewtypes'] = ['50']
    apply_global(config, data, 'none-videos', 50)
    for scope, rules in data.items():
        if scope not in ('library', 'plugins') and isinstance(rules, dict):
            rules.pop('none-videos', None)


def rebuild(force=False):
    command = 'RunScript(script.skinvariables,action=buildviews'
    if force:
        command += ',force=true'
    xbmc.executebuiltin(command + ')')


def initialize():
    config_path, data_path, marker_path = paths()
    config, data = read_json(config_path), read_json(data_path)
    before = json.dumps((config, data), sort_keys=True)
    first = not os.path.exists(marker_path)
    if first:
        for content in LEGACY_CONTENT:
            default = DEFAULTS[content]
            # Migrate global choices from the previous helper once; retain all
            # explicit native per-add-on choices on initial installation.
            old = xbmc.getInfoLabel('Skin.String(%s%s)' % (PREFIX, content))
            try:
                view = int(old)
            except (TypeError, ValueError):
                view = default
            apply_global(config, data, content, view if valid_view(config, content, view) else default)
    keep_none_fixed(config, data)
    dirty = before != json.dumps((config, data), sort_keys=True)
    if dirty or first:
        write_json(config_path, config)
        write_json(data_path, data)
        write_json(marker_path, {'version': 1})
    mirror_labels(config, data)
    rebuild(force=dirty or first)


def set_global(content, view):
    config_path, data_path, marker_path = paths()
    config, data = read_json(config_path), read_json(data_path)
    apply_global(config, data, content, view)
    keep_none_fixed(config, data)
    write_json(config_path, config)
    write_json(data_path, data)
    write_json(marker_path, {'version': 1})
    mirror_labels(config, data)
    rebuild(force=True)


def reset_video_views():
    config_path, data_path, marker_path = paths()
    config, data = read_json(config_path), read_json(data_path)
    for scope in list(data):
        if scope in ('library', 'plugins'):
            continue
        rules = data[scope]
        if not isinstance(rules, dict):
            raise ValueError('Invalid saved view configuration')
        for content in MANAGED:
            rules.pop(content, None)
        if not rules:
            del data[scope]
    # Global library/plugin defaults are retained exactly as chosen.
    keep_none_fixed(config, data)
    write_json(config_path, config)
    write_json(data_path, data)
    write_json(marker_path, {'version': 1})
    mirror_labels(config, data)
    rebuild(force=True)


def run(arguments):
    params = dict(arg.split('=', 1) for arg in arguments if '=' in arg)
    if not xbmc.getCondVisibility('System.AddonIsEnabled(script.skinvariables)'):
        if params.get('init') != 'true':
            xbmcgui.Dialog().ok('Default Views', 'Enable Skin Variables to configure saved views.')
        return
    if params.get('init') == 'true':
        initialize()
    elif params.get('reset') == 'true':
        reset_video_views()
    elif params.get('content') in DEFAULTS:
        content = params['content']
        config_path, data_path, marker_path = paths()
        config, data = read_json(config_path), read_json(data_path)
        views = [int(view) for view in config['rules'][content]['viewtypes']]
        current = global_view(config, data, content)
        choice = xbmcgui.Dialog().select(TITLES[content] + ' - global default',
                                        [label(view) for view in views],
                                        preselect=views.index(current))
        if choice >= 0:
            set_global(content, views[choice])


if __name__ == '__main__':
    try:
        run(sys.argv[1:])
    except Exception as error:
        xbmc.log('Xenon 2 default views: ' + type(error).__name__, xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Default Views', 'The view settings could not be updated. Check kodi.log.')
