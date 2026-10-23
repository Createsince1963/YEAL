# Yeal code review, findings and open tasks (2026-10-23, versions 0.8.11 - 0.8.13)

## 1. Findings

### Browser view (WebPane.qml)
- **Back button / functions impaired.** The web view sat in a Loader that was destroyed while any dialog was open and
  created fresh afterwards. Its own page history was lost, so Back did nothing after a dialog.
- **The video restarted whenever a dialog (export to MP3, audio choice, playlist ...) opened** - same cause.
- **Regressions from parallel editing.** Two coders overwrote WebPane.qml (many `.bak` / `known-good` copies were found).
  Lost: mute-during-ads (0.8.7), the "theme reload only once" guard, the logo placeholder (0.8.6).
- **The ad skipper muted the video and never unmuted it.**
- **Endless-reload risk:** the dark-theme step called `location.reload()` whenever the PREF cookie did not match; if
  YouTube rewrites the cookie itself the page reloads forever.
- A `--selftest` hook (`testSuspend`) is still in WebPane.qml ("remove after testing").

### Other code
- No hard module conflicts found in backend, platforms, updater, adblock or localserve. Tests: 120 passed, 1 skipped.
- Unused imports (audioprobe.py) removed. `PySide6.QtWebView` import in backend.py is an availability check (intended).
- Album playlist `.m3u8` could not be read by VLC (cause not confirmed, see open tasks).
- Album with tracks wrote its HTML page only next to the full file, not into the album folder.

### Exe size (dist\Yeal.exe, 62.8 MB)
| Part | Compressed |
|---|---|
| Qt / PySide6 DLLs and plugins | 36.9 MB (Qt FFmpeg stack for the preview player about 9 MB) |
| Python modules (PYZ), of which yt-dlp extractors | 11.0 MB, 4.7 MB |
| Python runtime, OpenSSL, other | about 13 MB |

Qt dependency check (Linux Qt build, same module graph): NOT removable - Qt6QmlWorkerScript, Qt6Concurrent,
Qt6OpenGL, QtOpenGL.pyd, Qt6QuickDialogs2QuickImpl, Qt6QuickEffects (Thumb.qml), Qt6QuickShapes (Icon.qml).

### Versions and history
- Source of versions 0.1.0 - 0.8.8 is **not recoverable locally**: GitHub had 2 commits, `Tools_Central\Projects\Yeal` is
  empty, `_SYNC` is empty. Only CHANGELOG.md and the code inside earlier Claude chats remain.
- The Claude session folder `...\local-agent-mode-sessions\...` is protected and could not be searched.

## 2. What was changed
| Version | Change |
|---|---|
| 0.8.11 | Own page history for Back/Forward; left-chevron icon; ad muting restored; theme reload once; slimmer exe spec; `Build_Yeal_Exe.bat slim`; README; docs/VERSIONING.md |
| 0.8.12 | Web view is collapsed to 2x2 px under dialogs instead of destroyed (video keeps playing); size check + nudge after expand; re-create only as fallback |
| 0.8.13 | Album HTML page in the album folder; `.m3u8` with `#EXTENC:UTF-8`, CRLF, single-line titles |

Backups of replaced files: `_to_delete\*.before-review`, `*.before-keepalive`, `*.before-m3u`, `*.before-albumpage`.

## 3. Open tasks (TODO)
1. **Push the tags**: run `Push_Tags.bat` (tags v0.8.11, v0.8.12, v0.8.13 exist only locally).
2. **Rebuild the exe and test on Windows** (nothing here was run on Windows):
   - Start, Back / Forward / Reload, start page.
   - Open an MP3 export dialog while a video plays: video must continue; no white box after the dialog closes. If it
     fails, check the log for the re-create fallback.
   - `Build_Yeal_Exe.bat` (expected about 59 MB) and `Build_Yeal_Exe.bat slim` (expected about 51 MB; check the frame
     extractor preview with webm/VP9 videos).
3. **VLC and the album playlist**: re-download an album and open the `.m3u8`. If VLC still refuses it, send the VLC error
   text. Suspects: path longer than 260 characters (long album folder name), VLC parser quirks.
4. **Remove the `--selftest` hook** from WebPane.qml and the debug launchers once the dialog behaviour is confirmed.
5. **Logo placeholder before the first page load (0.8.6)** is still missing; it conflicts with the Loader approach.
6. **Search for old versions**: copy `...\local-agent-mode-sessions\d6793a73-...\c146320f-...` into `APK YEAL\_SYNC` so it
   can be searched; extract code from the earlier Yeal chats if needed.
7. **Audit all other projects** under `AI_Coworker_Claude` for the versioning rule (git, remote, pushed, tags,
   snapshots) and report gaps. New projects: ask about version storage at the start.
8. **Save the `version-preservation` skill** (proposal card was shown; it must be saved by the user).
9. Optional size work: recompress the three logo PNGs (about 1 MB), slim bundle of yt-dlp extractors with first-start
   download (about 4 MB, needs internet at first start).
10. Old tracks/pages are not regenerated: albums downloaded before 0.8.13 need a re-download for the new HTML/m3u8.
11. Existing TODO.md items (real-app checks of 0.8.6 - 0.8.9, playlist ideas, speech-to-text idea) remain open.

## 4. Rules
- Every version: update VERSION + CHANGELOG, commit, tag `vX.Y.Z`, push branch and tags (docs/VERSIONING.md).
- Before overwriting a file that several coders edit, commit first or copy it to `_to_delete\<name>.before-<reason>`.
