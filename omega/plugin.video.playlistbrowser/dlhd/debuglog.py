"""Bounded local diagnostics; never include upstream paths, query strings or bodies."""
import logging
from logging.handlers import RotatingFileHandler
import os
import re
from urllib.error import HTTPError, URLError

LOG = logging.getLogger('dlhd.export')
LOG.addHandler(logging.NullHandler())


def setup(folder):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'debug.log')
    for existing in list(LOG.handlers):
        if isinstance(existing, RotatingFileHandler):
            LOG.removeHandler(existing)
            existing.close()
    handler = RotatingFileHandler(path, maxBytes=512 * 1024, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    LOG.addHandler(handler)
    return path


def reason(error):
    if isinstance(error, HTTPError):
        return 'HTTP {}'.format(error.code)
    if isinstance(error, URLError):
        return 'Network error ({})'.format(type(error.reason).__name__)
    if isinstance(error, ValueError):
        # Only internally defined messages are useful. Remove any accidental URLs.
        return re.sub(r'https?://[^\s]+', '[URL removed]', str(error))[:240]
    return type(error).__name__
