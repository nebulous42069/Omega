"""
Account Manager credential sync for Seren.

Account Manager (script.module.accountmgr) already knows Seren's setting key
names and can write to them correctly.  It fails silently for two reasons:

  1. Race condition: AM checks xbmcvfs.exists(settings.xml) before writing.
     On a fresh install Seren's settings.xml may not exist yet when AM runs,
     so AM skips Seren entirely.  This module runs before Seren's settings
     pre-warm and reads FROM AM rather than waiting for AM to push to Seren,
     bypassing the race condition entirely.

  2. Missing service coverage: AM 2.6.6 has no TorBox→Seren sync and no
     Debrid-Link sync module at all.  This module fills both gaps.

Strategy: pull-not-push.  We read AM's own settings (the canonical store),
fall back to sibling addons if AM has no token, and write into Seren's
settings only when Seren's setting is currently empty.  A token that is
already set in Seren is never overwritten — so manual auth inside Seren
always takes precedence.

Confirmed key names (from AM 2.6.6 source, acctview 2.5.0, and sibling addon source):

  Service  AM internal key          Seren key            Notes
  -------  -----------------------  -------------------  ----------------------
  RD       realdebrid.token         rd.auth
           realdebrid.refresh       rd.refresh
           realdebrid.client_id     rd.client_id
           realdebrid.secret        rd.secret
           realdebrid.username      rd.username
  AD       alldebrid.token          alldebrid.apikey     key names differ!
           alldebrid.username       alldebrid.username
  PM       premiumize.token         premiumize.token     same key name
           premiumize.username      premiumize.username
  TB       torbox.token             torbox.token         AM has no Seren sync
           torbox.acct_id           torbox.username      acctview tbit.py used
  DL       debridlink.token         debridlink.token     AM has no sync module
           debridlink.refresh       debridlink.refresh   Otaku only

Sibling addon fallback key names (confirmed from source):

  Service  plugin.video.pov  plugin.video.otaku.testing  plugin.video.dradis
  -------  ----------------  --------------------------  -------------------
  RD       rd.token          realdebrid.token            rd.auth
  AD       ad.token          alldebrid.token             ad.token
  PM       pm.token          premiumize.token            pm.token
  TB       tb.token          torbox.token                torbox.token
  DL       (no DL support)   debridlink.token            debridlink.token
"""

import json

import xbmcaddon
import xbmcgui

from resources.lib.modules.globals import g

_AM = "script.module.accountmgr"

# The 5 service enabled-flag settings and their short labels for logging
_ENABLED_FLAGS = {
    "realdebrid.enabled": "RD",
    "premiumize.enabled": "PM",
    "alldebrid.enabled":  "AD",
    "torbox.enabled":     "TB",
    "debridlink.enabled": "DL",
}
_SNAPSHOT_PROPERTY = "seren.user_enabled_snapshot"


def snapshot_enabled_flags():
    """
    Snapshot the user's intended enabled/disabled state for all 5 debrid services.
    Must be called at startup BEFORE Account Manager has a chance to overwrite
    these flags in Seren's settings.xml.

    Account Manager (debrid_pm.py / torbox_sync.py) calls setSetting('*.enabled', 'true')
    on Seren directly during its own startup sync — this re-enables services the user
    has intentionally disabled in Seren.  protect_enabled_flags() uses this snapshot
    to restore the user's intent after AM has run.
    """
    try:
        addon = xbmcaddon.Addon("plugin.video.seren")
        snapshot = {key: addon.getSetting(key) for key in _ENABLED_FLAGS}
        xbmcgui.Window(10000).setProperty(_SNAPSHOT_PROPERTY, json.dumps(snapshot))
        disabled = [lbl for key, lbl in _ENABLED_FLAGS.items() if snapshot.get(key) == "false"]
        if disabled:
            g.log(f"AccountMgrSync: snapshot — user has disabled: {', '.join(disabled)}", "info")
        else:
            g.log("AccountMgrSync: snapshot — all services enabled by user", "debug")
    except Exception as e:
        g.log(f"AccountMgrSync: snapshot_enabled_flags failed: {e}", "warning")


def protect_enabled_flags():
    """
    Restore any enabled flags that Account Manager re-enabled against the user's intent.
    Call after the startup delay that allows Account Manager to finish its own sync.

    For each service the user had set to disabled (snapshot value == 'false'), if
    Account Manager has since flipped it to 'true', we force it back to 'false'.
    """
    try:
        raw = xbmcgui.Window(10000).getProperty(_SNAPSHOT_PROPERTY)
        if not raw:
            g.log("AccountMgrSync: protect — no snapshot found, skipping", "warning")
            return
        snapshot = json.loads(raw)
        restored = []
        for key, label in _ENABLED_FLAGS.items():
            if snapshot.get(key) == "false" and g.get_bool_setting(key):
                g.set_setting(key, "false")
                restored.append(label)
                g.log(
                    f"AccountMgrSync: protect — restored {label} {key}=false "
                    f"(Account Manager had re-enabled it)",
                    "info",
                )
        if not restored:
            g.log("AccountMgrSync: protect — no flags needed restoring", "debug")
    except Exception as e:
        g.log(f"AccountMgrSync: protect_enabled_flags failed: {e}", "warning")


def _get(addon_id, key):
    """Read a setting from an addon. Returns the value or None if absent/empty."""
    try:
        v = xbmcaddon.Addon(addon_id).getSetting(key)
        return v if v else None
    except Exception:
        return None


def _first(*candidates):
    """Return the first non-empty value from (addon_id, key) pairs."""
    for addon_id, key in candidates:
        v = _get(addon_id, key)
        if v:
            return v
    return None


def _put(seren_key, value, label):
    """
    Write value to Seren's setting only if currently empty.
    Returns True if a write was performed.
    """
    if not value:
        return False
    if g.get_setting(seren_key):
        g.log(f"AccountMgrSync: {label} {seren_key} already set — skipped", "debug")
        return False
    g.set_setting(seren_key, value)
    g.log(f"AccountMgrSync: {label} populated {seren_key}", "info")
    return True


def _enable(seren_key, label):
    """Set a boolean enabled flag to 'true' unless user has explicitly disabled it."""
    if g.get_setting(seren_key) != "false":
        g.set_setting(seren_key, "true")
        g.log(f"AccountMgrSync: {label} enabled {seren_key}", "info")


def sync_accountmgr_credentials():
    """
    Pull debrid credentials from Account Manager and sibling addons into Seren.

    Called once at service startup, before settings are pre-warmed.
    Never overwrites a setting that already has a value.
    """
    synced = []

    # ------------------------------------------------------------------ #
    #  Real-Debrid
    #  AM internal key: realdebrid.token  →  Seren: rd.auth
    # ------------------------------------------------------------------ #
    rd_token = _first(
        (_AM,                           "realdebrid.token"),
        ("plugin.video.otaku.testing",  "realdebrid.token"),
        ("plugin.video.pov",            "rd.token"),
        ("plugin.video.dradis",         "rd.auth"),
        ("plugin.video.umbrella",       "rd.auth"),
    )
    if _put("rd.auth", rd_token, "RD"):
        synced.append("RD")
        _put("rd.refresh", _first(
            (_AM,                          "realdebrid.refresh"),
            ("plugin.video.otaku.testing", "realdebrid.refresh"),
            ("plugin.video.pov",           "rd.refresh"),
            ("plugin.video.dradis",        "rd.refresh"),
        ), "RD")
        _put("rd.client_id", _first(
            (_AM,                          "realdebrid.client_id"),
            ("plugin.video.otaku.testing", "realdebrid.client_id"),
            ("plugin.video.pov",           "rd.client_id"),
        ), "RD")
        _put("rd.secret", _first(
            (_AM,                          "realdebrid.secret"),
            ("plugin.video.otaku.testing", "realdebrid.secret"),
            ("plugin.video.pov",           "rd.secret"),
        ), "RD")
        _put("rd.username", _first(
            (_AM,                          "realdebrid.username"),
            ("plugin.video.otaku.testing", "realdebrid.username"),
            ("plugin.video.pov",           "rd.username"),
        ), "RD")
        _put("rd.premiumstatus", "Premium", "RD")
        _enable("realdebrid.enabled", "RD")

    # ------------------------------------------------------------------ #
    #  AllDebrid
    #  AM internal key: alldebrid.token  →  Seren: alldebrid.apikey
    #  Key names differ — this is the most common sync failure point.
    # ------------------------------------------------------------------ #
    ad_token = _first(
        (_AM,                           "alldebrid.token"),
        ("plugin.video.otaku.testing",  "alldebrid.token"),
        ("plugin.video.pov",            "ad.token"),
        ("plugin.video.dradis",         "ad.token"),
        ("plugin.video.umbrella",       "ad.token"),
    )
    if _put("alldebrid.apikey", ad_token, "AD"):
        synced.append("AD")
        _put("alldebrid.username", _first(
            (_AM,                          "alldebrid.username"),
            ("plugin.video.otaku.testing", "alldebrid.username"),
        ), "AD")
        _put("alldebrid.premiumstatus", "Premium", "AD")
        _enable("alldebrid.enabled", "AD")

    # ------------------------------------------------------------------ #
    #  Premiumize
    #  AM internal key: premiumize.token  →  Seren: premiumize.token (same)
    # ------------------------------------------------------------------ #
    pm_token = _first(
        (_AM,                           "premiumize.token"),
        ("plugin.video.otaku.testing",  "premiumize.token"),
        ("plugin.video.pov",            "pm.token"),
        ("plugin.video.dradis",         "pm.token"),
        ("plugin.video.umbrella",       "premiumize.token"),
    )
    if _put("premiumize.token", pm_token, "PM"):
        synced.append("PM")
        _put("premiumize.username", _first(
            (_AM,                          "premiumize.username"),
            ("plugin.video.otaku.testing", "premiumize.username"),
        ), "PM")
        _put("premiumize.premiumstatus", "Premium", "PM")
        _enable("premiumize.enabled", "PM")

    # ------------------------------------------------------------------ #
    #  TorBox
    #  AM internal key: torbox.token  →  Seren: torbox.token (same)
    #  AM has no Seren TorBox sync — confirmed from torbox_sync.py source.
    #  acctview 2.5.0 tbit.py confirms Seren keys:
    #    torbox.token, torbox.username, torbox.enabled, torbox.premiumstatus
    # ------------------------------------------------------------------ #
    tb_token = _first(
        (_AM,                           "torbox.token"),
        ("plugin.video.otaku.testing",  "torbox.token"),
        ("plugin.video.pov",            "tb.token"),
        ("plugin.video.dradis",         "torbox.token"),
    )
    if _put("torbox.token", tb_token, "TB"):
        synced.append("TB")
        # AM stores as torbox.acct_id; Seren uses torbox.username
        _put("torbox.username", _first(
            (_AM,                          "torbox.acct_id"),
            ("plugin.video.otaku.testing", "torbox.username"),
        ), "TB")
        _put("torbox.premiumstatus", "Premium", "TB")
        _enable("torbox.enabled", "TB")

    # ------------------------------------------------------------------ #
    #  Debrid-Link
    #  AM stores debridlink.token (confirmed: acctview 2.5.0 var.py line 94)
    #  but AM 2.6.6 has NO DL sync module — never writes to any addon.
    #  Seren key: debridlink.token (same across AM, Otaku, Dradis, Umbrella)
    # ------------------------------------------------------------------ #
    dl_token = _first(
        (_AM,                           "debridlink.token"),
        ("plugin.video.otaku.testing",  "debridlink.token"),
        ("plugin.video.dradis",         "debridlink.token"),
        ("plugin.video.umbrella",       "debridlink.token"),
    )
    if _put("debridlink.token", dl_token, "DL"):
        synced.append("DL")
        # Only Otaku stores the refresh token for DL
        _put("debridlink.refresh", _first(
            ("plugin.video.otaku.testing", "debridlink.refresh"),
        ), "DL")
        _enable("debridlink.enabled", "DL")

    # ------------------------------------------------------------------ #
    #  Summary
    # ------------------------------------------------------------------ #
    if synced:
        g.log(
            f"AccountMgrSync: synced {', '.join(synced)} from Account Manager / sibling addons",
            "info",
        )
    else:
        g.log("AccountMgrSync: all credentials already present in Seren — nothing to sync", "info")
