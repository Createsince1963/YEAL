# Engineering knowledge base - Yeal / MediaOrbit

Entry point for every AI session. Order of reading: central protocol `C:\Users\mail\AI_Coworker_Claude\.claude\PROJECT_AI_ENGINEERING_PROTOCOL.md` -> [../CLAUDE.md](../CLAUDE.md) -> this file -> the files below.
Initialised 2026-11-07 for version 0.9.1.38. Language of docs: English (OR-004).

## Purpose and context
Yeal downloads video/audio (yt-dlp, TIDAL via tiddl) and plays music in its own "sun view" players. It is a personal engineering/hobby tool of the owner, not a P3D/piping tool;
"engineering" in the protocol means software engineering here. Vision and limits: [00_PROJECT_VISION.md](00_PROJECT_VISION.md).

## Map of the knowledge base
| File | Content |
|---|---|
| [00_PROJECT_VISION.md](00_PROJECT_VISION.md) | goals, users, non-goals |
| [01_SYSTEM_OVERVIEW.md](01_SYSTEM_OVERVIEW.md) | paths, entry points, environment, data folder |
| [02_ARCHITECTURE.md](02_ARCHITECTURE.md) (+ [ARCHITECTURE.md](ARCHITECTURE.md)) | layers, rules, module map |
| [03_DOMAIN_MODEL.md](03_DOMAIN_MODEL.md) | terms, states, implemented rules |
| [04_DATA_MODEL.md](04_DATA_MODEL.md) | options, jobs, settings, files |
| [05_FUNCTIONS.md](05_FUNCTIONS.md) | business functions F-01 ... F-18 |
| [06_WORKFLOWS.md](06_WORKFLOWS.md) | user and developer workflows |
| [07_INTERFACES.md](07_INTERFACES.md) | external programs, APIs, CLI, env |
| [08_UI_UX.md](08_UI_UX.md) | UI structure and GUI rules |
| [09_DECISIONS.md](09_DECISIONS.md) | decisions D-001 ... D-019 |
| [10_CHANGELOG.md](10_CHANGELOG.md) | pointer to [../CHANGELOG.md](../CHANGELOG.md) + doc changes |
| [11_KNOWN_ISSUES.md](11_KNOWN_ISSUES.md) | KI-001 ... KI-021 |
| [12_PROJECT_STATE.md](12_PROJECT_STATE.md) | state, contradictions C-xx, open owner questions Q-xx |
| [13_OWNER_RULES.md](13_OWNER_RULES.md) | OR-001 ... OR-020 |
| [14_TEST_STRATEGY.md](14_TEST_STRATEGY.md) | test commands and suites |
| [tools/](tools/) | [Yeal_Downloader](tools/Yeal_Downloader.md), [TIDAL_DIY](tools/TIDAL_DIY.md), [MediaOrbit_Player](tools/MediaOrbit_Player.md) |
| [modules/](modules/) | [tidal](modules/tidal.md), [players](modules/players.md), [audio_engine](modules/audio_engine.md), [security_and_logins](modules/security_and_logins.md) |

## Status of the pre-existing documents (kept unchanged, nothing deleted)
| File | Role now | Remark |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | detail source for the layer diagrams | incomplete, C-10 |
| [HANDOFF_TIDALGUI.md](HANDOFF_TIDALGUI.md) | history of 0.9.1.01-0.9.1.38 | historical; migrated into 09/11/12 |
| [PLAN_TIDALGUI_0.9.1.md](PLAN_TIDALGUI_0.9.1.md) | approved design plan (German) | historical design source for TIDAL DIY |
| [PLAN_PLAYER_TRACK.md](PLAN_PLAYER_TRACK.md) | concept study for the oval player | built in 0.9.1.09; EQ part overtaken |
| [TIDAL_EVALUATION.md](TIDAL_EVALUATION.md) | candidate ranking, decision record D-004 | historical; Low quality text outdated |
| [REVIEW_AND_TODO.md](REVIEW_AND_TODO.md) | review of 0.8.11-0.8.13 | historical; open items copied to 11/12 |
| [VERSIONING.md](VERSIONING.md) | versioning rule | updated 2026-11-07 to OR-002 (C-02 resolved) |
| [ANDROID.md](ANDROID.md) | Android gaps and build path | current for D-017 |
| [../TODO.md](../TODO.md), [../README.md](../README.md), [../SECURITY.md](../SECURITY.md), [../CHANGELOG.md](../CHANGELOG.md) | root documents | README outdated, C-05 |
Per protocol 13: old files are marked here as historical; deleting or replacing them needs the owner's release (Q-07).

## Core knowledge in ten lines
1. Two download engines: yt-dlp (everything) and tiddl (TIDAL links), both as separate code paths in `core/engine.py`.
2. `core/` is Qt-free; UI talks to it only through `Backend` / `TidalBackend`.
3. TIDAL DIY reads TIDAL's unofficial web API with tiddl's token; playback is capped to FLAC 16-bit.
4. The players are drawn as a solar system; one generic `SunView.qml`, two wrappers.
5. The own audio engine is optional and lives in the GUI thread; GUI stalls become audio dropouts.
6. Secrets: vault (DPAPI + admin password), login pack (PBKDF2 + HMAC stream), cookie file; Yeal never stores TIDAL tokens itself.
7. Settings are validated on load and on set; every new key needs a validation entry in `core/settings.py`.
8. Versions are interim `0.9.1.NN`, local commit + tag, never pushed unasked; no EXE unasked.
9. Tests run one file at a time, offscreen; hand tests belong to the owner.
10. Other sessions may edit the same tree: `git status` first, FOREIGN changes stay untouched.

## Boundaries and excluded features
No Seal code; no TIDAL second engine; no equalizer in the Qt player; no cloud processing; no automatic multi-agent workflow (global instructions); no Android TIDAL DIY; no Figma.
