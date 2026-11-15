# -*- coding: utf-8 -*-
"""
	QR code image helper - builds a URL for a public QR-code rendering
	service so a Kodi image control can display it directly as a texture.
"""

import urllib.parse

QR_API = 'https://api.qrserver.com/v1/create-qr-code/?size=%dx%d&data=%s'


def qr_image_url(data, size=400):
	return QR_API % (size, size, urllib.parse.quote(data, safe=''))
