# -*- coding: utf-8 -*-
"""
    ReAuthorize - comparing version numbers (1.4.1)

    The update check used to cut the installed version to its first five characters
    (addonVersion()[:5]), so '1.3.10' read as '1.3.1', and compared part by part over the
    installed version only, which crashed (silently) when the two had a different number of
    parts. Versions are compared as numbers here, any number of parts and digits.
"""

import re


def parts(version):
    """'1.4.10' -> (1, 4, 10). Text around the numbers ('1.4.0~beta') is ignored."""
    return tuple(int(n) for n in re.findall(r'\d+', str(version or '')))


def is_newer(installed, available):
    """True when `available` is a later version than `installed` ('1.4.0' < '1.4.10' < '1.5')."""
    a, b = parts(installed), parts(available)
    width = max(len(a), len(b))
    return b + (0,) * (width - len(b)) > a + (0,) * (width - len(a))


def status_line(installed, latest):
    """
    The 'ReAuthorize version' line on the first settings tab: the version that is running, and
    how it stands against the newest one the start-up check last saw in the repo ('' = not
    checked, or the check is switched off: then the version alone, with no claim either way).
    """
    installed = str(installed or '').strip()
    latest = str(latest or '').strip()
    if not installed or not parts(latest):
        return installed
    if is_newer(installed, latest):
        return '%s  (update available: %s)' % (installed, latest)
    return '%s  (latest)' % installed
