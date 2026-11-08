# 11 Known issues, technical debt, unverified items

Status: collected 2026-11-07 from CLAUDE.md, HANDOFF_TIDALGUI.md, REVIEW_AND_TODO.md, TODO.md, CHANGELOG.md, ANDROID.md and checks on the working tree.
"Open" = nothing in the sources shows it fixed. Items with a source date older than 0.9.1.38 may be stale; they were **not re-tested** in this initialisation.

## Defects and risks
| ID | Issue | Source | Status |
|---|---|---|---|
| KI-001 | `Test_Yeal.bat` runs `unittest discover`; the full run segfaults at `test_streaming...test_qml_button_menu_and_dialog_load` (several Qt engines in one process). Run test files one by one. | HANDOFF 0.9.1.04, CLAUDE.md | open (workaround documented) |
| KI-002 | `test_streaming.py`: 2 failures already before TIDAL work (finds a real KEF speaker in the LAN; port test on Windows) | HANDOFF "Bekannte Punkte" | open, may be stale |
| KI-003 | tiddl inside the exe (`Yeal.exe --tiddl`) not verified in a built exe | CHANGELOG 0.9.1.28 | open |
| KI-004 | TIDAL Normal repeat download fetches an already converted song again (tiddl only knows the `.m4a` name) | CHANGELOG 0.9.1.24/26 | open |
| KI-005 | numpy is not in the exe -> own audio engine falls back to Qt's player | CLAUDE.md | open, decision needed |
| KI-006 | Album `.m3u8` unreadable in VLC (cause not confirmed; suspects: path > 260 chars, parser quirks) | REVIEW_AND_TODO 3 | open |
| KI-007 | `--selftest` test hook (`testSuspend` timers) still in `WebPane.qml` ("remove after testing") | REVIEW_AND_TODO 4; file checked 2026-11-07 | open |
| KI-008 | Logo placeholder before the first page load (0.8.6) missing; conflicts with the Loader approach | REVIEW_AND_TODO 5 | open |
| KI-009 | Rename of the app to MediaOrbit not done (only logos); MediaOrbit source picture is low resolution | CLAUDE.md | open |
| KI-010 | Folders planet: no rename of a folder (field exists only when adding); saved lists have no own edit list; TIDAL library not draggable as "folder" | HANDOFF 0.9.1.19 | open |
| KI-011 | Glow follows the overall level (bass dominates), no separate bass filter; Windows volume separate from player volume | HANDOFF 0.9.1.18 | open |
| KI-012 | Own engine: live filter change leaves a small gap; ReplayGain only after the scan ends; DASH hi-res through ffmpeg missing; chain not usable for Stream to box | HANDOFF 0.9.1.17 | open |
| KI-013 | Lyrics for local files missing; "refresh" when a download finishes while the library view is open | HANDOFF 0.9.1.11/.12 | open |
| KI-014 | Embedded browser cookies are DPAPI-bound; Google may refuse sign-in in embedded views; Chrome/Edge cookies not readable by yt-dlp -> cookie file | README, CLAUDE.md | by design |
| KI-015 | TIDAL web API is unofficial; endpoints verified only 2026-10-25 with one account | PLAN_TIDALGUI | risk |
| KI-016 | Manuals do not mention the 0.5 s cut shift | HANDOFF 0.9.1.08 | open |
| KI-017 | Albums downloaded before 0.8.13 need re-download for the new HTML/m3u8 | REVIEW_AND_TODO 10 | by design |
| KI-018 | Android: no ffmpeg, no JS runtime (YouTube fails), permissions/yt-dlp bundling/folder/SAF/foreground service unverified | ANDROID.md | open |
| KI-019 | Source of versions 0.1.0-0.8.8 not recoverable | REVIEW_AND_TODO | closed (accepted loss) |
| KI-020 | RESOLVED 2026-11-07: the uncommitted `probe_opts` edit was reviewed, tested (`test_probe_opts`) and committed as 0.9.1.39 (local tag, not pushed) | git history | closed |
| KI-021 | Untracked files: `docs/m2-res_480p/`, `docs/optional/m2-res_480p.mp4`, a YouTube logo PNG in `docs/optional/` (concept video of another community; per PLAN_PLAYER_TRACK "not ours to redistribute", must stay untracked) | `git status`, PLAN_PLAYER_TRACK | open: keep out of git |

## Technical debt
- `ui/backend.py` (2133 lines, 102 slots) and `ui/tidal_backend.py` (1248 lines) are large; the protocol forbids refactoring as a side effect - only on a separate owner task.
- `_to_delete\` holds backups and `.bak` files awaiting the owner's deletion; `build\` and `dist\` are build outputs (dist ~262 MB, disk almost full).
- Hard-coded prose in docs: README feature list still titled v0.8.x (see C-05 in [12_PROJECT_STATE.md](12_PROJECT_STATE.md)).

## Not hand-tested (only tested by script)
List maintained in [12_PROJECT_STATE.md](12_PROJECT_STATE.md) section "Hand tests outstanding".
