import sys
from urllib.parse import parse_qsl

from resources.lib.kodi_compat import get_addon, log, set_setting_string
from resources.lib.pairing_flow import pairing_entrypoint
from resources.lib.sync_engine import manual_sync_entrypoint


def _query_params():
    raw_query = ""
    if len(sys.argv) > 2:
        raw_query = (sys.argv[2] or "").lstrip("?")
    return dict(parse_qsl(raw_query))


def run():
    addon = get_addon()
    params = _query_params()
    action = params.get("action", "")
    log("Plugin route invoked: %s" % (action or "<none>"), addon=addon)

    if action == "pair_google_drive":
        set_setting_string(addon, "pair_on_next_startup", "false")
        pairing_entrypoint()
        return
    if action == "sync_now":
        manual_sync_entrypoint()
        return

    log("Unknown plugin action: %s" % (action or "<none>"), level="warning", addon=addon)


if __name__ == "__main__":
    run()
