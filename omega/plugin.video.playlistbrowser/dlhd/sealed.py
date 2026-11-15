"""Decode sealed HLS segment references using the playlist token's playback key."""
import base64
import re
from urllib.parse import urlsplit

from dlhd.debuglog import LOG


def decode_base64(value):
    return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


def unseal(data, key_text):
    text = data.decode('utf-8-sig', 'replace')
    if not text.lstrip().startswith('#EXTM3U'):
        return data
    lines = text.splitlines()
    entries = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith('#')]
    if not entries or not all(re.fullmatch(r'[A-Za-z0-9_-]{80,}={0,2}', entry) for entry in entries):
        return data
    if not key_text:
        raise ValueError('Sealed playlist token did not include a playback key')
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            raise ValueError('Sealed playlist requires the Kodi PyCryptodome dependency')
    key = decode_base64(key_text)
    sequence_match = re.search(r'^#EXT-X-MEDIA-SEQUENCE:\s*(\d+)', text, re.M)
    sequence = int(sequence_match.group(1)) if sequence_match else 0
    for index, line in enumerate(lines):
        entry = line.strip()
        if not entry or entry.startswith('#'):
            continue
        cipher = AES.new(key, AES.MODE_CTR, nonce=b'\x00' * 8, initial_value=sequence)
        uri = cipher.decrypt(decode_base64(entry)).decode('utf-8')
        if not uri or any(ord(char) <= 32 for char in uri) or urlsplit(uri).scheme not in ('', 'http', 'https'):
            raise ValueError('Sealed playlist yielded an invalid segment URI')
        lines[index] = uri
        sequence += 1
    LOG.info('Sealed HLS playlist decoded')
    return ('\n'.join(lines) + '\n').encode('utf-8')
