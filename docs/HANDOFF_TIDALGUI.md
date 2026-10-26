# Handoff: TIDAL DIY (Yeal 0.9.1) – Stand 2026-10-25

Plan (freigegeben): [docs/PLAN_TIDALGUI_0.9.1.md](PLAN_TIDALGUI_0.9.1.md) (vollständiger, vom Nutzer freigegebener Plan).
Code: `BIN/versions/v0.1/PyModul/yeal/`, Tests: `tests/`, Python: `Tools_Central\Python\python\python.exe`
(Tests: `Test_Yeal.bat` oder je Modul `python -m unittest test_xyz` in `tests/` mit `QT_QPA_PLATFORM=offscreen`).

## Versionsregel (Nutzer)
Vor jedem größeren/riskanten Schritt: Stand sichern (`_snapshots/<Datum>_v<Version>_<Grund>/` + lokaler Commit + Tag)
und Version eine Stufe höher: **0.9.1.01, 0.9.1.02, …** bis der Nutzer 0.9.2 vorgibt. Push zu GitHub nur für
vom Nutzer festgelegte Versionen und nur auf Anweisung. Bei jeder Version VERSION, `yeal/__init__.py`,
`pyproject.toml`, `CHANGELOG.md` gemeinsam setzen.

## Erledigt (lokal committet + getaggt)
| Version | Inhalt |
|---|---|
| 0.9.1.01 | Umschalter **YouTube / TIDAL Web / TIDAL DIY** (`Sidebar.qml`, `Main.qml` `player`: youtube/tidal/tidaldiy, `DownloadsPage.qml` Loader `tidalDiyLoader`), Menübreite passt sich an (`AppMenu.qml`, `AppMenuItem.qml`), „Tidal settings…“ im Qualitätsmenü, Platzhalter `TidalHome.qml`, Logo-Warnungen behoben |
| 0.9.1.02 | `core/tidal_api.py` (nur stdlib, nutzt tiddl-Login `~/.tiddl/auth.json`, Refresh via `tiddl auth refresh`, Cache 5 min, max 2 parallel, PAGE_LIMIT 50) + `tests/test_tidal_api.py` (Fake-Server, 16 Tests) |
| 0.9.1.03 | TIDAL-Optionen als Chips (`TidalOptions.qml`, im Workflow + Settings > Tidal > Download options), neue Settings `tidal_atmos/singles/lyrics/lrc/cover_embed/cover_file/m3u/html/no_skip/rewrite/volume/tile_size/layout`, eigener tiddl-Ordner `<data>/tiddl` (TIDDL_PATH, config.toml, auth.json-Spiegel) in `core/tidal.py` + `engine._run_tidal`, HTML-Player-Seite nach Download, Tests erweitert (Engine-Tests laufen jetzt auch unter Windows) |

## In Arbeit (Schritt 4+5, als WIP committet, NICHT getaggt, noch nicht getestet)
Neu geschrieben, aber **noch nicht geladen/getestet**:
- `yeal/ui/tidal_backend.py`: `TidalBackend` (Kontext `tidal`; `load(route,arg)` → `pageLoaded/pageFailed`, Playlists/Favoriten, `toggleFavorite`, Playlist anlegen/umbenennen/löschen/Titel hinzufügen/entfernen, `download(urls)`, `copyLink`, `saveLinklist(s)`), `TidalPlayer` (QMediaPlayer, Warteschlange `QueueModel` mit move/remove, Shuffle/Repeat, Lyrics, Qualitäts-Badge) – eingebunden in `Backend.__init__` (`self.tidal`), `Backend.shutdown`, `main.py` (`setContextProperty("tidal", …)`), `tests/test_qml_smoke.py`. Neues Signal `Backend.tidalDiyPlaying`.
- `core/extras.py`: `tidal_linklist_html()` / `write_tidal_linklist()` (HTML-Linkliste, kein Download, nie überschreiben).
- `Icon.qml` (`filled`), `IconPaths.qml` (heart, shuffle, repeat, repeatOne, skipNext/Prev, queue, lyrics, volume, mute, home, compass, bell, library, user, share, listAdd, back, dock).
- QML: `TidalRequest`, `TidalStatus`, `TidalTile`, `TidalTrackRow`, `TidalTrackList`, `TidalShelf`, `TidalFeed`, `TidalGrid`, `TidalCollection`, `TidalDetail`, `TidalArtist`, `TidalPlaylists`, `TidalQueue`, `TidalPlayerBar`.

## Nächste Schritte
1. **`TidalHome.qml` neu schreiben** (ist noch Platzhalter). Muss als `ctl` für alle Seiten bereitstellen:
   `open(item)`, `playItem(item)`, `itemMenu(item, extra)`, `openList(title, morePath, items)`, `search(text)`,
   `addToPlaylist(trackIds)`, `download(items)` (→ `tidal.download(items.map(url))`), `askName(title, text, cb)`,
   `confirm(text, cb)`, `back()`, `openInWeb(url)` (→ Player „tidal“ + navigate), `fmt(sec)`, `fmtLong(sec)`,
   `tileSize`, `setTileSize(v)` (→ `backend.setSetting("tidal_tile_size")`), `currentId`, `pausePlayback()`
   (→ `tidal.playerObject.pause()`), Signal `videoLink(url)` (beim Öffnen kanonischen Link an Workflow).
   Aufbau: nicht angemeldet → EmptyState (`backend.tidalLogin()`, `backend.tidalNotice`); sonst SplitView:
   [TidalPlaylists ~220px] | [Navigationsreiter oben waagrecht: Zurück/Vor, Start · Entdecken · Feed · Meine Sammlung
   + StackView] | [TidalQueue ~300px]; unten TidalPlayerBar (Signal toggleQueue). Routen: album/playlist/mix →
   TidalDetail{kind,itemId,seed}; artist → TidalArtist; link → TidalShelf{route:"page", arg:item.id};
   track → spielen; Start/Entdecken → TidalShelf{route home/explore}; Feed → TidalFeed; Sammlung → TidalCollection;
   Suche → TidalShelf{route:"search", arg}. Beim Laden `tidal.refreshLibrary()`.
2. `Main.qml`: auf `backend.tidalDiyPlaying` die Web-Player pausieren, wenn `single_playback` (DownloadsPage.pausePlayer für "youtube" und "tidal").
3. qmldir um neue Tidal*-Dateien ergänzen, `tests/test_tidal_gui_qml.py` COMPONENTS ergänzen, QML-Fehler beheben.
4. Tests für `QueueModel`/`TidalPlayer`-Logik (move/remove/shuffle restore) und `write_tidal_linklist` schreiben.
5. Schritt 7: Docks (`TidalDock.qml`: links/rechts/eigenes Fenster/ausblenden, Player oben/unten), Layout in `tidal_layout` speichern, „Layout zurücksetzen“ in Settings > Tidal.
6. Schritt 8: Doku (`docs/ARCHITECTURE.md`: tidal_api → tidal_backend → QML + QtMultimedia-Ausnahme; `docs/TIDAL_EVALUATION.md`; `help/manual-*.html`), `Yeal.spec` (neue QML), EXE bauen, manueller Gesamttest laut Plan.

## Bekannte Punkte
- `test_streaming.py`: 2 Fehler schon vor dieser Arbeit (echter KEF-Lautsprecher im LAN gefunden; Port-Test unter Windows) – nicht Teil dieser Aufgabe.
- Wiedergabe mit tiddl-Login: Tidal liefert zum Abspielen max. FLAC 16-bit/44.1 kHz (auch bei MAX); Badge zeigt das ehrlich. Downloads nicht betroffen.
- Bash-Heredocs in dieser Umgebung halbieren `\\` → Dateien mit Backslashes nur mit Write/Edit schreiben.
- Feed-Endpunkt: `v2/feed/activities?userId=…` ohne abschließenden Schrägstrich.

## Update 0.9.1.04 (2026-10-25, local commit + tag v0.9.1.04, not pushed)
- Done: `TidalHome.qml` (SplitView playlists | tabs + page | queue, player bar, context menu, name/confirm dialogs, history), Main/DownloadsPage wiring (`webRequested` -> TIDAL Web, `tidalDiyPlaying` pauses web players), drag and drop to download (`TidalDragSource.qml` on tiles/rows/playlists, `DropArea` in `WorkflowPanel.qml`), collapsible `TidalOptions.qml` (one group open at a time).
- All new components load without QML warnings (`tests/test_tidal_gui_qml.py`). The signed-in view, playback, the drag from the TIDAL **Web** view (native WebView2 drag-out) and the real GUI were NOT tried by hand yet: do the manual test from the plan first.
- Known: the full `unittest discover` run segfaults at `test_streaming...test_qml_button_menu_and_dialog_load` on clean HEAD too (several Qt engines in one process); the test passes alone. Run test files individually.
- Still open: tests for QueueModel/TidalPlayer/`write_tidal_linklist`, step 7 (docks, own windows, `tidal_layout` saving, reset in Settings), step 8 (ARCHITECTURE.md, TIDAL_EVALUATION.md, manuals, EXE build, full manual test).

## Update 0.9.1.05 (2026-10-25, local commit + tag v0.9.1.05, not pushed)
- Done: step 7. `TidalDock.qml` (dock left/right, own window, hide), `TidalHome.qml` arranges the areas (re-parenting inside the SplitView, `arrange()`), saves `tidal_layout` (`setSide`, `togglePane`, `moveFloat`, `saveWidths`, `setPlayerTop`, `resetLayout`), reset button in Settings > Tidal. `Backend.setSetting` now converts `QJSValue` objects (before, object values from QML were dropped silently).
- Hand test still needed: drag the dividers, detach a window, restart Yeal and check the arrangement returns; second monitor removed case.
- Still open: tests for `QueueModel` / `TidalPlayer` / `write_tidal_linklist`, step 8 (ARCHITECTURE.md, TIDAL_EVALUATION.md, manuals, `Yeal.spec` check, EXE build, full manual test).

## Update 0.9.1.06 (2026-10-25, local commit + tag v0.9.1.06, not pushed)
- Done: step 8. `tests/test_tidal_player.py` (QueueModel, player logic, link list), manuals EN/DE chapter TIDAL, ARCHITECTURE.md / TIDAL_EVALUATION.md, `Yeal.spec` checked (no change needed), `dist\Yeal.exe` built (58.6 MB) and started once offscreen (ran 12 s).
- NOT done: manual end-to-end test with the signed-in account (plan section 7), drag from the TIDAL Web view, EXE test with real playback.
- New idea waiting for a decision: `docs/PLAN_PLAYER_TRACK.md` (track-shaped player from the concept video; the video itself stays untracked in `docs/optional/`).

## Update 0.9.1.07 (2026-10-25, local commit + tag v0.9.1.07, not pushed)
- Done: TIDAL options in the workflow panel are two-column tiles, quality merged in (the duplicate quality menu button is hidden for TIDAL), the whole block folds (`tidal_opts_collapsed`), `TidalOptions.qml` rewritten (data model `groups`, `overview`). EXE not rebuilt for this version.

## Update 0.9.1.08 (2026-10-25, local commit + tag v0.9.1.08, not pushed)
- Done: download tile fixes (YouTube cookie hint hidden on success; TIDAL tile with song / artist / cover via `TidalApi.describe` and `Engine.tidal_meta`), HTML page per-title cover + `#id` link + time-synced header cover, cut shift 0.5 s earlier for chapter splitting (`album.shift_cuts`, `album.install_cut_shift`), album page cover. EXE not rebuilt for 0.9.1.07 / 0.9.1.08.
- Still open: hand test with a signed-in account; real check of the HTML page in a browser; the manuals do not yet mention the 0.5 s cut shift.

## Update 0.9.1.09 (2026-10-25, local commit + tag v0.9.1.09, not pushed, NO EXE built - rule: the user reviews first)
- Done: track player (oval) + panel, real levels, queue drag and drop (`TidalDragSource` / `TidalQueueDrop` / `tidal.dragPayload` / `TidalPlayer.enqueue`), folder button target for Tidal tiles, table column alignment.
- Hand test needed: sound + level band moving with the music (the level path was only tested with generated buffers and a sine file), drag from the table into the queue dock and into the panel, folder button for song / album / video, resizing table columns.

## Update 0.9.1.10 (2026-10-25, local commit + tag v0.9.1.10, not pushed, no EXE)
- Test feedback 0.9.1.09: the band was only a running level, not the song. Now `SongProfile` (240 bins) in `tidal_backend.py` + band modes song / flow / off (`tidal_player_vis_mode`). Local files (next step) can be scanned completely with `QAudioDecoder` so their profile is there from the start.
- Next (decided with the user): an own player for DOWNLOADED files in the oval design (also for streaming to the box over WLAN): `LocalPlayer(TidalPlayer)`, library of finished audio downloads, fourth player button, "Play in Yeal player" in the row menu.

## Update 0.9.1.11 (2026-10-25, local commit + tag v0.9.1.11, not pushed, NO EXE - the user reviews first)
- Done: player for downloaded files (`ui/local_player.py`: `LocalPlayer(TidalPlayer)`, `LocalOwner`, `library_items`; `LocalPlayerView.qml`, panel library tab, Sidebar button "Player", row menu "Play in Yeal player", `Backend.playInYeal / streamFile`), drop on the TIDAL DIY player = play now (`TidalPlayer.playNow`).
- Hand test: sound from a downloaded file, the loudness band appearing at once, STREAM to the KEF, library after new downloads (the list refreshes when the library tab / view opens).
- Open: equalizer (own audio engine), lyrics for local files, a "refresh" when a download finishes while the view is open.

## Update 0.9.1.12 (2026-10-25, local commit + tag v0.9.1.12, not pushed, NO EXE)
- Done after the user's test of 0.9.1.11: visible volume slider and 10 s jumps under the oval, colour setting, played list, solar system view (`LocalPlayerView.qml`, `Planet.qml`, `PlanetCard.qml`).
- Not done: the same solar-system layout for the TIDAL DIY player (only the player for downloads has it); equalizer; hand test of dragging, STREAM, colours and the planets with real window sizes.

## Update 0.9.1.13 (2026-10-25, local commit + tag v0.9.1.13, not pushed, NO EXE)
- Done: generic `SunView.qml` (zones left / right / top / bottom, slots, planets with own orbits by dragging, orbit slider), `LocalPlayerView.qml` and new `TidalSunView.qml` are thin wrappers; `TidalHome` has the sun mode (`tidal_sun`, `forceHidden` on the docks).
- Hand test: dragging planets with the mouse, the slider and wheel in a big window, the sun view of TIDAL DIY with a signed-in account, cards in a small window.
- Open: equalizer; lyrics for local files; planets keep their zone for the cards even when dragged to the other side.

## Update 0.9.1.17 (2026-10-26, local commit + tag v0.9.1.17, not pushed, NO EXE)
- Done: audio output choice (0.9.1.16), own audio engine (`core/dsp.py`, `ui/dsp_media.py`, `SunSound.qml`, settings `audio_engine` / `dsp`).
- Hand test needed: listen with Bluetooth headphones (A2DP stereo entry), EQ sliders while a song plays (350 ms pause, small gap when the filter is rebuilt), ReplayGain jump for a local file (the gain is set when the scan ends), crossfeed taste, an impulse response, seeking in a long mix, TIDAL songs through the own engine (stream URL via ffmpeg, hi-res DASH still falls back to CD quality).
- Open: bundle numpy in the exe (size!) or leave the engine as an optional extra; live filter change without the gap; ReplayGain before the first sound; DASH hi-res through ffmpeg; the same chain for Stream to box is not possible (the speaker plays the file itself).
