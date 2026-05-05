import xbmcgui


BUFFER_SIZE_MAP = {
    "0": 64,
    "1": 128,
    "2": 256,
    "3": 512,
}

BUFFER_LABEL_MAP = {
    "0": "small",
    "1": "medium",
    "2": "large",
    "3": "very large",
}


def _safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _get_selected_account(ADDON) -> str:
    value = str(ADDON.getSetting("account")).strip()
    return value if value in ("0", "1", "2") else "0"


def _get_account_suffix(ADDON, account_override=None) -> str:
    selected = (
        str(account_override).strip()
        if account_override is not None
        else _get_selected_account(ADDON)
    )

    if selected == "1":
        return "1"
    if selected == "2":
        return "2"
    return ""


def _get_account_setting(
    ADDON, base_key: str, default: str = "", account_override=None
) -> str:
    suffix = _get_account_suffix(ADDON, account_override)
    value = ADDON.getSetting(f"{base_key}{suffix}")
    if isinstance(value, str):
        value = value.strip()
    return value if value else default


def _get_enum_enabled(ADDON, setting_id: str) -> bool:
    return str(ADDON.getSetting(setting_id)).strip() == "0"


def get_api_credentials(ADDON):
    server = _get_account_setting(ADDON, "server")
    username = _get_account_setting(ADDON, "username")
    password = _get_account_setting(ADDON, "password")

    if not (server and username and password):
        xbmcgui.Dialog().ok(
            ADDON.getAddonInfo("name"),
            "Please configure your IPTV credentials in the add-on settings.",
        )
        return None, None, None

    return server, username, password


def get_cache_on_off(ADDON):
    return _get_enum_enabled(ADDON, "cache")


def get_buffer_size(ADDON):
    value = _get_account_setting(ADDON, "buffer_size", "0")
    return BUFFER_SIZE_MAP.get(value, 64)


def get_buffer_size_label(ADDON):
    value = _get_account_setting(ADDON, "buffer_size", "0")
    return BUFFER_LABEL_MAP.get(value, "small")


def get_epg_offset(ADDON):
    return _safe_int(_get_account_setting(ADDON, "epg_offset", "0"), 0)


def get_catchup_offset(ADDON):
    return _safe_int(_get_account_setting(ADDON, "catchup_offset", "0"), 0)


def get_epg_url(ADDON):
    return _get_account_setting(ADDON, "epg_url", "")


def get_stream_format(ADDON):
    value = _get_account_setting(ADDON, "stream_format", "0")
    return {
        "0": "auto",
        "1": "ts",
        "2": "m3u8",
    }.get(value, "auto")
