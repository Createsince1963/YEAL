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
