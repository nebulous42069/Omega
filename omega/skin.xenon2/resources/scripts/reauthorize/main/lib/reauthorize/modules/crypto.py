import base64
import hashlib
import hmac
import json
import os


def _keystream(key, nonce, length):
    stream, counter = b'', 0
    while len(stream) < length:
        stream += hmac.new(key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        counter += 1
    return stream[:length]


def encrypt_data(data, device_id):
    """
    Encrypt a dict to a base64 string.
    Key is derived from device_id via SHA-256. A random 16-byte nonce is
    prepended to the ciphertext so each backup produces a unique blob.
    """
    key = hashlib.sha256(device_id.encode()).digest()
    plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
    nonce = os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(plaintext, _keystream(key, nonce, len(plaintext))))
    return base64.b64encode(nonce + ct).decode()


def decrypt_data(encoded, device_id):
    """Decrypt a base64 string produced by encrypt_data back to a dict."""
    key = hashlib.sha256(device_id.encode()).digest()
    raw = base64.b64decode(encoded.encode())
    nonce, ct = raw[:16], raw[16:]
    plaintext = bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct))))
    return json.loads(plaintext.decode('utf-8'))
