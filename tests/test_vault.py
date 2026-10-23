import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core.vault import DEFAULT_PASSWORD, Vault


class FakeCipher:
    """Stand-in for DPAPI (Windows only): reversible, bound to the entropy like the real one."""
    def encrypt(self, data, entropy):
        return entropy[:4] + bytes(b ^ 0x5A for b in data)

    def decrypt(self, data, entropy):
        if data[:4] != entropy[:4]:
            raise ValueError("wrong entropy")
        return bytes(b ^ 0x5A for b in data[4:])


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "vault.json"
        self.now = [0.0]
        self.v = Vault(self.path, FakeCipher(), clock=lambda: self.now[0])

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_password_and_no_plaintext(self):
        self.assertTrue(self.v.uses_default_password())
        self.assertFalse(self.v.unlock("wrong"))
        self.assertTrue(self.v.unlock(DEFAULT_PASSWORD))
        self.v.save_entry({"service": "YouTube", "user": "me@example.com", "password": "s3cret-pw"})
        raw = self.path.read_text()
        self.assertNotIn("s3cret-pw", raw)
        self.assertNotIn("me@example.com", raw)
        self.assertNotIn(DEFAULT_PASSWORD, raw)

    def test_entries_roundtrip_and_secret_hidden(self):
        self.v.unlock(DEFAULT_PASSWORD)
        eid = self.v.save_entry({"service": "A", "user": "u", "password": "p"})
        self.assertNotIn("password", self.v.entries()[0])
        self.assertEqual(self.v.password_of(eid), "p")
        self.v.save_entry({"id": eid, "service": "A2", "user": "u", "password": ""})   # keeps the secret
        self.assertEqual(self.v.password_of(eid), "p")
        other = Vault(self.path, FakeCipher())
        self.assertTrue(other.unlock(DEFAULT_PASSWORD))
        self.assertEqual(other.entries()[0]["service"], "A2")
        self.v.delete_entry(eid)
        self.assertEqual(self.v.entries(), [])

    def test_locked_vault_refuses(self):
        with self.assertRaises(PermissionError):
            self.v.entries()
        self.v.unlock(DEFAULT_PASSWORD)
        self.v.lock()
        with self.assertRaises(PermissionError):
            self.v.save_entry({"service": "x"})

    def test_change_password(self):
        self.v.unlock(DEFAULT_PASSWORD)
        self.v.save_entry({"service": "A", "password": "p"})
        self.assertIn("8 characters", self.v.change_password(DEFAULT_PASSWORD, "short"))
        self.assertIn("default", self.v.change_password(DEFAULT_PASSWORD, DEFAULT_PASSWORD))
        self.assertIn("wrong", self.v.change_password("nope", "a-new-password"))
        self.assertEqual(self.v.change_password(DEFAULT_PASSWORD, "a-new-password"), "")
        self.assertFalse(self.v.uses_default_password())
        fresh = Vault(self.path, FakeCipher())
        self.assertFalse(fresh.unlock(DEFAULT_PASSWORD))
        self.assertTrue(fresh.unlock("a-new-password"))
        self.assertEqual(fresh.entries()[0]["service"], "A")

    def test_guess_throttling(self):
        for _ in range(5):
            self.assertFalse(self.v.unlock("bad"))
        self.assertGreater(self.v.wait_seconds(), 0)
        self.assertFalse(self.v.unlock(DEFAULT_PASSWORD))     # still locked out
        self.now[0] += 20
        self.assertTrue(self.v.unlock(DEFAULT_PASSWORD))


if __name__ == "__main__":
    unittest.main()
