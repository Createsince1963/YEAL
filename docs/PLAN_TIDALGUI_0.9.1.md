# Yeal 0.9.1.0 – Native TidalGUI

Grundlage: die von Copilot verdichtete Fassung, ergänzt um die Punkte, die dort fehlten. Sie sind mit **[Ergänzung]** markiert. Danach kamen die Anpassungen aus dem Screenshot vom 2026-10-25 dazu.

## Ziel
Yeal 0.9.1.0 bekommt neben der eingebetteten Tidal-Webseite eine native Tidal-Oberfläche im Yeal-Design („TIDAL DIY“). Der Webplayer (`TidalPane.qml`) bleibt als „TIDAL Web“ erhalten. Umgeschaltet wird über die Knöpfe YouTube | TIDAL Web | TIDAL DIY.

Umfang, komplett in 0.9.1.0:
- Start, Entdecken, Feed, Suche, Meine Sammlung
- Details zu Album, Künstler, Playlist und Mix
- Favoriten, Playlists erstellen und bearbeiten
- eigener Player mit Lyrics
- Download ausgewählter Titel
- erweiterte tiddl-Optionen als Chips im Workflow

Code: `BIN/versions/v0.1/PyModul/yeal/`, Tests in `tests/`.

## 1. Native Tidal-API: `yeal/core/tidal_api.py`
- Nur Standardbibliothek (urllib, json, base64), analog zu `core/streaming.py`. Kein Qt, keine tiddl-Interna.
- **Login:**
  - Der bestehende tiddl-Login (`tidal.app_path()/auth.json`) wird verwendet. Yeal speichert das Token nicht selbst.
  - Bei abgelaufenem Token oder HTTP 401 wird einmal `tiddl auth refresh` ausgeführt (über `_popen`/`_env` aus `core/tidal.py`) und die Anfrage wiederholt.
- **Lesen:**
  - `home()`, `explore()`, `feed()`, `my_mixes()`, `search()`
  - `album()`, `artist()`, `playlist()`, `mix()`, `favorites()`, `user_playlists()`, `lyrics()`, `stream_url()`
  - Detail-Methoden: Album-Titel; beim Künstler Top-Titel, Alben, Singles, Videos und Ähnliche
- **Schreiben:**
  - `add_favorite()`, `remove_favorite()`
  - `create_playlist()`, `rename_playlist()`, `delete_playlist()`
  - `add_to_playlist()`, `remove_from_playlist()`, jeweils mit Tidal-ETag
- **Rückgabe:** einheitliche Dicts `kind, id, title, subtitle, cover, duration, explicit, quality, url`. Die URL hat die kanonische Form `https://tidal.com/browse/<kind>/<id>`.
- **Player-Stream:** Aufruf von `playbackinfopostpaywall`, das BTS-Manifest wird dekodiert. Bevorzugt wird LOSSLESS/FLAC; bei Hi-Res oder DASH wird für die Wiedergabe auf LOSSLESS zurückgestuft.
- Cache im Speicher (etwa 5 min), höchstens 2 parallele Anfragen, Timeouts, Fehler gehen sauber an die GUI.
- **[Ergänzung] Geprüfte Endpunkte (2026-10-25), alle HTTP 200 mit dem tiddl-Token:**
  - `v1/pages/home|explore|my_collection_my_mixes` (`deviceType=BROWSER`)
  - `v1/users/{id}/favorites/tracks`, `v1/users/{id}/playlistsAndFavoritePlaylists`
  - `v1/search`
  - `v1/tracks/{id}/playbackinfopostpaywall` (liefert BTS / LOSSLESS)
  - Feed: `v2/feed/activities?userId=…` **ohne** abschließenden Schrägstrich. Mit `/` am Ende kommt 404.

## 2. Qt-Backend und Player: `yeal/ui/tidal_backend.py`
- `TidalBackend(QObject)` wird in `Backend` erzeugt und in `main.py` als QML-Kontext `tidal` bereitgestellt. Es kommt nicht in das ohnehin große `backend.py`.
- API-Aufrufe laufen in Worker-Threads; die Ergebnisse gehen über queued Signals an die GUI. Worker berühren keine QML-Objekte.
- Slots und Signale: `load(route, arg)`, `pageLoaded(route, data)`, `search(query)`, `toggleFavorite(...)`, Playlist-Bearbeitung, `download(urls)`.
- `download(urls)` nutzt den bestehenden Tidal-Jobpfad in `backend.py` (den `is_tidal_url`-Zweig).
- **TidalPlayer** (in derselben Datei):
  - `QMediaPlayer` + `QAudioOutput`
  - Play/Pause, Zurück/Weiter, Spulen, Lautstärke (`tidal_volume`), Warteschlange, Zufall, Wiederholen (aus/alle/eins)
  - Lyrics synchronisiert, sonst als Text
  - Die Stream-URL wird erst direkt vor der Wiedergabe geholt.
  - Die Warteschlange ist ein `QAbstractListModel` mit `move(from, to)`, `remove(i)`, `clear()` und „Als Playlist speichern“. Die Zufallsreihenfolge bleibt bei manuellem Verschieben stabil.
  - Die Einstellung `single_playback` wird beachtet.

## 3. Native QML-Oberfläche
- **Player-Umschalter mit 3 Knöpfen** statt bisher YouTube | TIDAL (`Sidebar.qml`, um Zeile 51–67, `PlayerButton`):
  - **YouTube** | **TIDAL Web** | **TIDAL DIY**, jeweils mit Logo und gleich breit.
  - Ist die Sidebar schmal, steht unter den beiden Tidal-Knöpfen nur „Web“ / „DIY“ mit dem Tidal-Logo; der Tooltip zeigt den vollen Namen.
  - `win.player` in `Main.qml` kennt die Werte `"youtube" | "tidal"` (Web, wie bisher) `| "tidaldiy"`.
- `DownloadsPage.qml` bekommt einen zweiten Loader `tidalDiyLoader` → `TidalHome.qml` (`visible: player === "tidaldiy"`, wird erst beim ersten Öffnen erzeugt und bleibt dann am Leben, wie `tidalWanted`). `TidalPane.qml` bleibt unverändert für „TIDAL Web“.
  - Spielen beide Tidal-Varianten gleichzeitig, gilt `single_playback`: Beim Umschalten pausiert der jeweils andere Player.
- `WorkflowPanel.tidalMode` ist für beide Tidal-Knöpfe wahr: `tidalPlayer: win.player !== "youtube"` in `Main.qml`, Zeile 196.
- Tidal-Login (`onTidalLoginLink` in `Main.qml`) öffnet die Bestätigungsseite wie bisher in „TIDAL Web“. Nach erfolgreicher Anmeldung kehrt Yeal zu der Ansicht zurück, von der aus der Login gestartet wurde. Ohne WebView2 öffnet sich der System-Browser.
- Die Regel „Yeal startet immer in der Standardansicht“ bleibt: Start mit YouTube.
- Neue Dateien: `TidalHome.qml`, `TidalShelf.qml`, `TidalGrid.qml`, `TidalDetail.qml`, `TidalArtist.qml`, `TidalTrackRow.qml`, `TidalPlayerBar.qml`, `TidalPlaylists.qml`, `TidalQueue.qml`, `TidalDock.qml`. Sie nutzen nur `Theme` und vorhandene Bausteine (`AppButton`, `IconButton`, `Chip`, `Segmented`, `AppMenu`, `EmptyState`).

### 3a. Layout: Aufteilung wie im Webplayer, aber frei verschiebbar (Screenshot 2026-10-25)
Die Grundaufteilung des heutigen TIDAL-Rahmens bleibt vorerst erhalten. Alle Bereiche werden aber **anpassbar**, und Yeal merkt sich Position und Größe.

| Bereich | Inhalt | Änderung gegenüber Tidal |
|---|---|---|
| **Playlists** (Standard: links) | „Alle Playlisten“ (eigene und favorisierte, Cover, Name, Anzahl), oben ein Filterfeld | **deutlich schmaler** (Standard etwa 220 px, nur Cover-Kachel und eine Zeile Text) |
| **Navigation** | Start · Entdecken · Feed · Meine Sammlung (Playlists, Alben, Künstler, Titel, Mixes, Videos) | Nicht mehr senkrecht links, sondern als **waagrechte Reiterleiste** oben über dem Hauptbereich, also neben der Playlist-Spalte. Dazu Zurück/Vor. |
| **Hauptbereich** (Mitte) | Start, Entdecken, Feed, Sammlung, Suche, Details | **neu gestaltet, siehe 3b** |
| **Suche + Warteschlange** (Standard: rechts) | Suchfeld, „Abgespielt aus …“, aktueller Titel, „Als Nächstes“ | Die Titel sind **Kacheln, die man mit der Maus verschiebt**, um die Abspielreihenfolge zu ändern. Weiter gibt es X zum Entfernen, „Leeren“ und „Als Playlist speichern“. |
| **Player-Leiste** (Standard: unten) | Cover, Titel, Quelle, Herz · Zufall, Zurück, Play, Weiter, Wiederholen, Fortschritt · Warteschlange, Lautstärke, Qualitäts-Badge | Die **3 Elemente rechts** (Warteschlange, Lautstärke, Qualitäts-Badge) rücken **nach links** direkt hinter Titel-Info und Herz (grüner Pfeil im Screenshot). Das **Qualitäts-Badge wird wie bei Tidal übernommen**: Pille mit Akzentfarbe und Text aus der gerade gespielten Qualität, z. B. „16-bit 44.1kHz“, „24-bit 96kHz“, „AAC 320“. Steuerung und Fortschritt folgen rechts davon und nutzen die restliche Breite. |

- **Technik:**
  - Ein Qt-Quick-Controls-`SplitView`, waagrecht für die Spalten und senkrecht für die Player-Leiste. Die Breiten werden mit der Maus gezogen.
  - Jeder Seitenbereich steckt in einem `TidalDock.qml` mit kleiner Titelzeile und Menü: **Links andocken / Rechts andocken / Als eigenes Fenster lösen / Ausblenden**, für die Player-Leiste **Oben / Unten**.
  - Ein gelöster Bereich wird ein eigenes QML-`Window` (Position und Größe frei). Schließt man es, dockt es wieder an.
  - „Layout zurücksetzen“ stellt die Standardaufteilung wieder her.
- **Speichern:**
  - Neues Setting `tidal_layout` (Dict): `split` (Ergebnis von `SplitView.saveState()` als base64), pro Bereich `dock` (left/right/float/hidden), `width`/`height` sowie `x`/`y`/`w`/`h` beim gelösten Fenster, `player` (top/bottom).
  - Validiert in `core/settings.py`: Werte werden auf erlaubte Bereiche begrenzt, ein Fenster außerhalb aller Bildschirme wird beim Start zurückgeholt.
  - Gespeichert wird beim Loslassen eines Trenners bzw. beim Verschieben oder Schließen eines Fensters, mit kurzer Verzögerung (Timer). Der Speicherdialog der Einstellungsseite wird dabei nicht ausgelöst; das gleiche Muster wie `panel_width` / `panel_right`.

### 3b. Hauptbereich: mehr Nutzen auf der Fläche
Problem heute: ein riesiger Kopf (Cover und Titel), viel leerer Raum und für einen einzelnen Titel eine fast leere Tabelle. Neu:
- **Kompakter Kopf** (etwa 140 px hoch): Cover 120 px, daneben Titel, Künstler (anklickbar), Jahr, Anzahl, Gesamtdauer, Qualitäts-Badges (MAX/Atmos) sowie Label/© in einer Zeile.
- **Eine Aktionsleiste** im Kopf: Abspielen · Zufall · Zur Warteschlange · Herz · Download (Auswahl/alles) · **Als HTML-Linkliste speichern** · Link kopieren (Teilen) · Credits · Mehr.
- **Titeltabelle als Hauptinhalt**, dicht (Zeilenhöhe etwa 36 px):
  - Spalten: Auswahl ☐ · # · Titel + Explicit · Künstler · Album · Qualität · Länge · Aktionen beim Überfahren (Play, Herz, Zu Playlist, Zur Warteschlange, Download)
  - Spaltenbreiten lassen sich ziehen; Sortieren durch Klick auf den Kopf; Filterfeld über der Tabelle
  - Auswahlleiste: Alle / Keine / Umkehren / Shift-Bereich; erscheint, sobald etwas ausgewählt ist
  - Doppelklick spielt ab
- **Zusatzinfos in Reitern statt untereinander:** Titel | Weitere Alben | Ähnliche Künstler | Credits | Info. Damit ist die Tabelle immer sofort sichtbar.
- **Bei wenigen Titeln** (Single, EP) ist der Reiter „Weitere Alben“ gleich daneben als Raster mit kleinen Kacheln zu sehen, damit kein leerer Raum bleibt.
- **Start / Entdecken / Feed:**
  - Kachelreihen mit kleinen Kacheln (120 px), Zeilen einklappbar, „Alle“ öffnet das Raster
  - Feed als kompakte Liste mit Datum, Cover, Titel, Künstler und Typ, gruppiert nach „Neu / Letzte Woche / Dieser Monat“
- **Raster** (Sammlung, Suche): Die Kachelgröße ist per Schieberegler einstellbar und wird gespeichert (`tidal_tile_size`). Umschaltbar zwischen Liste und Raster.

### 3c. Playlist als HTML-Linkliste (ohne Download)
- Jede Playlist lässt sich auslesen und als **HTML-Seite mit Tidal-Links** speichern, ohne dass Lieder heruntergeladen werden: eigene, favorisierte, Tidal-Redaktion, fremde Nutzer sowie Mixes und Alben.
- Aufruf über den Knopf im Detail-Kopf, das Kontextmenü in der Playlist-Spalte oder eine Mehrfachauswahl, die mehrere Playlists auf einmal speichert.
- Neue Funktion `extras.tidal_linklist_html()` / `write_tidal_linklist()` im Stil von `playlist_html()`:
  - Kopf mit Cover, Name, Ersteller, Anzahl, Dauer und Link zur Playlist bei Tidal
  - Tabelle mit Nr., Cover, Titel, Künstler, Album, Dauer und Link `https://tidal.com/browse/track/<id>`
  - Filterfeld, „Alle in Tidal öffnen“
  - Ein Klick auf einen Titel öffnet ihn bei Tidal im Browser bzw. in der Tidal-App.
  - Die Datei ist eigenständig (`file://`, kein Server nötig).
- Speicherort: `<Download-Ordner>\Tidal\Linklisten\<Playlistname>.html`. Eine vorhandene Datei wird nicht stillschweigend überschrieben, sondern bekommt eine Nummer (`… (2).html`).

### Navigation (Inhalt)
  - Über dem Hauptbereich Zurück/Vor und die Reiter Start · Entdecken · Feed · Meine Sammlung; die Suche steht im rechten Bereich. Darunter liegt ein eigener `StackView`.
  - Meine Sammlung enthält Playlists, Alben, Künstler, Titel, Mixes und Videos.
- **Titellisten:**
  - einzelne oder mehrere Titel auswählen, Alle / Keine / Umkehren, Shift-Bereich wie in `PlaylistDialog.qml`
  - Play, Favorit, „Zu Playlist“, Download, Alles abspielen, Zufall
- Ein Klick auf Tidal-Inhalte schreibt außerdem den kanonischen Link über `videoLink(url)` in den Workflow.
- **Nicht angemeldet:** `EmptyState` mit „Bei Tidal anmelden“, das `backend.tidalLogin()` aufruft. `tidal.NOTICE` ist sichtbar.
- **[Ergänzung]** `IconPaths.qml`: fehlende Icons (Herz, Play/Pause, Zufall, Wiederholen, Warteschlange, Lyrics) als 24×24-Pfade ergänzen.

## 4. Tidal-Download-Chips (`WorkflowPanel.qml`)
Eine eigene `Flow`-Gruppe „TIDAL options“ (`visible: panel.tidalMode`) steht neben der YouTube-Gruppe.

| Option | Werte | Setting | tiddl |
|---|---|---|---|
| Qualität | Low / Normal / High / Max | `tidal_quality` (gibt es schon) | `-q` |
| Videos | Keine / Mit / Nur | `tidal_videos` (gibt es schon) | `--videos` |
| Videoqualität | SD / HD / Full HD | `tidal_video_quality` (gibt es schon) | `-vq` |
| Dolby Atmos | Aus / Mit / Nur | `tidal_atmos` | `--dolby-atmos` |
| Künstler-Singles | Ohne / Mit / Nur | `tidal_singles` | `--singles` |
| Lyrics einbetten | an/aus | `tidal_lyrics` | `metadata.lyrics` |
| .lrc erzeugen | an/aus | `tidal_lrc` | `download.write_lrc_file` |
| Cover einbetten | an/aus | `tidal_cover_embed` | `metadata.cover` |
| Cover-Datei | an/aus | `tidal_cover_file` | `cover.save` + `allowed` |
| M3U | an/aus | `tidal_m3u` | `m3u.save` + `allowed` |
| HTML-Player-Seite | an/aus | `tidal_html` | Yeal: `extras.write_playlist_page()` |
| Überschreiben | an/aus | `tidal_no_skip` | `--no-skip` |
| Metadaten neu | an/aus | `tidal_rewrite` | `--rewrite-metadata` |

- Das bisherige Qualitätsmenü bleibt und ist mit den Chips gekoppelt (gleiches Setting).
- **Fix für abgeschnittene Texte im Qualitätsmenü** (Screenshot: „Tidal Normal (AAC 320 …“, „Tidal Max (FLAC up to 2…“):
  - `AppMenu.qml` hat eine feste Breite (`implicitWidth: 200`). Neu richtet sich die Breite nach dem breitesten Eintrag: `width = max(200, breitester AppMenuItem.implicitWidth + Ränder)`, begrenzt auf die Fensterbreite.
  - Das gilt für alle Menüs in Yeal, ist also auch für lange Profilnamen nützlich.
  - Im Tidal-Modus zeigt das Menü statt „Manage profiles…“ den Eintrag „Tidal-Einstellungen…“, der zur Gruppe Tidal in den Einstellungen springt.
- Alle neuen Settings, also die Tabelle oben plus `tidal_volume`, `tidal_layout` und `tidal_tile_size`, kommen in `core/settings.py` mit Validierung. Sie werden außerdem in die Whitelist und Werteprüfung in `backend.py` aufgenommen.
- `core/tidal.py`: `build_command()` und `run_download()` werden erweitert; `_tidal_config()` in `backend.py` passt dazu.
- **[Ergänzung]** `SettingsPage.qml`, Gruppe „Tidal“: dieselben Optionen als Standardwerte und „Layout der TIDAL-DIY-Ansicht zurücksetzen“. Ein eigenes Setting `tidal_view` entfällt, weil die Knöpfe TIDAL Web und TIDAL DIY umschalten.

## 5. Isolierte tiddl-Konfiguration
- Bevorzugt: eine Yeal-eigene `config.toml` unter `<Yeal-data>/tiddl/`, tiddl wird mit `TIDDL_PATH=<Yeal-data>/tiddl/` gestartet.
- `auth.json` wird aus `~/.tiddl` dorthin gespiegelt. Wird das Token erneuert, wird nur die neuere Version (nach `expires_at`) zurückgeschrieben.
- Die globale tiddl-Konfiguration des Nutzers bleibt dadurch unberührt.
- Fallback, nur falls das mit tiddl 3.4.4 nicht sauber funktioniert: Yeal verwaltet ausschließlich die benötigten Schlüssel in `~/.tiddl/config.toml` und lässt fremde Einstellungen stehen.

## 6. Version und Dokumentation
- **Versionsregel (Nutzer, 2026-10-25):**
  - Vor jedem größeren Umbau oder riskanten Schritt wird der aktuelle Stand gesichert und die Version um eins erhöht.
  - Format: **0.9.1.01, 0.9.1.02, …** (letzte Stelle zweistellig), bis der Nutzer den nächsten Sprung (z. B. 0.9.2) vorgibt.
  - Jede Version wird lokal hinterlegt: ein Snapshot `_snapshots/<Datum>_v<Version>_<Grund>/` plus lokaler Commit und Tag `v<Version>`.
  - Auf GitHub (Push) gehen nur die vom Nutzer festgelegten Versionen wie 0.9.2, und nur auf seine Anweisung.
- Start: Snapshot `_snapshots/2026-10-25_v0.9.0.0_before-tidalgui/` (Stand jetzt), dann Version **0.9.1.01** für Schritt 1. Jeder weitere größere Schritt der Umsetzungsreihenfolge bekommt die nächste Nummer (0.9.1.02 …).
- Bei jeder Version werden `VERSION`, `yeal/__init__.py`, `pyproject.toml` und `CHANGELOG.md` gemeinsam gesetzt. „Unreleased“ (Stream to box) wandert in den ersten Abschnitt 0.9.1.01.
- Aktualisieren:
  - `docs/ARCHITECTURE.md`: `tidal_api -> tidal_backend -> QML` und die bewusste QtMultimedia-Ausnahme von Regel 5
  - `docs/TIDAL_EVALUATION.md`, `help/manual-de.html`, `help/manual-en.html`
  - `Yeal.spec`: neue QML-Dateien; QtMultimedia ist schon drin
- Android blendet die native TidalGUI aus; sie ist nur für den Desktop.

## 7. Tests / Definition of Done
- Neu: `tests/test_tidal_api.py`, `tests/test_tidal_gui_qml.py`. Bestehende Tidal- und Settings-Tests werden erweitert.
- Automatisch geprüft:
  - API-Parsing gegen einen Fake-HTTP-Server
  - BTS-Dekodierung
  - 401 → einmal `tiddl auth refresh` (Fake-tiddl) → Wiederholung
  - Playlist-ETag
  - neue `build_command`-Schalter
  - isolierter `TIDDL_PATH` und Zurückspiegeln von `auth.json`
  - Settings-Validierung, auch für `tidal_layout` (ungültige oder ausufernde Werte, Fenster außerhalb des Bildschirms)
  - HTML-Linkliste: Escaping, Links, keine Mediendateien, kein Überschreiben
  - Warteschlange: Verschieben, Entfernen und die Abspielreihenfolge danach (Logik im Backend getestet)
  - alle neuen QML-Dateien laden fehlerfrei
- Manuell mit dem angemeldeten Konto (`Run_Yeal_Debug.bat`):
  - Start, Entdecken, Feed und Sammlung laden
  - Suche „Deep Purple“
  - Album und Künstler öffnen
  - FLAC abspielen, dabei Spulen und Weiter
  - Lyrics
  - Favorit setzen und entfernen
  - Playlist erstellen, umbenennen und löschen
  - Titelauswahl herunterladen
  - jeden Chip einmal mit einem kurzen Album testen
  - Bereiche verschieben, in der Größe ändern und als Fenster lösen; Yeal neu starten, die Aufteilung ist wieder da; „Layout zurücksetzen“
  - Warteschlange per Ziehen umsortieren, die Reihenfolge stimmt beim Weiterspielen
  - eine eigene und eine fremde Tidal-Playlist als HTML-Linkliste speichern und die Links öffnen
  - Qualitätsmenü im Workflow: alle vier Einträge vollständig lesbar
  - Player-Leiste: Warteschlange, Lautstärke und Qualitäts-Badge links; das Badge zeigt die echte Qualität
  - Umschalter YouTube | TIDAL Web | TIDAL DIY: Jede Ansicht behält ihren Zustand; Wiedergabe in DIY und Wechsel zu Web pausiert gemäß `single_playback`; schmale Sidebar zeigt die Kurzbeschriftung
  - `yeal.log` prüfen
- Danach `Test_Yeal.bat` und `Build_Yeal_Exe.bat`, dann die EXE noch einmal mit TidalGUI und Wiedergabe testen.
- Jede Zwischenversion wird nach ihren Tests lokal committet und getaggt (`v0.9.1.xx`). Kein Push ohne ausdrückliche Freigabe; Push nur für vom Nutzer festgelegte Versionen (z. B. 0.9.2).

## Umsetzungsreihenfolge (alles in 0.9.1.0, aber in prüfbaren Schritten)
1. Snapshot anlegen, `AppMenu`-Breite korrigieren, Umschalter mit 3 Knöpfen und leere `TidalHome.qml`. Damit ist der Umschalter sofort testbar.
2. `tidal_api.py` + Tests (Lesen, BTS, Refresh, ETag).
3. Download-Chips: `build_command`, isolierter `TIDDL_PATH`, Settings, `WorkflowPanel`.
4. `tidal_backend.py` mit Seiten-Laden; Hauptbereich (3b) mit Playlists-Spalte und Navigation.
5. Player, Warteschlange mit Ziehen, Player-Leiste mit Badge, Lyrics.
6. Favoriten und Playlist-Bearbeitung, HTML-Linkliste.
7. Docks, Fenster lösen, Layout speichern.
8. Doku, Version, EXE-Build, manueller Gesamttest.

Nach jedem Schritt laufen `Test_Yeal.bat` und ein kurzer Start der App.

## Risiken und Gegenmaßnahmen
- **TIDAL Web lässt sich nicht direkt pausieren** (fremde Seite in WebView2). Für `single_playback` pausiert Yeal dort per `runJavaScript` alle `audio`/`video`-Elemente; klappt das nicht, wird das als Hinweis dokumentiert.
- **Token-Refresh:** Für die API wird `tiddl auth refresh` immer mit dem globalen `~/.tiddl` ausgeführt. Die Yeal-Kopie für Downloads wird danach neu gespiegelt, damit es keine zwei abweichenden Tokens gibt.
- **Inoffizielle Tidal-API:** Jeder Bereich (Feed, Seiten, Lyrics) fängt Fehler einzeln ab und zeigt dann einen Hinweis statt einer leeren Seite. Ein Ausfall des Feeds blockiert also nicht den Rest.
- **Qualitäts-Badge:** Es zeigt die tatsächlich gespielte Qualität. Wurde Hi-Res für die Wiedergabe auf 16-bit zurückgestuft, steht dort „16-bit 44.1kHz“ und der Tooltip nennt den Grund.
- **Umfang:** sehr groß für eine Version. Die Schrittfolge oben hält jeden Zwischenstand lauffähig; Jeder größere Schritt ist eine eigene lokale Version (Snapshot + Commit + Tag, siehe 6).

## Leitlinie für die Umsetzung
Vorhandenes erweitern statt duplizieren:
- `core/tidal.py`
- der Tidal-Jobpfad
- `PlaylistDialog.qml` (Auswahl-Logik)
- `extras.write_playlist_page()`
- das Settings-System
- die vorhandenen QML-Bausteine

Die API-Schicht bleibt unabhängig von tiddl-Interna. tiddl dient nur für Auth-Refresh und Downloads.
