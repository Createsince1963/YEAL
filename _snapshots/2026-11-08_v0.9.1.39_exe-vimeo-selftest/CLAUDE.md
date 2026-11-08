# Yeal / MediaOrbit - project notes for Claude Code (read this first)

This file is the hand-over for a new session or a **different Claude account**: the project does not depend on the account; the
session history and the personal memory do. Everything a new session needs is here and in `docs/HANDOFF_TIDALGUI.md`,
`CHANGELOG.md`, `docs/VERSIONING.md`.

## What it is
Yeal: a Seal-style video / audio downloader (yt-dlp, TIDAL through tiddl) with its own players, written in Python + PySide6/QML for
Windows 11 (and an Android APK target). The players are drawn as a small solar system ("sun view"): the oval track player is the sun,
the planets (Library, Queue, Played, Settings, Speaker, Sound, Folders ...) open cards. The logo / brand of the player view is
"MediaOrbit" (the app is still called Yeal).

## Where things are
- Root: `C:\Users\mail\AI_Coworker_Claude\APK YEAL` (git repo, branch `main`, remote GitHub Createsince1963/YEAL).
- Source: `BIN\versions\v0.1\PyModul` - `main.py`, `yeal\core\` (no Qt: settings, engine, tidal, dsp, vault, loginpack, music_sources),
  `yeal\ui\` (Qt backend, players, calibration, perfmon), `yeal\ui\qml\` (all QML, `assets\` logos).
- Tests: `tests\` - run ONE file at a time (several Qt engines in one process crash):
  `set QT_QPA_PLATFORM=offscreen` and `set QT_QUICK_BACKEND=software`, then
  `C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe -m unittest test_xxx` from `tests\`
  (or `Test_Yeal.bat`). After a card / button change always run `test_gui_clipping`, `test_qml_smoke`, `test_tidal_gui_qml`.
- Python: the central portable WinPython above (`_find_python.bat`). Run: `Run_Yeal.bat`; no-GPU: `Run_Yeal_NoGPU.bat`.
- Diagnostics: `YEAL_PERF=1` prints CPU / RAM / threads / GUI lag every 2 s; `YEAL_DATA_DIR` moves the data folder (tests use it);
  `Calibrate_Yeal.bat` (sound check; also a button in the Settings planet); `tests\bench_player.py`, `tests\bench_open_cards.py`.
- Brand sources and the scripts that make the logo files: `docs\brand\`.

## Rules of the owner (Thomas) - keep them
- Chat in **German**; code, comments, docs, commit messages in **English**.
- **Versioning:** before a larger / risky change make a snapshot (`_snapshots\<date>_v<version>_<reason>\`) and raise the interim
  version `0.9.1.NN` in `VERSION`, `yeal\__init__.py`, `pyproject.toml`, `CHANGELOG.md` together; local commit + tag `vX.Y.Z.NN`.
  **Push only versions the user names**, and only when he says so. Never lose code.
- **No EXE build unasked** (`Build_Yeal_Exe.bat`): the user reviews first. `dist\Yeal.exe` is old (0.9.1.06).
- **No cut-off buttons:** rows of buttons / chips are a `Flow`, never a plain `Row` wider than the card (`test_gui_clipping`).
- **Parallel coders:** another session may edit the same tree. Run `git status` before editing; do not touch or commit changes that are
  not yours (document the needed change instead); never `git stash` / reset other people's work.
- The AI Hub (`D:\@AI Tools\AI_Launcher`) is read-only (a model only). Do not guess root paths; look in project files first.
- Hand tests are done by the user; say plainly what was only tested by script.
- Windows / tool quirks: Git-Bash heredocs halve backslashes - write files that contain `\` with the Write / Edit tools (or a
  Python script file), not with `cat <<EOF`. Git has `autocrlf`: "LF will be replaced by CRLF" warnings are normal.

## Machines (for judging performance)
- Monitor: 2560 x 1440, 100 % scaling, landscape. Laptop: ThinkPad 20HJS0K001, i7-7820HQ (4 cores, 2017), 32 GB, RTX 5070 12 GB +
  Intel HD 630, disk 427 of 466 GB used (almost full - do not write big files for nothing; `_snapshots` is 24 MB, `dist` 262 MB).
- Qt Quick may render on the Intel GPU: Windows > Settings > System > Display > Graphics > set python.exe / Yeal.exe to "High performance".

## Hard-won technical facts
- **Never use Canvas `shadowBlur`** (software blur of the whole canvas: 1.3 s per paint, made the GUI crawl and the sound stutter).
  Make glows from faint strokes / radial gradients; repaint canvases at most ~20 Hz; a full-window canvas must not repaint with the music.
- The own audio engine (`ui/dsp_media.py`: ffmpeg -> float32 chain -> QAudioSink) runs in the GUI thread: a busy GUI starves the sound
  buffer (`audio_buffer_ms`, default 600). Long work (library scans, decoding) must be sliced or run in a thread.
- `AppButton` clamps its width to the parent only inside a `Flow` / `Grid`; elsewhere it keeps its natural width (a clamp in a
  self-sizing Row made a binding loop and empty buttons). `Chip` caps its natural width at 200 px.
- TIDAL: quality `normal` = AAC 320 in `.m4a`, converted to MP3 320 after the download (`tidal.convert_to_mp3`); `high` / `max` are FLAC.
  `low` (AAC 96) was removed (a saved "low" becomes "normal"). MP3 is only ever 320 kbps.
- tiddl runs from inside the exe as `Yeal.exe --tiddl ...` (`main.py`, `tidal.EMBEDDED`); `Yeal.spec` packs it - **not yet verified in a
  built exe**. ffmpeg must be in `bin\` next to the exe (or `YEAL_EMBED_TOOLS=1`).
- The embedded browser's cookies are DPAPI-bound to the Windows account: they cannot be moved to another PC. For downloads use a
  `cookies.txt` (Settings > Login & network); the **login pack** (Settings > Admin > "Take the logins with you", `core/loginpack.py`)
  carries Tidal sign-in + cookie file + vault entries in one password-encrypted file.
- Cards of the sun view open on the side where their planet stands (`SunView.zoneOf`); cards with `edit: true` zoom for editing.

## State (update this when you finish something)
- Version **0.9.1.38** (local commits + tags `v0.9.1.19` ... `v0.9.1.38`, nothing pushed, no EXE since 0.9.1.06).
- Done since 0.9.1.18: cards at their planets, Folders planet (own music folders, network), edit-mode zoom, drag library / albums /
  folders into the queue, Clear all + Save list, song lists above / below the player, TIDAL options as pulldowns, TIDAL Normal -> MP3 320,
  sound check + calibration, performance fixes, tiddl in the exe, login pack + cookie file, new logos (MediaOrbit mark, Yeal tile),
  password Show / Hide, oval glow without shadowBlur.
- **Open / to verify by hand:** a long listening test with `YEAL_PERF=1` over Bluetooth; the new exe (tiddl inside, icon, logos) on a PC
  without Python; hand test of the card zoom, the drag into the queue, the login pack on a second PC; numpy is not in the exe (own audio
  engine would fall back to Qt's player there); TIDAL Normal fetches a converted song again on a repeat download; rename of a folder in
  the Folders planet; rename of the app to MediaOrbit is NOT done (only logos); the MediaOrbit source picture is low resolution.

## Switching the Claude account
Nothing in the repo is tied to an account. In the Claude Code desktop app use the account menu to sign out / in; in a terminal session
`/logout` then `/login`. A new account starts without the old session history and without the personal memory
(`C:\Users\mail\.claude\projects\C--Users-mail-AI-Coworker-Claude-APK-YEAL\memory\` belongs to the Windows profile - it stays on this PC
and is found again by a session started in this folder; on another PC it is missing). This file replaces it: a new session that reads
`CLAUDE.md` + `docs/HANDOFF_TIDALGUI.md` has the rules and the state. Start a new session with: "Read CLAUDE.md and continue".
