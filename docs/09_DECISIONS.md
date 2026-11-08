# 09 Decisions

Reconstructed from existing project documents on 2026-11-07. Status values: `freigegeben` only when a source says the owner approved/decided it; otherwise
`vorgeschlagen` = documented after the fact, owner confirmation requested (list in [12_PROJECT_STATE.md](12_PROJECT_STATE.md), section Open owner decisions).
Fields not found in the sources are written "n/a" - nothing was filled in by guessing.

---
**D-001 One code base, two targets (Python + PySide6/QML)**
Datum: before 0.8.x (n/a exact) - Status: vorgeschlagen - Problem: a Seal-style downloader for Windows 11 and Android.
Entscheidung: `core/` without Qt/platform code, `platforms/` per OS, QML UI. Begründung: both targets share logic (ARCHITECTURE.md rules 1-5). Risiken: Android gaps (ANDROID.md).
Betroffene Module: all. Owner-Freigabe: not documented.

**D-002 yt-dlp self-update from PyPI into the data folder**
Status: vorgeschlagen - Problem: YouTube changes constantly; old yt-dlp stops working. Entscheidung: `core/updater.py` keeps `<data>/ytdlp`, sha256 + zip-slip checks, atomic swap, lazy import. Betroffene Module: updater, engine. Owner-Freigabe: n/a.

**D-003 Custom yt-dlp options only as a safe subset**
Status: vorgeschlagen - Entscheidung: `FORBIDDEN_KEYS` blocks exec hooks, postprocessor chain, external downloaders, output paths, browser cookies. Betroffene Module: presets. Owner-Freigabe: n/a.

**D-004 tiddl is the only TIDAL download engine**
Datum: 2026-10-24/25 - Status: freigegeben (project memory: "tiddl is the only TIDAL download interface (tidal-dl-ng rejected)") - Geprüfte Optionen: tiddl, tidal-dl-ng (r3ferrei fork),
tidarr, Tidal-Media-Downloader, Tidal-Media-Downloader-PRO, tidalext ([TIDAL_EVALUATION.md](TIDAL_EVALUATION.md)).
Begründung: Apache-2.0, CLI, maintained, one process like yt-dlp; tidal-dl-ng does not start as shipped, Python pinned <3.13, AGPL-3.0, no per-run options. Risiken: TIDAL token / stream manifest changes -> update tiddl independently.
Verworfen: all others (kept documented so they are not reintroduced without new reason). Betroffene Module: `core/tidal.py`, engine.

**D-005 TIDAL DIY uses an own stdlib API layer with tiddl's token**
Datum: 2026-10-25 - Status: freigegeben ("PLAN_TIDALGUI_0.9.1.md (vollständiger, vom Nutzer freigegebener Plan)") - Geprüfte Optionen: `tidalapi` (LGPL-3.0) vs own `core/tidal_api.py`.
Entscheidung: own layer, no extra dependency, token never stored by Yeal. Risiken: unofficial API, errors isolated per area. Ersetzt: the idea in TIDAL_EVALUATION ("tidalapi for listing").

**D-006 Isolated tiddl home (`TIDDL_PATH=<data>/tiddl`)**
Status: freigegeben (part of the approved plan, section 5) - Entscheidung: own `config.toml`, `auth.json` mirrored from `~/.tiddl`, newer token written back by `expires_at`, user's global tiddl config untouched.

**D-007 Playback quality capped to FLAC 16-bit / 44.1 kHz**
Status: vorgeschlagen - cause: TIDAL delivers at most this with the tiddl token; Hi-Res/DASH is down-graded for playback; badge shows the real quality. Downloads unaffected.

**D-008 QtMultimedia exception to the "only core Qt modules" rule**
Status: freigegeben (plan) - `ui/tidal_backend.py` imports QtMultimedia lazily (`_ensure`); a build without it still starts and shows a toast on play.

**D-009 Web view collapsed to 2x2 px under dialogs instead of destroyed**
Datum: 0.8.12 (2026-10-23) - Status: vorgeschlagen - Problem: Loader destruction lost page history and restarted the video; Entscheidung: collapse + size check; re-create only as fallback. Owner-Freigabe: n/a (owner requirement "dialogs must not interrupt the YouTube view" is in memory, see OR-011).

**D-010 Track player: switchable look, real levels only, no EQ (first version)**
Datum: 2026-10-25 - Status: ersetzt (EQ part) - see [PLAN_PLAYER_TRACK.md](PLAN_PLAYER_TRACK.md): style `bar|track`, default stays bar, no made-up animation. The "no EQ" decision was overtaken by D-012.

**D-011 `ARCHITECTURE.md` stays as detail source; `02_ARCHITECTURE.md` links it**
Datum: 2026-11-07 - Status: vorgeschlagen (initialisation, avoids duplicate truth). Owner-Freigabe: pending.

**D-012 Own audio engine (ffmpeg -> float32 DSP -> QAudioSink), optional**
Datum: 0.9.1.17 (2026-10-26) - Status: vorgeschlagen - Entscheidung: runs in the GUI thread; needs numpy; falls back to Qt's player. Consequences: long work must be sliced; numpy not in the exe; no chain for Stream to box. Offene Entscheidung: bundle numpy or keep optional ([12](12_PROJECT_STATE.md)).

**D-013 No Canvas `shadowBlur`; canvases at most ~20 Hz**
Datum: 0.9.1.37 - Status: vorgeschlagen -> treated as binding technical rule (CLAUDE.md "Hard-won technical facts"; OR-006). Evidence: 1346 ms per paint measured with `tests/bench_open_cards.py`.

**D-014 TIDAL qualities Normal / High / Max; Normal converted to MP3 320**
Datum: 0.9.1.22/.24 - Status: vorgeschlagen (CHANGELOG entry; request origin not recorded) -> OR-010 awaiting confirmation. Verworfen: "Low" (AAC 96).

**D-015 Cookie file and login pack instead of moving browser cookies**
Datum: 0.9.1.29/.30 - Status: vorgeschlagen - Reason: embedded-browser cookies are DPAPI-bound to the Windows account; Chrome/Edge cookies cannot be read by yt-dlp. Risiken: pack only as strong as its password (>= 10 chars).

**D-016 tiddl runs from inside the exe (`Yeal.exe --tiddl`)**
Datum: 0.9.1.28 - Status: vorgeschlagen - NOT verified in a built exe.

**D-017 Android: TIDAL DIY hidden, build only on explicit request**
Status: freigegeben (central APK standard in memory: "only trigger on explicit request") - details [ANDROID.md](ANDROID.md).

**D-018 Song fans without oval ring; vertical cards in front**
Datum: 0.9.1.36 - Status: ersetzt D (fans of 0.9.1.20) - less drawing work. Verworfen: oval ring + flying pills.

**D-020 Remove Vimeo support**
Datum: 2026-11-07 - Status: freigegeben (owner answer Q-01) - Problem: code embeds Vimeo players although only YouTube/TIDAL are intended. Entscheidung: remove Vimeo from the online-player embed.
Betroffene Module/Dokumente (to change in a separate, approved task): `core/extras.py` (`embed_url`), `core/models.py` comment, `ui/qml/ProfileEditor.qml` hint, README, manuals, tests touching `embed_url`. Not yet implemented.

**D-019 Source history before 0.8.10 is not recoverable**
Fact, not a decision: GitHub had 2 commits, `Tools_Central\Projects\Yeal` and `_SYNC` empty (REVIEW_AND_TODO). From 0.8.10 on every version is tagged (VERSIONING.md).
