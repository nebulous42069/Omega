# Patched for Kodi addon: hardcoded version (no pip install / importlib.metadata available)
__title__ = "curl_cffi"
__description__ = "libcurl python binding, with impersonation support"
__version__ = "0.15.0"


def _resolve_curl_version() -> str:
    """Read libcurl version without creating a curl easy handle at import time."""
    from ._wrapper import ffi, lib

    return ffi.string(lib.curl_version()).decode()


# Kodi patch: do NOT call _resolve_curl_version() at import time.
# Calling it here triggers _wrapper import before _cffi_backend is registered.
__curl_version__ = "libcurl/8.15.0-IMPERSONATE BoringSSL"
