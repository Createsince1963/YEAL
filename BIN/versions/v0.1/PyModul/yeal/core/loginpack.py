"""Login pack (0.9.1.29): the logins of the admin area packed into ONE file that is encrypted with a password of your choice, so
it can be carried to another PC (on a stick, next to the exe) and opened there. No Qt, standard library only.

What is inside: the Tidal sign-in (tiddl's auth.json), the YouTube cookie file for downloads (cookies.txt, if one was chosen
in Settings) and the entries of the admin vault (service, user, password, note).
NOT inside: the sign-in of the embedded browser view - its cookies are locked to the Windows account of this PC (DPAPI) and
cannot be used on another one; sign in there once on the new PC.

Protection: the key is made from the password with PBKDF2-HMAC-SHA256 (random salt, 400,000 rounds) and split into an
encryption key and a MAC key. The data is encrypted with a stream made from HMAC-SHA256 in counter mode (random nonce) and
authenticated with HMAC-SHA256 over everything (encrypt-then-MAC): a wrong password or a changed file is recognised before
anything is decrypted. The pack is only as strong as its password (at least 10 characters are required).

File layout:  b"YEALPK1\\n" | salt 16 | nonce 16 | rounds (4 bytes) | ciphertext | MAC 32
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
import time
from typing import List

MAGIC = b"YEALPK1\n"
ROUNDS = 400_000
MIN_PASSWORD = 10
MAX_PACK = 4 * 1024 * 1024


class PackError(ValueError):
    """A message that can be shown to the user."""


def _keys(password: str, salt: bytes, rounds: int) -> tuple:
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds, dklen=64)
    return raw[:32], raw[32:]


def _stream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + struct.pack(">Q", counter), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def seal(payload: dict, password: str, rounds: int = ROUNDS) -> bytes:
    """The pack file content for `payload` (JSON-able dict)."""
    if len(password or "") < MIN_PASSWORD:
        raise PackError("The pack password needs at least %d characters." % MIN_PASSWORD)
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    salt, nonce = os.urandom(16), os.urandom(16)
    enc_key, mac_key = _keys(password, salt, rounds)
    cipher = bytes(a ^ b for a, b in zip(data, _stream(enc_key, nonce, len(data))))
    body = MAGIC + salt + nonce + struct.pack(">I", rounds) + cipher
    return body + hmac.new(mac_key, body, hashlib.sha256).digest()


def open_pack(blob: bytes, password: str) -> dict:
    """The payload of a pack, or PackError (wrong password and a damaged file give the same message)."""
    head = len(MAGIC) + 16 + 16 + 4
    if not blob.startswith(MAGIC) or len(blob) < head + 32 or len(blob) > MAX_PACK:
        raise PackError("This is not a Yeal login pack.")
    salt, nonce = blob[len(MAGIC):len(MAGIC) + 16], blob[len(MAGIC) + 16:len(MAGIC) + 32]
    rounds = struct.unpack(">I", blob[len(MAGIC) + 32:head])[0]
    if not 1000 <= rounds <= 5_000_000:
        raise PackError("This is not a Yeal login pack.")
    enc_key, mac_key = _keys(password or "", salt, rounds)
    body, mac = blob[:-32], blob[-32:]
    if not hmac.compare_digest(hmac.new(mac_key, body, hashlib.sha256).digest(), mac):
        raise PackError("Wrong password, or the file was changed.")
    cipher = body[head:]
    data = bytes(a ^ b for a, b in zip(cipher, _stream(enc_key, nonce, len(cipher))))
    try:
        payload = json.loads(data.decode("utf-8"))
    except ValueError:
        raise PackError("The pack could not be read.")
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise PackError("The pack comes from a newer Yeal.")
    return payload


def build_payload(tidal_auth_text: str, vault_entries: List[dict], yt_cookies: str = "") -> dict:
    return {"version": 1, "created": int(time.time()), "tidal_auth": tidal_auth_text or "", "yt_cookies": yt_cookies or "",
            "vault": [{k: str(e.get(k, "")) for k in ("service", "user", "password", "note")} for e in vault_entries or []]}
