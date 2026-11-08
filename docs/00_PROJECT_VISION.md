# 00 Project vision

Status: initialised 2026-11-07 from existing project knowledge (see [12_PROJECT_STATE.md](12_PROJECT_STATE.md)).
Rules for every AI session: `C:\Users\mail\AI_Coworker_Claude\.claude\PROJECT_AI_ENGINEERING_PROTOCOL.md` (central) and
[../CLAUDE.md](../CLAUDE.md) (project). Index of this knowledge base: [ENGINEERING_KNOWLEDGE_BASE.md](ENGINEERING_KNOWLEDGE_BASE.md).

## What Yeal is
Yeal is a Seal-style video / audio downloader (yt-dlp, TIDAL through tiddl) with its own players, written in Python +
PySide6/QML for Windows 11, with an Android APK target. The brand of the player view is "MediaOrbit"; the app itself is still
called Yeal (the rename is not done, see [11_KNOWN_ISSUES.md](11_KNOWN_ISSUES.md)).
Sources: [../CLAUDE.md](../CLAUDE.md), [../README.md](../README.md).

## Goals (as stated in project files)
1. Download video / audio from many sites with a simple workflow (profiles, queue, playlists, albums from tracklists,
   live streams), with polite ("gentle") request behaviour. Source: README, `core/presets.py`, `core/queue.py`.
2. Download from TIDAL with the user's own subscription (tiddl is the only TIDAL download interface). Source: [09_DECISIONS.md](09_DECISIONS.md) D-004.
3. Play music in Yeal's own players: the "TIDAL DIY" view (native TIDAL browser + player) and the player for downloaded
   files, both drawn as a small solar system ("sun view": oval track player = sun, planets = cards). Source: CLAUDE.md, HANDOFF_TIDALGUI.md.
4. Keep the result durable and portable: files saved in a clear folder structure, HTML player pages, login pack, no code loss
   ([13_OWNER_RULES.md](13_OWNER_RULES.md) OR-001).
5. One code base for two targets: Windows 11 desktop and Android APK ([02_ARCHITECTURE.md](02_ARCHITECTURE.md) rules).

## Users
- Owner and main user: Thomas (chat in German). Family members sign in to TIDAL with their own accounts (README, TIDAL family plan note).
- Machines used for judging performance: see [13_OWNER_RULES.md](13_OWNER_RULES.md) section "Machines".

## Explicit non-goals / limits (from project files)
- No Seal source code, name, icon or assets are used (README legal note).
- TIDAL only with an active TIDAL subscription; no hard-coded API keys; no second TIDAL engine (tidal-dl-ng rejected).
- No equalizer in the *Qt* player; EQ exists only in the own audio engine (`core/dsp.py`).
- The Android build hides TIDAL DIY (desktop only) and has no ffmpeg / JS runtime yet ([ANDROID.md](ANDROID.md)).
- No EXE build without the owner's request ([13_OWNER_RULES.md](13_OWNER_RULES.md) OR-003).
