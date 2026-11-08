# Module: vault, login pack, cookies, network exposure

## Admin vault (`core/vault.py`)
- Entries (service, user, password, note) are encrypted with Windows DPAPI; the key derived from the admin password (PBKDF2-HMAC-SHA256, salt, 300k rounds) is used as DPAPI entropy. Only a verifier hash is stored. File is useless on another PC/account or without the password.
- Auto-lock after 5 minutes, clipboard cleared after 30 s, throttle on wrong passwords (`wait_seconds`). A new vault starts with a default password (shown as hint in the UI) and entries are unavailable until a private password is set; existing vault passwords are not changed.
- "Delete all logins" also wipes the browser sign-in. Yeal never sees the Google password (sign-in stays in the browser profile).

## Login pack (`core/loginpack.py`)
- One `*.yealpack`: TIDAL `auth.json`, YouTube cookie file, vault entries. PBKDF2-HMAC-SHA256 (400,000 rounds, random salt), HMAC-SHA256 counter-mode stream, encrypt-then-MAC; password >= 10 characters, stored nowhere. Requires the admin area to be unlocked with a private password.
- Opening: TIDAL sign-in only if newer than the local one; vault entries added only if missing. Not included: embedded browser sign-in (DPAPI-bound).

## Cookies for YouTube
Setting `cookies_file` (Netscape `cookies.txt`, must contain youtube.com/google.com cookies); Yeal keeps its own copy `youtube_cookies.txt` and passes it to yt-dlp before browser cookies. Chrome/Edge cookies are not readable (locked) -> notes on tiles; the uncommitted `probe_opts` edit (KI-020) addresses repeated errors in background probes.

## Network exposure
Local page server (127.0.0.1, one folder, no listing), media server for boxes (own port, registered files, random token, private clients only), ad-block proxy (127.0.0.1, host check only). Self-update: sha256, zip-slip protection.

## Tests
`test_vault`, `test_loginpack`, `test_streaming`, `test_adblock`, `test_updater`. The checklist template for releases is [../../SECURITY.md](../../SECURITY.md) (generic; not yet filled for Yeal).
