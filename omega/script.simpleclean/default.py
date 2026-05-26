import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import shutil
import sqlite3
import time


# ===========================================================
#                     ADDON INFO
# ===========================================================

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')


# ===========================================================
#                     KODI PATHS
# ===========================================================

KODI_HOME      = xbmcvfs.translatePath('special://home/')
ADDONS_DIR     = os.path.join(KODI_HOME, 'addons')
USERDATA_DIR   = os.path.join(KODI_HOME, 'userdata')
DATABASE_DIR   = os.path.join(USERDATA_DIR, 'Database')
PACKAGES_DIR   = os.path.join(ADDONS_DIR, 'packages')
ADDONS_TEMP    = os.path.join(ADDONS_DIR, 'temp')
CACHE_DIR      = os.path.join(KODI_HOME, 'cache')
TEMP_DIR       = os.path.join(KODI_HOME, 'temp')
THUMBNAILS_DIR = os.path.join(USERDATA_DIR, 'Thumbnails')


# ===========================================================
#                   HELPER FUNCTIONS
# ===========================================================

def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[{0}] {1}'.format(ADDON_ID, msg), level)


def setting(key):
    return ADDON.getSetting(key)


def bool_setting(key):
    v = setting(key)
    return v.lower() == 'true' if v else False


def fmt_size(n):
    if n < 1024:
        return '{0} B'.format(n)
    if n < 1048576:
        return '{0:.1f} KB'.format(n / 1024.0)
    if n < 1073741824:
        return '{0:.1f} MB'.format(n / 1048576.0)
    return '{0:.2f} GB'.format(n / 1073741824.0)


def calc_folder_size(path):
    """Calculate total size of a folder recursively."""
    total = 0
    if not os.path.isdir(path):
        return 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def count_folder_files(path):
    """Count files in a folder recursively."""
    count = 0
    if not os.path.isdir(path):
        return 0
    try:
        for root, dirs, files in os.walk(path):
            count += len(files)
    except OSError:
        pass
    return count


def is_inside_kodi(path):
    """Safety check: path must be inside Kodi home."""
    p = os.path.normpath(os.path.realpath(path))
    k = os.path.normpath(os.path.realpath(KODI_HOME))
    if p == k:
        return False
    return p.startswith(k + os.sep)


def safe_delete_folder(path):
    """Safely delete a folder. Returns (success, message)."""
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        return True, 'does not exist'
    if not is_inside_kodi(path):
        return False, 'UNSAFE PATH - outside Kodi!'
    try:
        shutil.rmtree(path)
        return True, 'deleted'
    except Exception as e:
        return False, str(e)


def safe_delete_file(path):
    """Safely delete a file. Returns (success, message)."""
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        return True, 'does not exist'
    if not is_inside_kodi(path):
        return False, 'UNSAFE PATH - outside Kodi!'
    try:
        os.remove(path)
        return True, 'deleted'
    except Exception as e:
        return False, str(e)


def remove_empty_dirs(path):
    """Remove empty subfolders under a Kodi folder after pruning files."""
    removed = 0
    if not os.path.isdir(path) or not is_inside_kodi(path):
        return 0

    for root, dirs, files in os.walk(path, topdown=False):
        if os.path.normpath(root) == os.path.normpath(path):
            continue
        try:
            os.rmdir(root)
            removed += 1
        except OSError:
            pass
    return removed


# ===========================================================
#             TEXTURE / THUMBNAIL PRUNING HELPERS
# ===========================================================

def texture_db_version(path):
    """Return the numeric version from a Textures*.db filename."""
    base = os.path.basename(path).lower()
    digits = ''.join(ch for ch in base if ch.isdigit())
    return int(digits) if digits else 0


def find_texture_db_files(include_sidecars=False):
    """Find Kodi texture database files."""
    matches = []
    if not os.path.isdir(DATABASE_DIR):
        return matches

    for f in os.listdir(DATABASE_DIR):
        fl = f.lower()
        if not fl.startswith('textures'):
            continue
        if fl.endswith('.db') or (include_sidecars and (fl.endswith('.db-shm') or fl.endswith('.db-wal'))):
            matches.append(os.path.join(DATABASE_DIR, f))

    return sorted(matches, key=texture_db_version)


def find_latest_textures_db():
    """Find the newest Textures*.db file by version number."""
    matches = find_texture_db_files(include_sidecars=False)
    if not matches:
        return None
    return matches[-1]


def normalize_cached_thumb_path(cached):
    """Normalize Textures DB cachedurl values so they match Thumbnails relative paths."""
    if not cached:
        return ''

    cached = cached.replace('\\', '/').strip().lstrip('/')

    # Some cached paths may contain a full or special Kodi thumbnail path.
    marker = '/Thumbnails/'
    if marker in cached:
        cached = cached.split(marker, 1)[1]

    if cached.startswith('Thumbnails/'):
        cached = cached[len('Thumbnails/'):]

    return cached.lower()


def read_referenced_thumbnails():
    """Read thumbnail files currently referenced by Kodi's Textures database."""
    db_path = find_latest_textures_db()
    if not db_path:
        return None, 'No Textures*.db file was found.'

    referenced = set()
    conn = None

    try:
        conn = sqlite3.connect(db_path, timeout=2)
        cur = conn.cursor()
        cur.execute('SELECT cachedurl FROM texture WHERE cachedurl IS NOT NULL')
        for row in cur.fetchall():
            cached = normalize_cached_thumb_path(row[0])
            if cached:
                referenced.add(cached)
    except Exception as e:
        return None, 'Could not read {0}: {1}'.format(os.path.basename(db_path), e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return referenced, None


def scan_orphaned_thumbnails(dialog=None, start_pct=0, end_pct=100):
    """
    Find thumbnail files that are not referenced by Textures*.db.

    This is safer than deleting the entire Thumbnails folder while Kodi is running.
    Kodi will keep using valid cached artwork, and only old/orphaned files are removed.
    """
    result = {
        'type': 'thumbnail_prune',
        'label': 'Unused thumbnails',
        'files': [],
        'count': 0,
        'size': 0,
        'status': 'skipped',
        'message': '',
        'cancelled': False,
    }

    if not os.path.isdir(THUMBNAILS_DIR):
        result['message'] = 'Thumbnail folder does not exist.'
        return result

    referenced, err = read_referenced_thumbnails()
    if err:
        result['status'] = 'error'
        result['message'] = err
        return result

    total_files = count_folder_files(THUMBNAILS_DIR)
    checked = 0

    try:
        for root, dirs, files in os.walk(THUMBNAILS_DIR):
            for f in files:
                if dialog and dialog.iscanceled():
                    result['cancelled'] = True
                    result['message'] = 'Thumbnail scan canceled.'
                    return result

                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, THUMBNAILS_DIR).replace('\\', '/')
                rel_key = rel_path.lower()
                checked += 1

                if dialog and total_files > 0:
                    pct = start_pct + int((checked / float(total_files)) * (end_pct - start_pct))
                    dialog.update(
                        pct,
                        '[COLOR deepskyblue]Checking thumbnail cache:[/COLOR]\n'
                        '[COLOR silver]{0}[/COLOR]'.format(rel_path)
                    )

                if rel_key not in referenced:
                    try:
                        sz = os.path.getsize(full_path)
                    except OSError:
                        sz = 0
                    result['files'].append((full_path, rel_path, sz))
                    result['count'] += 1
                    result['size'] += sz
    except OSError as e:
        result['status'] = 'error'
        result['message'] = 'Could not scan thumbnail folder: {0}'.format(e)
        return result

    result['status'] = 'ok'
    if result['count'] == 0:
        result['message'] = 'No unused thumbnails found.'
    else:
        result['message'] = '{0} unused thumbnail files found.'.format(result['count'])
    return result


def refresh_kodi_ui():
    """Refresh Kodi UI after cleaning without forcing a full Kodi restart."""
    try:
        xbmc.executebuiltin('Container.Refresh')
        xbmc.sleep(500)
        xbmc.executebuiltin('ReloadSkin()')
        log('Kodi UI refreshed with Container.Refresh and ReloadSkin')
    except Exception as e:
        log('UI refresh failed: {0}'.format(e), xbmc.LOGWARNING)


# ===========================================================
#                       CLEANING
# ===========================================================

def do_cleaning():
    """Clean selected Kodi cache/temp/junk folders and safely prune thumbnail cache."""

    folder_targets = []
    info_lines = []
    skip_lines = []

    if bool_setting('clean_packages'):
        folder_targets.append({
            'type': 'folder',
            'path': PACKAGES_DIR,
            'label': 'addons/packages/',
            'desc': 'Downloaded add-on ZIP files',
        })

    if bool_setting('clean_addons_temp'):
        folder_targets.append({
            'type': 'folder',
            'path': ADDONS_TEMP,
            'label': 'addons/temp/',
            'desc': 'Temporary add-on files',
        })

    if bool_setting('clean_cache'):
        folder_targets.append({
            'type': 'folder',
            'path': CACHE_DIR,
            'label': 'cache/',
            'desc': 'General Kodi cache',
        })

    if bool_setting('clean_temp'):
        folder_targets.append({
            'type': 'folder',
            'path': TEMP_DIR,
            'label': 'temp/',
            'desc': 'Kodi temp files',
        })

    if bool_setting('clean_thumbnails'):
        # Do not delete userdata/Thumbnails while Kodi is running.
        # Instead, prune orphaned thumbnail files that are not referenced by Textures*.db.
        info_lines.append(
            '[COLOR deepskyblue]Thumbnail cache:[/COLOR] '
            '[COLOR white]Safe prune mode enabled[/COLOR]\n'
            '         [COLOR silver]Only unused thumbnails will be deleted. Active artwork is kept.[/COLOR]'
        )

        # These add-on image caches are separate from Kodi's main artwork cache.
        folder_targets.append({
            'type': 'folder',
            'path': os.path.join(USERDATA_DIR, 'addon_data', 'plugin.video.themoviedb.helper', 'blur_v3'),
            'label': 'TMDb blur_v3/',
            'desc': 'Blurred image cache',
        })
        folder_targets.append({
            'type': 'folder',
            'path': os.path.join(USERDATA_DIR, 'addon_data', 'plugin.video.themoviedb.helper', 'crop_v2'),
            'label': 'TMDb crop_v2/',
            'desc': 'Cropped image cache',
        })

    if bool_setting('clean_textures_db'):
        texture_files = find_texture_db_files(include_sidecars=True)
        if texture_files:
            tex_size = 0
            for fp in texture_files:
                try:
                    tex_size += os.path.getsize(fp)
                except OSError:
                    pass
            skip_lines.append(
                '[COLOR orange]Skipped live artwork DB reset:[/COLOR] '
                '[COLOR white]Textures*.db[/COLOR]  -  '
                '[COLOR springgreen]{0}[/COLOR]\n'
                '         [COLOR silver]Deleting this while Kodi is running causes missing icons/thumbnails. Restart-required deep reset only.[/COLOR]'.format(fmt_size(tex_size))
            )
        else:
            skip_lines.append(
                '[COLOR gray]Textures*.db:[/COLOR] '
                '[COLOR silver]No texture database found.[/COLOR]'
            )

    if not folder_targets and not bool_setting('clean_thumbnails') and not bool_setting('clean_textures_db'):
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            '[COLOR gold]No cleaning option is enabled![/COLOR]\n\n'
            '[COLOR white]Go to Settings -> Cleaning Options[/COLOR]\n'
            '[COLOR white]and check what you want to clean.[/COLOR]'
        )
        ADDON.openSettings()
        return

    # ---- Scan sizes and safe thumbnail prune candidates ----
    pdia = xbmcgui.DialogProgress()
    pdia.create(ADDON_NAME, '[COLOR deepskyblue]Scanning cleaning targets...[/COLOR]')
    pdia.update(0)

    total_size = 0
    total_files = 0
    details = []
    operations = []

    try:
        scan_steps = len(folder_targets) + (1 if bool_setting('clean_thumbnails') else 0)
        scan_steps = max(scan_steps, 1)
        step = 0

        for t in folder_targets:
            if pdia.iscanceled():
                pdia.close()
                return

            step += 1
            pct = int((step / float(scan_steps)) * 100)
            pdia.update(pct, '[COLOR silver]Scanning: {0}[/COLOR]'.format(t['label']))

            if os.path.isdir(t['path']):
                sz = calc_folder_size(t['path'])
                fc = count_folder_files(t['path'])
                t['size'] = sz
                t['count'] = fc
                t['exists'] = True
                total_size += sz
                total_files += fc
                operations.append(t)
                details.append(
                    '[COLOR lime]  [+][/COLOR]  '
                    '[COLOR deepskyblue]{label}[/COLOR]\n'
                    '         [COLOR white]{cnt} files[/COLOR]  -  '
                    '[COLOR springgreen]{sz}[/COLOR]'.format(
                        label=t['label'],
                        cnt=fc,
                        sz=fmt_size(sz))
                )
            else:
                t['exists'] = False
                details.append(
                    '[COLOR gray]  [-][/COLOR]  '
                    '[COLOR gray]{0}[/COLOR]  '
                    '[COLOR silver](does not exist)[/COLOR]'.format(t['label'])
                )

        thumb_scan = None
        if bool_setting('clean_thumbnails'):
            if pdia.iscanceled():
                pdia.close()
                return

            step += 1
            start_pct = int(((step - 1) / float(scan_steps)) * 100)
            end_pct = 100
            thumb_scan = scan_orphaned_thumbnails(pdia, start_pct, end_pct)

            if thumb_scan.get('cancelled'):
                pdia.close()
                return

            if thumb_scan['status'] == 'ok' and thumb_scan['count'] > 0:
                total_size += thumb_scan['size']
                total_files += thumb_scan['count']
                operations.append(thumb_scan)
                details.append(
                    '[COLOR lime]  [+][/COLOR]  '
                    '[COLOR deepskyblue]Unused thumbnails[/COLOR]\n'
                    '         [COLOR white]{cnt} files[/COLOR]  -  '
                    '[COLOR springgreen]{sz}[/COLOR]'.format(
                        cnt=thumb_scan['count'],
                        sz=fmt_size(thumb_scan['size']))
                )
            elif thumb_scan['status'] == 'ok':
                details.append(
                    '[COLOR gray]  [-][/COLOR]  '
                    '[COLOR gray]Unused thumbnails[/COLOR]  '
                    '[COLOR silver](none found)[/COLOR]'
                )
            else:
                details.append(
                    '[COLOR orange]  [!][/COLOR]  '
                    '[COLOR orange]Unused thumbnail scan skipped[/COLOR]\n'
                    '         [COLOR silver]{0}[/COLOR]'.format(thumb_scan['message'])
                )

    finally:
        try:
            pdia.close()
        except Exception:
            pass

    if info_lines:
        details.insert(0, '\n'.join(info_lines))

    if skip_lines:
        details.append(
            '[COLOR gold]----------------------------------------[/COLOR]\n'
            '[COLOR gold]Safe-mode notes[/COLOR]\n'
            '[COLOR gold]----------------------------------------[/COLOR]\n'
            + '\n'.join(skip_lines)
        )

    if not operations:
        details_msg = (
            '[COLOR lime]========================================[/COLOR]\n'
            '[COLOR lime]        NOTHING TO DELETE[/COLOR]\n'
            '[COLOR lime]========================================[/COLOR]\n\n'
            '{details}\n\n'
            '[COLOR silver]No restart is needed.[/COLOR]'
        ).format(details='\n\n'.join(details) if details else '[COLOR silver]No matching cleanup targets were found.[/COLOR]')
        xbmcgui.Dialog().textviewer(ADDON_NAME + '  -  Cleaning Details', details_msg)
        refresh_kodi_ui()
        return

    # ---- Show cleaning details in a larger window ----
    detail_text = '\n\n'.join(details)

    details_msg = (
        '[COLOR orangered]========================================[/COLOR]\n'
        '[COLOR orangered]            CLEANING DETAILS[/COLOR]\n'
        '[COLOR orangered]========================================[/COLOR]\n\n'
        '{details}\n\n'
        '[COLOR gold]==========================================[/COLOR]\n'
        '[COLOR gold]Total to delete:[/COLOR]  '
        '[COLOR orangered]{files} files[/COLOR]  -  '
        '[COLOR orangered]{size}[/COLOR]\n'
        '[COLOR gold]==========================================[/COLOR]\n\n'
        '[COLOR lime]No-restart safe mode:[/COLOR]\n'
        '[COLOR silver]Textures*.db is not deleted while Kodi is running. Unused thumbnails are pruned instead of wiping all artwork.[/COLOR]\n\n'
        '[COLOR silver]Close this window to continue to the final confirmation.[/COLOR]'
    ).format(
        details=detail_text,
        files=total_files,
        size=fmt_size(total_size)
    )

    xbmcgui.Dialog().textviewer(ADDON_NAME + '  -  Cleaning Details', details_msg)

    confirm_msg = (
        '[COLOR gold]Ready to clean:[/COLOR]\n'
        '[COLOR orangered]{files} files[/COLOR]  -  '
        '[COLOR orangered]{size}[/COLOR]\n\n'
        '[COLOR lime]Safe mode is active:[/COLOR]\n'
        '[COLOR white]Textures DB will not be deleted live.[/COLOR]\n\n'
        '[COLOR orange]Continue with cleaning?[/COLOR]'
    ).format(
        files=total_files,
        size=fmt_size(total_size)
    )

    if not xbmcgui.Dialog().yesno(
        ADDON_NAME + '  -  Confirm Cleaning',
        confirm_msg,
        yeslabel='[COLOR orangered]Yes, clean now[/COLOR]',
        nolabel='[COLOR lime]Cancel[/COLOR]'
    ):
        return

    # ---- Perform cleaning ----
    pdia = xbmcgui.DialogProgress()
    pdia.create(ADDON_NAME, '[COLOR orangered]Cleaning files...[/COLOR]\n ')

    deleted_targets = 0
    deleted_files = 0
    deleted_fail = 0
    freed_size = 0
    results = []
    canceled = False

    op_count = max(len(operations), 1)

    for idx, t in enumerate(operations):
        if pdia.iscanceled():
            canceled = True
            break

        if t['type'] == 'folder':
            pct = int(((idx + 1) / float(op_count)) * 100)
            pdia.update(
                pct,
                '[COLOR orangered]Deleting:[/COLOR]\n'
                '[COLOR white]{0}[/COLOR]'.format(t['label'])
            )

            ok, msg = safe_delete_folder(t['path'])
            if ok:
                deleted_targets += 1
                deleted_files += t.get('count', 0)
                freed_size += t.get('size', 0)
                results.append(
                    '[COLOR lime]  [OK][/COLOR]  '
                    '[COLOR white]{0}[/COLOR]  '
                    '[COLOR springgreen]({1})[/COLOR]'.format(
                        t['label'], fmt_size(t.get('size', 0)))
                )
                log('CLEAN OK: {0}'.format(t['path']))
            else:
                deleted_fail += 1
                results.append(
                    '[COLOR red]  [FAIL][/COLOR]  '
                    '[COLOR white]{0}[/COLOR]\n'
                    '         [COLOR red]{1}[/COLOR]'.format(t['label'], msg)
                )
                log('CLEAN FAIL: {0} -> {1}'.format(t['path'], msg), xbmc.LOGWARNING)

        elif t['type'] == 'thumbnail_prune':
            files = t.get('files', [])
            total = max(len(files), 1)
            thumb_deleted = 0
            thumb_failed = 0
            thumb_freed = 0

            for j, (full_path, rel_path, sz) in enumerate(files):
                if pdia.iscanceled():
                    canceled = True
                    break

                pct = int(((idx + ((j + 1) / float(total))) / float(op_count)) * 100)
                pdia.update(
                    pct,
                    '[COLOR deepskyblue]Pruning unused thumbnails:[/COLOR]\n'
                    '[COLOR silver]{0}[/COLOR]'.format(rel_path)
                )

                ok, msg = safe_delete_file(full_path)
                if ok:
                    thumb_deleted += 1
                    thumb_freed += sz
                else:
                    thumb_failed += 1
                    log('THUMB PRUNE FAIL: {0} -> {1}'.format(full_path, msg), xbmc.LOGWARNING)

            empty_dirs = remove_empty_dirs(THUMBNAILS_DIR)

            if thumb_deleted > 0:
                deleted_targets += 1
                deleted_files += thumb_deleted
                freed_size += thumb_freed
                results.append(
                    '[COLOR lime]  [OK][/COLOR]  '
                    '[COLOR white]Unused thumbnails[/COLOR]  '
                    '[COLOR springgreen]({0}, {1} files)[/COLOR]'.format(
                        fmt_size(thumb_freed), thumb_deleted)
                )
                if empty_dirs > 0:
                    results.append(
                        '         [COLOR silver]Removed {0} empty thumbnail folders[/COLOR]'.format(empty_dirs)
                    )
                log('Thumbnail prune OK: {0} files, freed {1}'.format(thumb_deleted, fmt_size(thumb_freed)))

            if thumb_failed > 0:
                deleted_fail += thumb_failed
                results.append(
                    '[COLOR orange]  [!][/COLOR]  '
                    '[COLOR white]Thumbnail prune failures:[/COLOR] '
                    '[COLOR red]{0}[/COLOR]'.format(thumb_failed)
                )

            if canceled:
                break

        time.sleep(0.1)

    try:
        pdia.close()
    except Exception:
        pass

    # ---- Results ----
    results_text = '\n'.join(results) if results else '[COLOR silver]No files were deleted.[/COLOR]'

    title = 'CLEANING CANCELED' if canceled else 'CLEANING COMPLETE!'
    title_color = 'orange' if canceled else 'lime'

    result_msg = (
        '[COLOR {title_color}]========================================[/COLOR]\n'
        '[COLOR {title_color}]        {title}[/COLOR]\n'
        '[COLOR {title_color}]========================================[/COLOR]\n\n'
        '{results}\n\n'
        '[COLOR gold]==========================================[/COLOR]\n'
        '[COLOR deepskyblue]Targets cleaned:[/COLOR]  '
        '[COLOR springgreen]{targets}[/COLOR]\n'
        '[COLOR deepskyblue]Files deleted:[/COLOR]  '
        '[COLOR springgreen]{files}[/COLOR]\n'
        '[COLOR deepskyblue]Space freed:[/COLOR]  '
        '[COLOR springgreen]{freed}[/COLOR]\n'
    ).format(
        title_color=title_color,
        title=title,
        results=results_text,
        targets=deleted_targets,
        files=deleted_files,
        freed=fmt_size(freed_size)
    )

    if deleted_fail > 0:
        result_msg += (
            '[COLOR orange]Failures:[/COLOR]  '
            '[COLOR red]{0}[/COLOR]\n'
        ).format(deleted_fail)

    result_msg += (
        '[COLOR gold]==========================================[/COLOR]\n\n'
        '[COLOR lime]Kodi skin/listing will be refreshed after you press OK.[/COLOR]\n'
        '[COLOR silver]A restart is not required for this safe clean.[/COLOR]'
    )

    xbmcgui.Dialog().ok(ADDON_NAME, result_msg)

    log('Cleaning done: {0} targets, {1} files, {2} failures, freed {3}'.format(
        deleted_targets, deleted_files, deleted_fail, fmt_size(freed_size)))

    refresh_kodi_ui()


# ===========================================================
#                     ENTRY POINT
# ===========================================================

def main():
    """Open the cleaning workflow directly."""
    do_cleaning()


if __name__ == '__main__':
    main()
