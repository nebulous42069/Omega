"""Render a private, locally generated QR code as a temporary PNG."""
import contextlib
import os
import struct
import tempfile
import zlib
from ._qrencoder import QRCode


def png_bytes(data):
    code = QRCode(border=4)
    code.add_data(data)
    matrix = code.get_matrix()
    scale = max(5, 600 // len(matrix))
    width = len(matrix) * scale
    rows = []
    for row in matrix:
        pixels = b''.join((b'\x00\x00\x00' if cell else b'\xff\xff\xff') * scale for cell in row)
        rows.extend([b'\x00' + pixels] * scale)
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, width, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


@contextlib.contextmanager
def temporary_qr(data):
    import xbmcvfs
    directory = xbmcvfs.translatePath('special://temp/')
    fd, path = tempfile.mkstemp(prefix='diggz_tmdb_qr_', suffix='.png', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(png_bytes(data))
        yield path.replace(os.sep, "/")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def qr_rectangles(data, left, top, size):
    """Return dark horizontal module runs, including a four-module quiet zone."""
    code = QRCode(border=4)
    code.add_data(data)
    matrix = code.get_matrix()
    scale = size // len(matrix)
    if scale < 1:
        raise ValueError('QR too large for display')
    offset = (size - scale * len(matrix)) // 2
    for y, row in enumerate(matrix):
        start = None
        for x, cell in enumerate(list(row) + [False]):
            if cell and start is None:
                start = x
            elif not cell and start is not None:
                yield (left + offset + start * scale, top + offset + y * scale,
                       (x - start) * scale, scale)
                start = None
