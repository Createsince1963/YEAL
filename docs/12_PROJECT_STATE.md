# 12 Project state

Real state on **2026-11-07**. Version files `VERSION`, `yeal/__init__.py`, `pyproject.toml` now **0.9.1.39** (was 0.9.1.38 at the start of the initialisation); branch `main`; last commit
`7d631d4` (Yeal 0.9.1.38, 2026-10-26); 45 local tags (`v0.9.1.01` ... `v0.9.1.38` plus earlier); remote `origin` = GitHub `Createsince1963/YEAL`.
Not checked: which tag/commit is the last one actually pushed (no network call made).

## Current development state
- Version 0.9.1.38, local commits + tags only, no EXE since 0.9.1.06 (OR-002, OR-003).
- Last completed change: 0.9.1.38 (Chip width cap, CLAUDE.md hand-over, handoff notes). Before that: shadowBlur fix 0.9.1.37.
- Working tree is **not clean** (FOREIGN, not from this session, left untouched):
  - modified `core/engine.py` (+23: `probe_opts`, `_READABLE_BROWSERS`) and `ui/backend.py` (3 probe call sites use `probe_opts`) - purpose: stop repeating the yt-dlp cookie error on background probes;
    no CHANGELOG entry, no tests, no version bump -> KI-020.
  - untracked: `docs/m2-res_480p/`, `docs/optional/m2-res_480p.mp4`, `docs/optional/apps_media_youtube_logo_...png` (KI-021). New in this session: the files listed in [ENGINEERING_KNOWLEDGE_BASE.md](ENGINEERING_KNOWLEDGE_BASE.md), uncommitted.

## Open tasks (with source)
1. Hand tests by the owner (CLAUDE.md "Open", HANDOFF): long listening test with `YEAL_PERF=1` over Bluetooth; new exe (tiddl inside, icon, logos) on a PC without Python; card zoom; drag into the queue
   (real system drag from library rows / folder moon); login pack on a second PC; UNC path on the network; saved lists after restart; crossfade with real music; engine switch; EQ while playing; ReplayGain;
   signed-in TIDAL DIY (playback, docks, dragging from TIDAL Web); live stream with a real stream; playlist dialog; HTML page in a real browser.
2. KI-001...KI-018 in [11_KNOWN_ISSUES.md](11_KNOWN_ISSUES.md).
3. Rename Yeal -> MediaOrbit: decided NO for now (Q-09), idea stays open.
4. Ideas without decision (speech-to-text dropped, Q-14): sort/search in the playlist dialog; shrink exe (logos, slim extractor bundle).
5. Old-version search in the protected agent-session folder (REVIEW_AND_TODO 6); audit of other projects for the versioning rule (REVIEW_AND_TODO 7) - outside this project.

## Blocked
- EXE build (waits for the owner's review). APK build (only on request; first cloud run pending).

## Next approved steps
None recorded. Next step requires owner priority (see Q-12).

## Contradictions found (C) - not resolved, no rule was invented
| ID | Contradiction | Where |
|---|---|---|
| C-01 | **RESOLVED 2026-11-07 by owner (Q-01): Vimeo is removed.** Code removal still pending as its own task (not part of the initialisation). Was: memory says embedded players are YouTube and TIDAL only, no Vimeo; code supports a Vimeo embed (`extras.embed_url`) and README/ProfileEditor say "YouTube/Vimeo" for the online player of HTML pages | memory vs `core/extras.py`, README, `ProfileEditor.qml` |
| C-02 | Versioning: `docs/VERSIONING.md` and REVIEW_AND_TODO say "commit, tag, push branch and tags for every release"; OR-002 says interim versions are never pushed (only owner-named versions) | VERSIONING.md vs CLAUDE.md |
| C-03 | `Test_Yeal.bat` is "run all tests" (discover) but a full run crashes; the rule is one file at a time | bat vs CLAUDE.md |
| C-04 | RESOLVED (Q-06): both modes stay, default server, README corrected. Was: HTML "Open page" default: README says the independent local file is the default; `Settings.html_open_mode` default is `"server"`; memory says "default server page + link to the file version" | README vs `core/settings.py` |
| C-05 | README is titled "Features (v0.8.x)" and lacks TIDAL DIY, players, sun view, audio engine, login pack; its project-layout lists only 3 docs | README |
| C-06 | TIDAL_EVALUATION says "Yeal 0.8.14+ contains no Tidal code" and lists quality LOW; PLAN_TIDALGUI lists Low/Normal/High/Max chips and the German text contradicts later state ("Low" removed 0.9.1.22) | historical docs vs code |
| C-07 | PLAN_PLAYER_TRACK: "no EQ" vs own audio engine with 10-band EQ (0.9.1.17) | PLAN_PLAYER_TRACK vs `core/dsp.py` |
| C-08 | HANDOFF_TIDALGUI header says "Stand 2026-10-25" and lists tests "still open" that were done in 0.9.1.06 | internal to HANDOFF |
| C-09 | Protocol: no GUI tests without release; CLAUDE.md: always run the QML offscreen tests after a card change | protocol vs CLAUDE.md |
| C-10 | ARCHITECTURE.md describes only the first layers; rule 5 exceptions (QtMultimedia, probably QAudioSink in `dsp_media`) incomplete | ARCHITECTURE.md |

## Open owner decisions / questions (Q)
| ID | Question | Default if the owner does not answer |
|---|---|---|
| Q-01 | ~~Vimeo as online player in HTML pages~~ ANSWERED 2026-11-07: **remove** (D-020, OR-011). Code change pending approval of a work order | - |
| Q-02 | ~~Update `docs/VERSIONING.md`~~ ANSWERED 2026-11-07: done, file now states OR-002 (C-02 resolved) | - |
| Q-03 | ~~Offscreen QML tests = "GUI tests"? `Test_Yeal.bat` loop?~~ ANSWERED 2026-11-07 (closed with the default): the three standard offscreen suites (`test_gui_clipping`, `test_qml_smoke`, `test_tidal_gui_qml`) run after card/button changes as CLAUDE.md says, no extra release needed; `Test_Yeal.bat` stays unchanged (C-03 remains a documented known issue KI-001, C-09 resolved) | - |
| Q-04 | ANSWERED 2026-11-07: keep and finish properly -> done as 0.9.1.39 (snapshot, test, changelog, local commit d37438f + tag, no push) | - |
| Q-05 | ANSWERED 2026-11-07: OR-006, OR-009, OR-010 confirmed as owner rules | - |
| Q-06 | ANSWERED 2026-11-07: both modes stay available; default stays `server` (code value); README corrected (C-04 resolved) | - |
| Q-07 | ANSWERED 2026-11-07: old docs stay unchanged as historical; only the speech-to-text section of TODO.md is removed | - |
| Q-08 | ANSWERED 2026-11-07: numpy NOT in the exe; stays an optional extra for the Python module (KI-005 accepted) | - |
| Q-09 | ANSWERED 2026-11-07 (replaces the earlier "yes"): NO rename to MediaOrbit at the moment (KI-009 stays open as idea) | - |
| Q-10 | ANSWERED 2026-11-07: Android is not a priority (no work planned) | - |
| Q-11 | ANSWERED 2026-11-07: when this initialisation round is finished, the last created version is to be pushed; the push itself waits for the explicit go at that moment (OR-002) | - |
| Q-12 | ANSWERED 2026-11-07: dropped here; the owner does the hand tests during review | - |
| Q-13 | ANSWERED 2026-11-07: owner tests the KEF speaker in the current version himself, then decide (the 2 failing tests find the real KEF LSX II in the LAN) | - |
| Q-14 | ANSWERED 2026-11-07: speech-to-text idea dropped (TODO.md section to be removed) | - |

## Hand tests outstanding
See open task 1. Everything in CHANGELOG 0.9.1.09-0.9.1.38 was verified by script only unless the changelog says the owner tested it (feedback on 0.9.1.09, .11 is recorded in the handoff).
