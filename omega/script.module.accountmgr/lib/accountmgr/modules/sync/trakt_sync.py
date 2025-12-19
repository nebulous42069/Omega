import os
import json
import time

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from libs.common import var


def _log(msg, level=xbmc.LOGINFO):
    try:
        xbmc.log(f"{var.amgr}: {msg}", level)
    except Exception:
        xbmc.log(f"AccountMgr: {msg}", level)


def _attr(name, default=None):
    return getattr(var, name, default)


def _exists_attr(name):
    p = _attr(name)
    return bool(p) and xbmcvfs.exists(p)


def _read_synclist():
    # Prefer the path from var.py (dependency), fall back to addon profile path
    path = _attr("synclist_file")
    if not path:
        addon = xbmcaddon.Addon(xbmcaddon.Addon().getAddonInfo("id"))
        addon_data = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        path = xbmcvfs.translatePath(os.path.join(addon_data, "trakt_sync_list.json"))

    if not xbmcvfs.exists(path):
        return []

    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data.get("addon_list", [])
    except Exception:
        _log("Failed to read trakt_sync_list.json", xbmc.LOGINFO)
        return []


def _get_accountmgr_trakt():
    """Always read fresh. Access tokens rotate. Humans forget. Code shouldn't."""
    try:
        am = xbmcaddon.Addon("script.module.accountmgr")
        return {
            "token": am.getSetting("trakt.token") or "",
            "username": am.getSetting("trakt.username") or "",
            "refresh": am.getSetting("trakt.refresh") or "",
            "expires": am.getSetting("trakt.expires") or "",
        }
    except Exception:
        return {"token": "", "username": "", "refresh": "", "expires": ""}


def _expires_epoch_int(expires_raw):
    try:
        return int(float(expires_raw))
    except Exception:
        return 0


def _oauth_blob(access_token, refresh_token, expires_at_epoch, expires_in=86400):
    """
    TMDb Helper + script.trakt store Trakt auth as a JSON blob.
    Old code used expires_in=7776000 and created_at=expires_at (wrong).
    This generates a sane blob: created_at = expires_at - expires_in.
    """
    now = int(time.time())
    if expires_at_epoch > 0:
        created_at = max(0, int(expires_at_epoch) - int(expires_in))
    else:
        created_at = now

    payload = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(expires_in),
        "refresh_token": refresh_token,
        "scope": "public",
        "created_at": int(created_at),
    }
    return json.dumps(payload, separators=(",", ":"))


def _ensure_userdata_and_settings(chk_attr, ud_attr, src_xml_attr, dst_xml_attr):
    """
    Some addons don't create userdata/settings.xml until first run.
    Original code created the userdata folder and copied a default settings.xml from AccountMgr resources/xmls.
    """
    try:
        if not _exists_attr(chk_attr):
            return

        ud = _attr(ud_attr)
        if ud and not xbmcvfs.exists(ud):
            try:
                xbmcvfs.mkdirs(ud)
            except Exception:
                try:
                    os.mkdir(ud)
                except Exception:
                    pass

        src = _attr(src_xml_attr)
        dst = _attr(dst_xml_attr)
        if src and dst and xbmcvfs.exists(src) and not xbmcvfs.exists(dst):
            try:
                xbmcvfs.copy(src, dst)
            except Exception:
                pass
    except Exception:
        pass


def _patch_file(path_attr, client_placeholder_attr, secret_placeholder_attr):
    """Replace placeholder API keys inside an addon file, only if it changes."""
    try:
        path = _attr(path_attr)
        if not path or not xbmcvfs.exists(path):
            return

        old_client = _attr(client_placeholder_attr)
        old_secret = _attr(secret_placeholder_attr)
        new_client = _attr("client_am")
        new_secret = _attr("secret_am")

        if not old_client or not old_secret or not new_client or not new_secret:
            return

        f = xbmcvfs.File(path)
        data = f.read()
        f.close()

        new_data = data.replace(old_client, new_client).replace(old_secret, new_secret)
        if new_data == data:
            return

        fw = xbmcvfs.File(path, "w")
        fw.write(new_data)
        fw.close()
    except Exception:
        pass


def _patch_umbrella_defaults():
    """Force Umbrella's hardcoded Trakt client keys to match Account Manager keys.
    This is a fallback for cases where Umbrella doesn't pick up custom-key settings early enough and wipes auth."""
    try:
        path = xbmcvfs.translatePath("special://home/addons/plugin.video.umbrella/resources/lib/modules/trakt.py")
        if not path or not xbmcvfs.exists(path):
            return
        new_client = _attr("client_am")
        new_secret = _attr("secret_am")
        if not new_client or not new_secret:
            return

        old_client = "87e3f055fc4d8fcfd96e61a47463327ca877c51e8597b448e132611c5a677b13"
        old_secret = "4a1957a52d5feb98fafde53193e51f692fa9bdcd0cc13cf44a5e39975539edf0"

        f = xbmcvfs.File(path)
        data = f.read()
        f.close()

        new_data = data.replace(old_client, new_client).replace(old_secret, new_secret)
        if new_data == data:
            return

        fw = xbmcvfs.File(path, "w")
        fw.write(new_data)
        fw.close()
        _log("Umbrella: patched hardcoded Trakt API keys in trakt.py", xbmc.LOGINFO)
    except Exception:
        pass


def _get_setting(addon_obj, key):
    try:
        return addon_obj.getSetting(key)
    except Exception:
        return ""


def _set_setting(addon_obj, key, value, use_set_string=False):
    try:
        v = "" if value is None else str(value)
        if use_set_string and hasattr(addon_obj, "setSettingString"):
            addon_obj.setSettingString(key, v)
        else:
            addon_obj.setSetting(key, v)
    except Exception:
        pass



def _clear_window_property(prop_key):
    try:
        xbmcgui.Window(10000).clearProperty(prop_key)
    except Exception:
        pass


def _clear_addon_settings_cache(addon_id, setting_ids):
    """Clear home-window cached settings for addons that use Window(10000) property caches (e.g. Seren)."""
    try:
        ver = xbmcaddon.Addon(addon_id).getAddonInfo("version")
        win = xbmcgui.Window(10000)
        for sid in setting_ids:
            win.clearProperty(f"{addon_id}.{ver}.persisted.{sid}")
        # Seren persists a list of cached ids in runtime settings as well
        win.clearProperty(f"{addon_id}.{ver}.runtime.CachedSettingsList")
    except Exception:
        pass

def _token_matches(addon_obj, compare_key, token, mode="equal"):
    if not compare_key:
        return False
    current = _get_setting(addon_obj, compare_key)
    if mode == "contains":
        return bool(token) and token in str(current)
    return str(current) == str(token)


def _sync(cfg, v):
    """
    cfg:
      - display (string) sync list label
      - addon_id
      - required_attrs: list of var.* attributes that must exist on disk
      - preflight: tuple(chk_attr, ud_attr, src_xml_attr, dst_xml_attr) or None
      - patch: tuple(path_attr, client_placeholder_attr, secret_placeholder_attr) or None
      - compare_key, compare_mode
      - settings: list of (key, value_ref_or_literal, use_set_string_bool)
    """
    try:
        if cfg.get("preflight"):
            _ensure_userdata_and_settings(*cfg["preflight"])

        for req in cfg.get("required_attrs", []):
            if not _exists_attr(req):
                return

        addon_obj = xbmcaddon.Addon(cfg["addon_id"])
    except Exception:
        return

    if not v["token"] or not v["refresh"]:
        return

    if _token_matches(addon_obj, cfg.get("compare_key"), v["token"], cfg.get("compare_mode", "equal")):
        return

    if cfg.get("patch"):
        _patch_file(*cfg["patch"])

    for key, valref, use_set_string in cfg.get("settings", []):
        value = v.get(valref, valref)
        _set_setting(addon_obj, key, value, use_set_string=use_set_string)
    # Some addons cache settings in Window(10000) properties. If we don't clear those,
    # they will keep showing "not authorized" even though settings.xml was updated.
    try:
        if cfg.get("addon_id") == "plugin.video.umbrella":
            _clear_window_property("umbrella_settings")
            try:
                xbmcgui.Window(10000).setProperty("umbrella.updateSettings", "true")
            except Exception:
                pass
            _patch_umbrella_defaults()
        elif cfg.get("addon_id") == "plugin.video.seren":
            _clear_addon_settings_cache(
                "plugin.video.seren",
                ["trakt.auth", "trakt.refresh", "trakt.expires", "trakt.username"],
            )
    except Exception:
        pass



class Auth:
    def trakt_auth(self):
        enabled = set(_read_synclist())
        if not enabled:
            _log("Trakt Sync List does not exist or is empty", xbmc.LOGINFO)
            return

        am = _get_accountmgr_trakt()
        expires_at = _expires_epoch_int(am["expires"])

        v = {
            "token": am["token"],
            "username": am["username"],
            "refresh": am["refresh"],
            "expires_raw": am["expires"],
            "client_am": _attr("client_am"),
            "secret_am": _attr("secret_am"),
            "tmdbh_blob": _oauth_blob(am["token"], am["refresh"], expires_at),
            "trakt_blob": _oauth_blob(am["token"], am["refresh"], expires_at),
        }

        # ----- Config table -----
        targets = [
            # Seren
            dict(
                display="Seren",
                addon_id="plugin.video.seren",
                required_attrs=["chk_seren", "chkset_seren", "path_seren"],
                patch=("path_seren", "seren_client", "seren_secret"),
                compare_key="trakt.auth",
                settings=[
                    ("trakt.auth", "token", False),
                    ("trakt.username", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                ],
            ),

            # Fen
            dict(
                display="Fen",
                addon_id="plugin.video.fen",
                required_attrs=["chk_fen", "chkset_fen", "path_fen"],
                patch=("path_fen", "fen_client", "fen_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.token", "token", False),
                    ("trakt.user", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                    ("trakt.indicators_active", "true", False),
                    ("watched_indicators", "1", False),
                ],
            ),

            # The Coalition
            dict(
                display="The Coalition",
                addon_id="plugin.video.coalition",
                required_attrs=["chk_coal", "chkset_coal", "path_coal"],
                patch=("path_coal", "coal_client", "coal_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.token", "token", False),
                    ("trakt_user", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                    ("trakt.indicators_active", "true", False),
                    ("watched_indicators", "1", False),
                ],
            ),

            # POV
            dict(
                display="POV",
                addon_id="plugin.video.pov",
                required_attrs=["chk_pov", "chkset_pov"],
                compare_key="trakt.token",
                settings=[
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                    ("trakt.token", "token", False),
                    ("trakt_user", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                    ("trakt_indicators_active", "true", False),
                    ("watched_indicators", "1", False),
                ],
            ),

            # Umbrella
            dict(
                display="Umbrella",
                addon_id="plugin.video.umbrella",
                required_attrs=["chk_umb", "chkset_umb"],
                compare_key="trakt.user.token",
                settings=[
                    ("trakt.user.name", "username", False),
                    ("trakt.user.token", "token", False),
                    ("trakt.refreshtoken", "refresh", False),
                    ("trakt.token.expires", "expires_raw", False),
                    ("traktuserkey.customenabled", "true", False),
                    ("trakt.clientid", "client_am", False),
                    ("trakt.clientsecret", "secret_am", False),
                    ("trakt.isauthed", "true", False),
                    ("trakt.indicators", "Trakt", False),
                    ("trakt.scrobble", "true", False),
                    ("resume.source", "1", False),
                ],
            ),

            # Infinity
            dict(
                display="Infinity",
                addon_id="plugin.video.infinity",
                required_attrs=["chk_infinity", "chkset_infinity"],
                compare_key="trakt.user.token",
                settings=[
                    ("trakt.user.name", "username", False),
                    ("trakt.user.token", "token", False),
                    ("trakt.refreshtoken", "refresh", False),
                    ("trakt.token.expires", "expires_raw", False),
                    ("traktuserkey.customenabled", "true", False),
                    ("trakt.clientid", "client_am", False),
                    ("trakt.clientsecret", "secret_am", False),
                    ("trakt.scrobble", "true", False),
                    ("resume.source", "1", False),
                ],
            ),

            # Dradis
            dict(
                display="Dradis",
                addon_id="plugin.video.dradis",
                required_attrs=["chk_dradis", "chkset_dradis"],
                compare_key="trakt.token",
                settings=[
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                    ("trakt.username", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                    ("trakt.isauthed", "true", False),
                ],
            ),

            # TMDb Helper (JSON blob)
            dict(
                display="TMDb Helper",
                addon_id="plugin.video.themoviedb.helper",
                required_attrs=["chk_tmdbh", "path_tmdbh"],
                preflight=("chk_tmdbh", "tmdbh_ud", "tmdbh", "chkset_tmdbh"),
                patch=("path_tmdbh", "tmdbh_client", "tmdbh_secret"),
                compare_key="trakt_token",
                compare_mode="contains",
                settings=[
                    ("trakt_token", "tmdbh_blob", True),
                    ("startup_notifications", "false", False),
                ],
            ),

            # Trakt Addon (JSON blob)
            dict(
                display="Trakt Addon",
                addon_id="script.trakt",
                required_attrs=["chk_trakt", "path_trakt"],
                preflight=("chk_trakt", "trakt_ud", "trakt", "chkset_trakt"),
                patch=("path_trakt", "trakt_client", "trakt_secret"),
                compare_key="authorization",
                compare_mode="contains",
                settings=[
                    ("user", "username", False),
                    ("authorization", "trakt_blob", False),
                ],
            ),

            # All Accounts
            dict(
                display="All Accounts",
                addon_id="script.module.allaccounts",
                required_attrs=["chk_allaccounts", "path_allaccounts"],
                preflight=("chk_allaccounts", "allaccounts_ud", "allaccounts", "chkset_allaccounts"),
                patch=("path_allaccounts", "allacts_client", "allacts_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.token", "token", False),
                    ("trakt.username", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                ],
            ),

            # My Accounts
            dict(
                display="My Accounts",
                addon_id="script.module.myaccounts",
                required_attrs=["chk_myaccounts", "path_myaccounts"],
                preflight=("chk_myaccounts", "myaccounts_ud", "myaccounts", "chkset_myaccounts"),
                patch=("path_myaccounts", "myacts_client", "myacts_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.token", "token", False),
                    ("trakt.username", "username", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.expires", "expires_raw", False),
                ],
            ),

            # Homelander
            dict(
                display="Homelander",
                addon_id="plugin.video.homelander",
                required_attrs=["chk_home"],
                preflight=("chk_home", "home_ud", "home", "chkset_home"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Quicksilver
            dict(
                display="Quicksilver",
                addon_id="plugin.video.quicksilver",
                required_attrs=["chk_quick"],
                preflight=("chk_quick", "quick_ud", "quick", "chkset_quick"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Absolution
            dict(
                display="Absolution",
                addon_id="plugin.video.absolution",
                required_attrs=["chk_absol"],
                preflight=("chk_absol", "absol_ud", "absol", "chkset_absol"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Shazam
            dict(
                display="Shazam",
                addon_id="plugin.video.shazam",
                required_attrs=["chk_shazam"],
                preflight=("chk_shazam", "shazam_ud", "shazam", "chkset_shazam"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Alvin
            dict(
                display="Alvin",
                addon_id="plugin.video.alvin",
                required_attrs=["chk_alvin"],
                preflight=("chk_alvin", "alvin_ud", "alvin", "chkset_alvin"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Moria
            dict(
                display="Moria",
                addon_id="plugin.video.moria",
                required_attrs=["chk_moria"],
                preflight=("chk_moria", "moria_ud", "moria", "chkset_moria"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Nine Lives
            dict(
                display="Nine Lives",
                addon_id="plugin.video.nine",
                required_attrs=["chk_nine"],
                preflight=("chk_nine", "nine_ud", "nine", "chkset_nine"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                    ("trakt.client_id", "client_am", False),
                    ("trakt.client_secret", "secret_am", False),
                ],
            ),

            # Chains Genocide (patch file + different keys)
            dict(
                display="Chains Genocide",
                addon_id="plugin.video.chainsgenocide",
                required_attrs=["chk_genocide", "path_genocide"],
                preflight=("chk_genocide", "genocide_ud", "genocide", "chkset_genocide"),
                patch=("path_genocide", "genocide_client", "genocide_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.username", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.isauthed", "true", False),
                ],
            ),

            # The Crew (patch file)
            dict(
                display="The Crew",
                addon_id="plugin.video.thecrew",
                required_attrs=["chk_crew", "path_crew"],
                preflight=("chk_crew", "crew_ud", "crew", "chkset_crew"),
                patch=("path_crew", "crew_client", "crew_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                ],
            ),

            # Scrubs V2 (patch file)
            dict(
                display="Scrubs V2",
                addon_id="plugin.video.scrubsv2",
                required_attrs=["chk_scrubs", "path_scrubs"],
                preflight=("chk_scrubs", "scrubs_ud", "scrubs", "chkset_scrubs"),
                patch=("path_scrubs", "scrubs_client", "scrubs_secret"),
                compare_key="trakt.token",
                settings=[
                    ("trakt.user", "username", False),
                    ("trakt.token", "token", False),
                    ("trakt.refresh", "refresh", False),
                    ("trakt.authed", "yes", False),
                ],
            ),
        ]

        # Access-token style addons (trakt_access_token / trakt_refresh_token / trakt_expires_at)
        access_style = [
            ("Shadow", "plugin.video.shadow", "chk_shadow", "shadow_ud", "shadow", "chkset_shadow", "path_shadow", "shadow_client", "shadow_secret"),
            ("Ghost", "plugin.video.ghost", "chk_ghost", "ghost_ud", "ghost", "chkset_ghost", "path_ghost", "ghost_client", "ghost_secret"),
            ("Base", "plugin.video.base", "chk_base", "base_ud", "base", "chkset_base", "path_base", "base_client", "base_secret"),
            ("Chain Reaction", "plugin.video.thechains", "chk_chains", "chains_ud", "chains", "chkset_chains", "path_chains", "chains_client", "chains_secret"),
            ("Asgard", "plugin.video.asgard", "chk_asgard", "asgard_ud", "asgard", "chkset_asgard", "path_asgard", "asgard_client", "asgard_secret"),
            ("Patriot", "plugin.video.patriot", "chk_patriot", "patriot_ud", "patriot", "chkset_patriot", "path_patriot", "patriot_client", "patriot_secret"),
            ("Black Lightning", "plugin.video.blacklightning", "chk_blackl", "blackl_ud", "blackl", "chkset_blackl", "path_blackl", "blackl_client", "blackl_secret"),
            ("Aliunde K19", "plugin.video.aliundek19", "chk_aliunde", "aliunde_ud", "aliunde", "chkset_aliunde", "path_aliunde", "aliunde_client", "aliunde_secret"),
            ("Nightwing Lite", "plugin.video.NightwingLite", "chk_night", "night_ud", "night", "chkset_night", "path_night", "night_client", "night_secret"),
        ]

        for disp, addon_id, chk, ud, src, dst, pth, phc, phs in access_style:
            targets.append(dict(
                display=disp,
                addon_id=addon_id,
                required_attrs=[chk, pth],
                preflight=(chk, ud, src, dst),
                patch=(pth, phc, phs),
                compare_key="trakt_access_token",
                settings=[
                    ("trakt_access_token", "token", False),
                    ("trakt_refresh_token", "refresh", False),
                    ("trakt_expires_at", "expires_raw", False),
                ],
            ))

        # ----- Execute -----
        for cfg in targets:
            if cfg["display"] in enabled:
                _sync(cfg, v)

        # Fen Light uses settings.db (handled via trakt_db)
        if "Fen Light" in enabled:
            try:
                if _exists_attr("chk_fenlt") and _exists_attr("chkset_fenlt"):
                    from accountmgr.modules.db import trakt_db
                    trakt_db.auth_fenlt_trakt()
                    try:
                        var.remake_settings()
                    except Exception:
                        pass
                    try:
                        from accountmgr.modules import control
                        control.fenlt_chk()
                    except Exception:
                        pass
            except Exception:
                _log("Fen Light Trakt sync failed", xbmc.LOGINFO)
                pass
