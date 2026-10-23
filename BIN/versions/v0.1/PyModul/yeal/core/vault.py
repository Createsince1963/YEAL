"""Admin vault: account logins stored encrypted and locked with an admin password (no Qt imports).

Protection, two layers:
  1. Admin password -> PBKDF2-HMAC-SHA256 (salt, 300k rounds). Only a verifier hash is stored, never the password.
  2. The entries are encrypted with Windows DPAPI (bound to the Windows user account) and the key derived from
     the admin password is used as DPAPI "entropy" - so the file is useless on another PC/account and without
     the password.
Yeal never sees your Google password: sign-ins done in the browser view stay in the browser profile. The vault
holds entries you add yourself (service, user, password, note).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Optional, Protocol

ITERATIONS = 300_000
# Initial admin password: a neutral, publicly known placeholder (the user is asked to change it). A personal
# initial password is NOT kept in the source: put it in the environment variable YEAL_ADMIN_DEFAULT or in the
# file `admin_default.txt` next to vault.json (first line) - both stay out of the repository.
DEFAULT_PASSWORD = os.environ.get("YEAL_ADMIN_DEFAULT") or "change-me-yeal"
MAX_FIELD = 2000
MAX_ENTRIES = 500


class Unavailable(RuntimeError):
    pass


class Cipher(Protocol):
    def encrypt(self, data: bytes, entropy: bytes) -> bytes: ...
    def decrypt(self, data: bytes, entropy: bytes) -> bytes: ...


class DpapiCipher:
    """Windows Data Protection API through ctypes (no extra package)."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise Unavailable("The vault needs Windows (DPAPI).")

    @staticmethod
    def _call(fn_name: str, data: bytes, entropy: bytes) -> bytes:
        import ctypes
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        def make(b: bytes):
            buf = ctypes.create_string_buffer(b, len(b))
            return Blob(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

        inb, keep1 = make(data)
        ent, keep2 = make(entropy)
        out = Blob()
        crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32   # type: ignore[attr-defined]
        fn = getattr(crypt32, fn_name)
        ok = fn(ctypes.byref(inb), None, ctypes.byref(ent), None, None, 0, ctypes.byref(out))
        if not ok:
            raise Unavailable("Windows could not process the vault (%s)." % fn_name)
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            kernel32.LocalFree(out.pbData)
            del keep1, keep2

    def encrypt(self, data: bytes, entropy: bytes) -> bytes:
        return self._call("CryptProtectData", data, entropy)

    def decrypt(self, data: bytes, entropy: bytes) -> bytes:
        return self._call("CryptUnprotectData", data, entropy)


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=64)


class Vault:
    def __init__(self, path: Path, cipher: Optional[Cipher] = None, clock=time.monotonic) -> None:
        self.path = Path(path)
        self._cipher = cipher if cipher is not None else DpapiCipher()
        self._clock = clock
        self._key: Optional[bytes] = None        # derived key while unlocked
        self._entries: list = []
        self._fails = 0
        self._locked_until = 0.0
        self._default = self._local_default()
        if not self.path.exists():
            self._create(self._default)

    # ---- file ---------------------------------------------------------------------------------
    def _local_default(self) -> str:
        """The initial password of this installation: admin_default.txt next to the vault, else the placeholder."""
        try:
            first = (self.path.with_name("admin_default.txt").read_text(encoding="utf-8").splitlines() or [""])[0].strip()
        except OSError:
            first = ""
        return first or DEFAULT_PASSWORD

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, salt: bytes, key: bytes, entries: list, default: bool) -> None:
        blob = self._cipher.encrypt(json.dumps(entries).encode("utf-8"), key[32:])
        doc = {"v": 1, "salt": base64.b64encode(salt).decode(), "verify": base64.b64encode(key[:32]).decode(),
               "default": default, "data": base64.b64encode(blob).decode()}
        tmp = self.path.with_suffix(".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(doc), encoding="utf-8")
        os.replace(tmp, self.path)

    def _create(self, password: str) -> None:
        salt = secrets.token_bytes(16)
        self._write(salt, _derive(password, salt), [], default=(password == self._default))

    # ---- state --------------------------------------------------------------------------------
    @property
    def unlocked(self) -> bool:
        return self._key is not None

    def uses_default_password(self) -> bool:
        try:
            return bool(self._read().get("default"))
        except (OSError, ValueError):
            return False

    def wait_seconds(self) -> int:
        return max(0, int(self._locked_until - self._clock() + 0.999))

    def unlock(self, password: str) -> bool:
        if self.wait_seconds() > 0:
            return False
        try:
            doc = self._read()
            salt = base64.b64decode(doc["salt"])
            key = _derive(password, salt)
            if not hmac.compare_digest(key[:32], base64.b64decode(doc["verify"])):
                self._fails += 1
                if self._fails >= 5:        # slow down guessing
                    self._locked_until = self._clock() + min(300, 15 * 2 ** (self._fails - 5))
                return False
            self._entries = json.loads(self._cipher.decrypt(base64.b64decode(doc["data"]), key[32:]).decode("utf-8"))
        except (OSError, ValueError, KeyError):
            return False
        self._fails = 0
        self._key = key
        return True

    def lock(self) -> None:
        self._key = None
        self._entries = []

    # ---- entries (only while unlocked) --------------------------------------------------------
    def _need(self) -> bytes:
        if self._key is None:
            raise PermissionError("locked")
        return self._key

    def _save(self) -> None:
        doc = self._read()
        self._write(base64.b64decode(doc["salt"]), self._need(), self._entries, bool(doc.get("default")))

    def entries(self, with_secret: bool = False) -> list:
        self._need()
        return [dict(e) if with_secret else {k: v for k, v in e.items() if k != "password"}
                for e in self._entries]

    def password_of(self, entry_id: str) -> str:
        self._need()
        for e in self._entries:
            if e["id"] == entry_id:
                return str(e.get("password", ""))
        return ""

    def save_entry(self, entry: dict) -> str:
        """Add (no id) or update (id). Returns the entry id."""
        self._need()
        clean = {k: str(entry.get(k, ""))[:MAX_FIELD] for k in ("service", "user", "password", "note")}
        if not clean["service"].strip():
            raise ValueError("Please enter a service name.")
        eid = str(entry.get("id") or "")
        for e in self._entries:
            if e["id"] == eid:
                if not clean["password"]:       # edit without retyping the secret keeps it
                    clean["password"] = e.get("password", "")
                e.update(clean)
                break
        else:
            if len(self._entries) >= MAX_ENTRIES:
                raise ValueError("The vault is full.")
            eid = uuid.uuid4().hex[:12]
            self._entries.append({"id": eid, **clean})
        self._save()
        return eid

    def delete_entry(self, entry_id: str) -> None:
        self._need()
        self._entries = [e for e in self._entries if e["id"] != entry_id]
        self._save()

    def change_password(self, old: str, new: str) -> str:
        """Returns an error text or ''."""
        if len(new) < 8:
            return "The new password needs at least 8 characters."
        if new in (DEFAULT_PASSWORD, self._default):
            return "Please choose a different password than the default."
        if not self.unlocked and not self.unlock(old):
            return "The current password is wrong."
        doc = self._read()
        if not hmac.compare_digest(_derive(old, base64.b64decode(doc["salt"]))[:32], base64.b64decode(doc["verify"])):
            return "The current password is wrong."
        salt = secrets.token_bytes(16)
        key = _derive(new, salt)
        self._write(salt, key, self._entries, default=False)
        self._key = key
        return ""
