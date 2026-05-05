import threading
import xbmc
from resources.utils import settings
import xbmcaddon

from resources.lib.proxy.proxy_server import IPTVStreamProxy

ADDON = xbmcaddon.Addon()
_proxy = None
_port = None
_lock = threading.Lock()


def ensure_proxy_running():
    global _proxy, _port

    current_buffer = settings.get_buffer_size(ADDON)

    with _lock:
        if _proxy is None:
            _proxy = IPTVStreamProxy(ADDON, host="127.0.0.1", port=0)
            _proxy._last_buffer = current_buffer
            _port = _proxy.start()

        elif getattr(_proxy, "_last_buffer", None) != current_buffer:
            xbmc.log("Buffer size changed → restarting proxy", xbmc.LOGINFO)

            _proxy.stop()
            _proxy = IPTVStreamProxy(ADDON, host="127.0.0.1", port=0)
            _proxy._last_buffer = current_buffer
            _port = _proxy.start()

    return _port
