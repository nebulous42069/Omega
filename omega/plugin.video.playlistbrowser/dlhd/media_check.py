"""Structural media checks, not a substitute for decoding in Kodi."""
import struct


def validate_ts(data):
    if len(data) < 188 or len(data) % 188:
        raise ValueError('MPEG-TS sample has incomplete packets')
    video_pids = set()
    payload_bytes = 0
    for offset in range(0, len(data), 188):
        packet = data[offset:offset + 188]
        if packet[0] != 0x47:
            raise ValueError('MPEG-TS packet synchronization failed')
        if packet[1] & 0x80:  # transport_error_indicator
            continue
        pid = ((packet[1] & 31) << 8) | packet[2]
        if pid == 8191 or packet[3] & 0xc0:  # null or scrambled
            continue
        control = (packet[3] >> 4) & 3
        if control not in (1, 3):
            continue
        start = 4 if control == 1 else 5 + packet[4]
        if start >= 188:
            continue
        payload = packet[start:]
        if packet[1] & 0x40:
            video_pids.discard(pid)
            if payload[:3] == b'\x00\x00\x01' and len(payload) >= 9 and 0xe0 <= payload[3] <= 0xef:
                video_pids.add(pid)
                payload = payload[9 + payload[8]:]
        if pid in video_pids:
            payload_bytes += len(payload)
    if payload_bytes < 2048:
        raise ValueError('MPEG-TS sample lacks substantial video PES payload')
    return payload_bytes


def validate_mp4(data, initialization=False):
    offset = 0
    media = 0
    init = False
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from('>I4s', data, offset)
        header = 8
        if size == 1:
            if offset + 16 > len(data):break
            size = struct.unpack_from('>Q', data, offset + 8)[0]
            header = 16
        elif size == 0:size = len(data) - offset
        if size < header or offset + size > len(data):
            raise ValueError('MP4 sample has an incomplete box')
        if kind == b'mdat':media += size - header
        if kind == b'moov':init = True
        offset += size
    if offset != len(data) or (not initialization and media < 2048) or (initialization and not init):
        raise ValueError('MP4 sample lacks required initialization or media payload')
    return media


def validate_media(data, encrypted=False):
    if encrypted:
        # Ciphertext cannot be inspected for video without a decryptor.
        if len(data) < 2048 or len(data) % 16 or data.lstrip().startswith(b'<'):
            raise ValueError('Encrypted media sample is too small or malformed')
        return 'encrypted'
    if data[:1] == b'G':
        validate_ts(data)
        return 'mpeg-ts'
    validate_mp4(data)
    return 'mp4'
