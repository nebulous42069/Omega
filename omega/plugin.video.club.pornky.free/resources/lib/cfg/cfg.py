# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals

from resources.lib.cfg.filter import Filter
from resources.lib.cfg.res import Res


class Cfg:
    res = Res.MAX  # Res(0)
    filter = Filter.OFF  # Filter(1)
    cat = False
    filter_items = None
    search_items = None

    disable_login = False

    username = ''
    password = ''
    cookie_PHPSESSID = ''
