"""Decode upstream image wrappers without relying on the HTTP content type."""
import struct
import zlib

MAX_DECODED = 64 * 1024 * 1024


def inflate(data, gzip=False):
    decoder = zlib.decompressobj(31 if gzip else 15)
    result = decoder.decompress(data, MAX_DECODED + 1)
    if len(result) > MAX_DECODED or decoder.unconsumed_tail or not decoder.eof:
        raise ValueError('Wrapped segment is oversized or incomplete')
    return result


def ts(data):
    return len(data) >= 376 and data[0] == 71 and data[188] == 71


def paeth(a, b, c):
    p = a + b - c
    distances = (abs(p-a), abs(p-b), abs(p-c))
    return (a,b,c)[distances.index(min(distances))]


def png_payload(data):
    pos, width, height, bpp = 8, 0, 0, 0
    compressed = []
    while pos + 12 <= len(data):
        size = int.from_bytes(data[pos:pos+4], 'big')
        end = pos + size + 12
        if end > len(data):
            raise ValueError('Truncated PNG segment wrapper')
        kind, payload = data[pos+4:pos+8], data[pos+8:pos+8+size]
        if kind == b'IHDR':
            if len(payload) != 13:
                raise ValueError('Invalid PNG wrapper header')
            width,height,depth,color,compression,filtering,interlace = struct.unpack('>IIBBBBB', payload)
            if depth != 8 or color not in (2,6) or compression or filtering or interlace:
                raise ValueError('Unsupported PNG wrapper pixel format')
            bpp = 3 if color == 2 else 4
            if not width or not height or (width*bpp+1)*height > MAX_DECODED:
                raise ValueError('PNG wrapper dimensions exceed limit')
        elif kind == b'IDAT':
            compressed.append(payload)
        elif kind == b'IEND':
            if ts(data[end:]):
                return data[end:]
            break
        pos = end
    if not width or not bpp:
        raise ValueError('PNG wrapper has no valid header')
    raw = inflate(b''.join(compressed))
    stride = width*bpp
    if len(raw) != (stride+1)*height:
        raise ValueError('PNG wrapper pixel data has invalid size')
    rgb = bytearray()
    previous = bytearray(stride)
    source = 0
    for _ in range(height):
        mode = raw[source]
        source += 1
        if mode > 4:
            raise ValueError('Invalid PNG wrapper filter')
        row = bytearray(raw[source:source+stride])
        for i in range(stride) if mode else ():
            a = row[i-bpp] if i >= bpp else 0
            b = previous[i]
            c = previous[i-bpp] if i >= bpp else 0
            if mode == 1:
                prediction = a
            elif mode == 2:
                prediction = b
            elif mode == 3:
                prediction = (a+b)//2
            else:
                prediction = paeth(a,b,c)
            row[i] = (raw[source+i]+prediction)&255
        source += stride
        if bpp == 3:
            rgb.extend(row)
        else:
            for i in range(0,stride,4):
                rgb.extend(row[i:i+3])
        previous = row
    if rgb[:8] != b'TIKTIKPX' or len(rgb) < 12:
        raise ValueError('PNG wrapper is missing the expected pixel payload marker')
    size = int.from_bytes(rgb[8:12], 'big')
    if not size or size > len(rgb)-12:
        raise ValueError('PNG wrapper pixel payload length is invalid')
    return inflate(bytes(rgb[12:12+size]), gzip=True)


def unwrap(data):
    if ts(data):
        return data
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        result = png_payload(data)
        if not ts(result):
            raise ValueError('Decoded PNG payload is not MPEG-TS')
        return result
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        pos = 12
        while pos+8 <= len(data):
            size = int.from_bytes(data[pos+4:pos+8], 'little')
            end = pos+8+size
            if end > len(data):
                raise ValueError('Truncated WebP segment wrapper')
            if data[pos:pos+4] == b'EXIF' and ts(data[pos+8:end]):
                return data[pos+8:end]
            pos = end+(size&1)
        raise ValueError('WebP wrapper contains no MPEG-TS payload')
    for marker in (b'TIKTIKRAW',b'TIKTIKTSGZ'):
        if marker in data:
            payload = data.split(marker,1)[1]
            result = inflate(payload,gzip=True) if marker.endswith(b'GZ') else payload
            if not ts(result):
                raise ValueError('Wrapped payload is not MPEG-TS')
            return result
    return data
