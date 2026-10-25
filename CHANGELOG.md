# Changelog

## 0.9.1.12
- **Player for downloads as a solar system:** the oval player is the **sun** in the middle with a glow that breathes with the music; the **planets** on the orbits around it unfold into cards and fold away again: **Library** (left), **Queue** (right), **Played** (below), **Settings** and **Speaker** (above). Opening a planet moves the sun and its orbits over so that nothing is covered; several planets can be open at once. The sun button in the corner folds all planets into the sun (`local_orbit`).
- **Volume and jumping always visible:** under the oval there is now a volume slider (click the speaker icon to mute, mouse wheel on the oval still works) and "10 s back / ahead" buttons; the text buttons are brighter and wrap into more lines instead of running out of the window.
- **Player colour:** green, blue, red, yellow, purple, orange, pink, cyan or white for the band, the loop and the dot (`tidal_player_color`): colour dots in the Settings planet and in Settings > Tidal > TIDAL DIY layout, and the COLOR button under the oval cycles them. The volume highlight is yellow, or orange when the player itself is yellow.
- **Played songs:** a list of the songs of this session, newest first (tab "Played" in the TIDAL DIY panel, planet "Played" in the player for downloads); a click plays it again.
- **Speaker planet:** lists the speakers / TVs found in the network, searches again, plays the current song there, pause / continue / stop.
- Tests: colours and orbit setting, theme colours, the sun making room for opened planets, played list.
- No EXE built.

## 0.9.1.11
- **Player for your downloads** (concept: the oval design as an own player for the downloaded songs; chosen with the user). New fourth button **Player** next to YouTube / TIDAL Web / TIDAL DIY, and **Play in Yeal player** in the menu of a download. It shows the oval track player with a library of all finished audio downloads (single files and the songs inside downloaded albums / playlists / folders, newest first; names like "NN - Artist - Title" become title and artist) and a filter field. Own volume (`local_volume`); starting it pauses the web players and the TIDAL DIY player and the other way round (Settings: single playback).
- The loudness profile around the oval is there from the first second: the whole file is scanned in the background (`QAudioDecoder`), the played part glows. **STREAM** plays the current song on the speaker / TV chosen under "Stream to box" (`Backend.streamFile`, the song then pauses here).
- **Drop to play:** titles, albums and playlists dragged onto the TIDAL DIY player (bar or oval) replace the queue and play at once; dragging into the queue keeps adding them.
- Fixed: the playlist panel of the track player showed the wrong tab content once the library tab was added (tab order).
- Tests: `tests/test_local_player.py` (file names, library, playing a generated sine file, loudness profile of the whole file, "Play in Yeal player", single playback between the three players), play-now tests.
- No EXE built.

## 0.9.1.10
- **Track player, band around the oval: the song itself.** After the first test the band was only a running level. New default **VIS SONG**: the loudness of the whole song is laid around the oval (start at the bottom centre, the dot is the playhead); the part already played glows, the part to come is quieter, and a loud passage of the song is a thick place in the band. For a song that plays from the start the profile grows while it plays (a jump ahead leaves a gap until that part was heard). **VIS FLOW** is the running level of 0.9.1.09, **VIS OFF** hides the band; the VIS text button cycles the three, and Settings > Tidal > TIDAL DIY layout has chips for them (`tidal_player_vis_mode`, replaces `tidal_player_vis`).
- Tests: loudness profile (position in the song, gaps, reset per song), mode setting.


## 0.9.1.09
- **Track player for TIDAL DIY** (design after the concept video): the player as a running track. Switch it by right-click on the player bar or in Settings > Tidal > TIDAL DIY layout (the classic bar stays the default). The dot is the playhead and runs once around the oval while the song plays; click or drag on the loop to jump. The **green band around the inner oval is the real level of the music** (taken from the decoded audio, Qt `QAudioBufferOutput`): the louder, the thicker; VIS switches it off. **VOL** turns the band yellow and shows the volume as a big number, the mouse wheel over the oval changes it too. Text controls under the oval: repeat off / all / single, shuffle, like, time and quality, PLAYLIST (queue with jump and remove, playlists, search results), LYRICS (timed, click a line to jump), VIS, VOL. No equalizer: Qt's player has none, it would need an own audio engine.
- **Drag titles into the queue:** titles, albums, playlists and mixes dragged from the pages (or a whole selection) land in the queue where the line shows; albums and playlists bring all their titles; an empty queue starts with the first one. The same drag still downloads when dropped on the workflow panel.
- **Download tile, folder button:** it opens the downloaded song itself, or the folder of the album / playlist / artist, or the video - not only the Tidal folder (`tidal.downloaded_target`); folders are opened, not just selected in their parent.
- **Track table:** the column headers (title, artist, album, time) sit exactly over the cells of the rows and move with them when a column edge is dragged (the rows kept 112 px less room for the hidden action buttons, and the grips shifted the header cells by 16 px).
- Tests: level measurement from audio buffers, queue insert / enqueue, drag payload, column alignment while resizing, folder target, new settings.
- Not built: equalizer, hand test with sound and a signed-in account. No EXE built (the last build is 0.9.1.06).


## 0.9.1.08
- **YouTube download tile:** the hint "The browser login could not be read ..." is no longer shown when the download worked (it only matters when the download fails, then the error is shown as before).
- **TIDAL download tile:** shows the song, album or playlist name with the artist (or creator) and the cover instead of `playlist/7e9b7ad6-...`; albums and playlists also show "n of N" while they download. The technical id is never shown in the list. If the lookup fails (offline, signed out) the tile keeps the link and the download is not affected (`TidalApi.describe`, `Engine.tidal_meta`).
- **TIDAL HTML player page:** every title has its own cover and artist; the id is only a small link `#id` to the title at TIDAL. While a title plays, the cover in the page header, the "now playing" line and the browser tab title follow the song at once (`tidal.match_tracks` pairs the files with the TIDAL titles by name, then by order).
- **Long tracks cut into songs (chapters / timestamps):** every cut is placed **0.5 s earlier** than the listed time (checked with a real file: the first song ends 0.5 s sooner, the last starts 0.5 s sooner, middle songs keep their length; a song is never made shorter than 1 s). The cover stays in every song.
- **Album page of cut songs:** the cover is shown for every song and in the page header (before the squares were empty).
- Tests: cut shifting incl. the step order inside yt-dlp, the cookie hint, album page cover, TIDAL job description, `TidalApi.describe`, `match_tracks`, HTML page with ids and covers.


## 0.9.1.07
- **TIDAL options: smaller and without the double quality control.** The quality menu button below the options is gone for TIDAL; the quality is the first tile of the TIDAL options. The option groups are small tiles in **two columns** (caption + current value); the choices of the opened group appear below, across the full width, one group at a time.
- **The whole TIDAL options block can be folded** with a click on its heading; folded it is one line with the current quality, videos and extras (remembered, setting `tidal_opts_collapsed`). A small settings button in the heading opens Settings > Tidal. The values are the defaults of every download (the same settings as in Settings > Tidal).
- Tests: tiles, one open group at a time, overview line, folding (`tests/test_tidal_gui_qml.py`); manuals updated.


## 0.9.1.06
- Tests for the TIDAL DIY play queue and player: moving, removing and inserting rows keeps following the playing track, shuffle only touches the upcoming titles and restores their order, repeat (off / all / one), what happens at the end of the queue, volume limits (`tests/test_tidal_player.py`, 22 tests, no audio device needed).
- Tests for the HTML link list: text and links are escaped, only https TIDAL links appear, no media files are referred to, an existing page is never replaced, an unwritable folder gives no crash.
- Manuals (English and German): new chapter TIDAL (three views, TIDAL DIY, arranging the view, drag and drop, TIDAL options). `docs/ARCHITECTURE.md` describes the TIDAL DIY layers and the QtMultimedia exception; `docs/TIDAL_EVALUATION.md` has the outcome.
- `Yeal.spec` checked: QtMultimedia and QtQuick.Window stay in the bundle, all QML files are packed as a folder (the new `TidalDock.qml` etc. need no change).


## 0.9.1.05
- **TIDAL DIY: areas can be arranged.** The playlist column and "search and queue" can be docked on the left or the right, detached into their own window or hidden (menu button in the header of each area, or right-click on it). Two buttons next to the page tabs show / hide them again, a third resets the arrangement. A detached window can be moved and resized freely; closing it docks the area again. A window left on a screen that is gone comes back to the main screen. The player bar moves to the top or bottom with a right-click. Widths, sides, window positions and the player position are remembered (`tidal_layout`); Settings > Tidal > "TIDAL DIY layout" resets them.
- The queue button (player bar and page tabs) uses the three-line icon of TIDAL.
- Fixed: settings that are objects (the layout) sent from QML were silently ignored by `Backend.setSetting`; they are converted now.
- Tests: layout changes are saved, validated and reset (`tests/test_tidal_gui_qml.py`). Not yet done: tests for the queue / player logic and the link-list writer, manuals, EXE build, hand test of the whole view.


## 0.9.1.04
- **TIDAL DIY view** (`TidalHome.qml`): playlists column | navigation tabs (Start, Explore, Feed, My collection, back/forward) with the page | search and queue, player bar below. Albums, playlists, mixes, artists, genre pages, search results and "All" lists open as pages; titles play in Yeal's own player. Context menu on every tile, row and playlist: play, play next, add to queue, open, add to / remove from collection, add to playlist, download, save as HTML link list, copy link, open in TIDAL Web. Not signed in: sign-in prompt with the subscription notice.
- **Drag and drop to download:** drag a title, album, playlist or mix from the TIDAL DIY view onto the workflow panel (a "Drop to download" frame shows the target). TIDAL links dropped there, also from the embedded web players or other programs, are added to the downloads at once; other links fill the link field as before. Several picked playlists are dragged together.
- **TIDAL options are collapsed:** every group (quality, videos, video quality, Dolby Atmos, artist singles, extras) is one line with its current value; the chips appear below it only when the group is opened, one group at a time.
- Playing in TIDAL DIY pauses the YouTube and TIDAL Web players (setting "single playback"); "Open in TIDAL Web" switches to the web view and loads the link.
- Fixed: artist page property clashed with a built-in item property; track length and quality badge no longer warn when a value is missing.
- Tests: all new Tidal components load without QML warnings (`tests/test_tidal_gui_qml.py`). Not yet done: docks / own windows and saving the layout (`tidal_layout`), manuals, EXE build.


## 0.9.1.03
- New **TIDAL options** in the workflow (shown for TIDAL Web and TIDAL DIY, like the YouTube options) and in Settings > Tidal > Download options, all as chips:
  quality (Low / Normal / High FLAC / Max Hi-Res), videos (none / with / only) and video quality (SD / HD / Full HD), Dolby Atmos (off / with / only), artist singles (albums only / with singles / only singles; only used for artist links), lyrics in the file, lyrics as .lrc, cover in the file, cover image, M3U playlist, Yeal player page (HTML), overwrite existing files, rewrite tags.
- Tidal downloads now run in Yeal's own tiddl folder (`<Yeal data>\tiddl`, `TIDDL_PATH`): the extras go into a config.toml there, so your own tiddl setup is never changed. The sign-in stays the one of tiddl; a token renewed during a download is copied back (the newer one always wins).
- "Player page (HTML)": after an album or playlist download Yeal writes its player page into that folder (relative links, works from disk).
- New defaults: lyrics and cover are embedded into Tidal files (both can be switched off).
- Tests: Tidal engine tests now also run on Windows (a .cmd wrapper starts the fake tiddl).

## 0.9.1.02
- TIDAL DIY data layer `core/tidal_api.py` (standard library only, no new dependency): start page, explore and genre pages, feed (new releases of followed artists, monthly history mixes), search, album (with credits), artist (top tracks, albums, singles/EPs, videos, similar artists), playlists, mixes, favorites, own and favorited playlists, lyrics (timed when Tidal has them) and the playable stream link for Yeal's own player. Writing: add/remove favorites, create/rename/delete playlists, add/remove playlist tracks (with Tidal's playlist version check, ETag). Uses the existing tiddl sign-in; an expired token is renewed once with `tiddl auth refresh`. Answers are cached for 5 minutes, at most 2 requests run at the same time.
- Playback quality: with the tiddl sign-in Tidal streams at most FLAC 16-bit / 44.1 kHz for playing (also for MAX albums); the quality badge shows what is really played. Hi-res downloads through tiddl are not affected.
- Tests: `tests/test_tidal_api.py` (fake Tidal server).

## 0.9.1.01
- Start of the TIDAL DIY work (0.9.1): the player switch next to the workflow now has three buttons, **YouTube | TIDAL Web | TIDAL DIY**. TIDAL Web is the embedded TIDAL web player as before; TIDAL DIY is Yeal's own TIDAL view (being built step by step; for now it shows the sign-in with the subscription notice). In a narrow bar the buttons read "Web" / "DIY", the tooltip gives the full name. The Tidal download options apply to both Tidal views. After a Tidal sign-in Yeal returns to the view it came from.
- Menus are as wide as their longest entry (at least 200 px, at most the window): the Tidal quality menu no longer cuts off "Tidal Normal (AAC 320 kbps)" and "Tidal Max (FLAC up to 24-bit / 192 kHz)". In Tidal mode the menu offers "Tidal settings…" (opens the Tidal group in Settings) instead of "Manage profiles…".
- Fixed: the player buttons asked for logo files that do not exist (QML warnings); they show icon and name.
- Versions: interim versions are numbered 0.9.1.01, 0.9.1.02, …; each is kept locally (snapshot, commit, tag).

### Also in 0.9.1.01 (was Unreleased)
- **Fixed: Tidal sign-in showed the wrong page** (the GitHub page of tiddl). Yeal took the first web address in tiddl's output, which can be an update notice. Only the Tidal link (link.tidal.com / login.tidal.com, with or without `https://`) is used now (`tidal.find_login_link`, tests in `tests/test_tidal.py`).
- **Tidal sign-in inside Yeal.** Settings > Tidal > Sign in now opens tiddl's device-login link in the embedded TIDAL view (Downloads page switches to TIDAL) instead of the system browser: the user signs in or confirms there, tiddl notices the confirmation by itself and Yeal switches the view back to the TIDAL start page. Yeal never reads the Tidal session or password. Without the embedded view the link opens in the system browser as before.
- **Fixed: Tidal sign-in never opened the browser** (Settings stayed on "Waiting for the browser..."). The login link was handed to the GUI thread with `QTimer.singleShot` from a plain Python thread, which never fires; it now uses a Qt signal. The link is also shown in a message in case no window opens.
- Tidal login check: also accepts `access_token` and the old `.tiddl_config.json`; the "Not signed in" message now says that the login inside the TIDAL player is separate from the download login and shows the folder where Yeal looked for the tiddl login.
- **Download options now differ between YouTube and TIDAL.** While the TIDAL player is shown (or the link in the field is a Tidal link) the profile button lists the Tidal quality steps (Low AAC 96, Normal AAC 320, High FLAC 16-bit, Max FLAC up to 24-bit/192 kHz) instead of the yt-dlp profiles, the Video/Audio switch and the YouTube-only chips are hidden, and a label shows which source the options belong to. The chosen quality is stored in the job (`DownloadOptions.tidal_quality`) and passed to tiddl as `-q`; before, only Settings > Tidal counted and the download dropdown had no effect. Test in `tests/test_tidal.py`.
- Tidal downloads are sorted into sub folders of `<download folder>\Tidal\` by default: **Singles** (single songs, `Artist - Title`), **Playlists** (`<playlist name>\01 - Artist - Title`; mixes as `Mix <id>`), **Videos** and **Albums** (`Artist\Album\01 - Title`; artist links download all albums). Done with tiddl's `--output` template per kind of link (`tidal.OUTPUT_TEMPLATES`).
- **Fixed: Tidal videos were never downloaded.** tiddl skips videos by default (`--videos none`), even a link to a single video, so such a download ended without a file. Yeal now always allows a single video link and passes the new settings to tiddl.
- Settings > Tidal: **Audio quality** now looks like the TIDAL app (Low with a 96 / 320 kbps choice, High 16-bit 44.1 kHz, Max up to 24-bit 192 kHz; adaptive streaming does not apply to downloads). New **Video quality** (SD / HD / Full HD, default Full HD) and **Videos in albums and playlists** (Skip / Include / Only videos, default Include). Tests in `tests/test_tidal.py`.
- The embedded TIDAL view now puts the link of an opened track, album, playlist, mix, artist or video page into the download field by itself, like the YouTube view does ("Use this link" still repeats it).
- Settings page regrouped by function into nine groups, all collapsed at first: **Appearance & browser** (theme, YouTube browser, ad blocker), **Downloads** (save to, drive question, parallel downloads, speed limit, gentle mode), **Output** (MP3 tags, HTML pages), **Login & network** (browser login, proxy), **Streaming**, **Tidal**, **Download engine**, **Advanced** (custom yt-dlp options and the Admin vault, now a collapsible item) and **Info**. Every item is still a one-line entry that opens on click; group headers show a pointer cursor.
- Settings > Info > Module licenses lists the modules as soon as the item is opened (no more "Show" link).
- The question that appears when an external drive is found now shows the **current download folder** first. **Continue** keeps it, **Change folder...** opens the drive/folder chooser (with a new **Other folder...** button for any folder). A small **Don't ask again** button turns the question off; the new switch Settings > Downloads > "Ask about the download folder when a drive is found" turns it back on (`ask_drive_dialog`). `tests/test_settings_layout.py`.
- New **Stream to box**: finished downloads can be played on speakers and TVs in the Wi-Fi/LAN (UPnP/DLNA, e.g. KEF LS50 Wireless I and II). A button under the action icons of each finished download (and the right-click menu) starts the stream on the saved device; right-click the button or use "Stream to another device…" to choose one. The device dialog searches the network (SSDP), lists the devices, lets you add an address by hand and offers Pause / Resume / Stop and a volume slider. Settings has a new **Streaming** group: chosen device, manual addresses, start volume, search time and a fixed media-server port for the firewall. No new dependency: `core/streaming.py` uses only the standard library; the file is served by a small token-protected HTTP server (Range requests, private networks only) and the speaker is controlled by SOAP calls. If the speaker never fetches the file, Yeal points to the Windows firewall. Desktop only for now (the Android build hides it). Tests: `tests/test_streaming.py` (fake speaker).

## 0.9.0.0
- Standing rule: Yeal always starts in the default view (workflow in the sidebar, embedded YouTube browser on the Downloads page), whatever was saved before. The header button and the Settings switch still hide the browser, but only until the next start. `tests/test_default_gui.py`.
- New: Tidal downloads. Paste a Tidal link (track, album, playlist, artist, mix or video from tidal.com / listen.tidal.com) like any other link; Yeal hands it to the separate helper program tiddl (https://github.com/oskvr37/tiddl, Apache-2.0, installed with `pip install tiddl`, not bundled) and saves the files to `<download folder>\Tidal\`. Progress, cancel and retry work like for other downloads.
- Tidal only works with an active Tidal subscription. Every user signs in with their own Tidal account (Settings > Tidal > Sign in opens the Tidal device login in the browser; Yeal never sees the password). This is stated in Settings > Tidal and in Settings > Info. The downloads are for personal use and subject to Tidal's terms of use.
- New Settings group "Tidal": subscription notice, tiddl status with Choose / Automatic / Download, account sign-in and sign-out, quality (Low AAC 96, Normal AAC 320, High FLAC 16-bit, Max FLAC up to 24-bit) and parallel tracks (default 2, maximum 4, kept low on purpose because many parallel requests can get an account blocked).
- tiddl is listed in the module licenses as an optional, separately started helper.
- Version number format is now four-part (0.9.0.0).
- New direct Download button in the header button bar of the main view (next to the title, in the free spot before the browser/side/folder buttons). Right-click it to choose the look (icon only / icon and text) and the position (next to the title / end of the bar); the choice is remembered (`dl_button_style`, `dl_button_pos`).
- USB drive detection: a drive that Windows announces before its file system is readable is now rescanned for up to a minute instead of being missed for the whole session; drives down to 64 MB are accepted (was 1 GB); a different stick that gets the same drive letter is noticed; a removed drive is offered again when plugged back in; write access is checked with a real write probe; skipped drives are logged with the reason in `yeal.log`.
- Fixed `dist\Yeal.exe` showing the splash screen and then never opening the window: the Qt WebView2 plugin (`plugins\webview\qtwebview_webview2.dll`) was not packed into the exe, so the embedded YouTube view failed when it was created right after the splash. `Yeal.spec` now packs it and stops the build if it is missing. The exe also writes `%APPDATA%\Yeal\yeal.log` (previous run: `yeal.prev.log`) with Python errors, native crashes and Qt/QML messages.
- Settings page: every setting is a collapsed one-line item (icon, name, current value) that opens on click to edit; the groups have icons too. No more endless rows.
- New setting "Create HTML pages" (Server / File / Both, default Both). Both writes `name.html` (online player, opened through Yeal's local server) and `name.file.html` (standalone, works from disk), linked to each other. Pages always link to the media by file name only (same folder, no full path). "Open saved HTML pages" now defaults to the local server for new installs; in File mode the standalone page is opened.
- Description pages no longer embed the online YouTube player for videos whose owner forbids embedding (YouTube showed "This video is not available" inside the page); the local file player is used.
- Playlist dialog shows every video as a thumbnail tile (number, duration, tick mark) and offers Select all / none / Invert, single and Shift-range selection. Only the ticked videos are downloaded.
- The playlist HTML page has its own layout: video playlists get a tile grid with thumbnails under a sticky player, audio playlists a cover header with a track list; both have Play all, Shuffle and a title filter.
- A video watched inside a YouTube playlist now offers "Use playlist" next to "Use this link": the whole playlist is listed, saved in `Playlists\<playlist name>\` with the playlist HTML page. Before, only the single video was taken (the playlist part of the link was cut off).
- Playlist rows show a third bar for the whole playlist (video n/N) above the download bar of the current video and the conversion bar.
- The browser login is checked once before a download. If it cannot be read, the download continues without it (before, a playlist silently skipped most videos). Playlists that could not be fully downloaded now say how many videos were skipped.
- Fixed downloads failing with "Failed to decrypt with DPAPI" (yt-dlp issue 10927): Chrome and Edge protect their cookies, so the browser login cannot be read. Yeal now retries automatically without the browser login, shows a clear note, and explains that Firefox is the reliable choice for protected videos.
- Fixed the image extractor preview when switching videos: each selection gets fresh filmstrip files, the player resets to the new source, and a late result from the previous selection can no longer replace the current preview.
- The embedded YouTube browser now presses visible ad-skip controls automatically with both German (`Überspringen`) and English (`Skip` / `Skip ad`) labels, independently of the experimental ad blocker.
- First start now asks for the browser used by protected YouTube downloads (Chrome is preselected) and the download folder.
- Selected segmented options and enabled switches use Yeal's blue accent consistently throughout Settings.
- Settings changes are staged. The page shows Save / Discard and asks whether to save, discard, or stay when the user leaves Settings or closes Yeal; no prompt appears when nothing changed.
- New Admin vaults start with password `1234` and require a private replacement before YouTube/browser login entries can be added or viewed. Existing vault passwords are preserved.
- Every group on the Settings page can now be expanded and collapsed.
- The download-engine section shows the detected ffmpeg and Node.js versions and full executable paths. Both helpers can be selected manually, reset to automatic detection, or opened on their official download page for updates; manual paths are saved and used immediately.
- The Info group now contains the complete Yeal version history and a versioned license overview for the runtime modules. The changelog is also included in packaged builds.
- Protected YouTube downloads now explain that Google can reject sign-in inside the embedded view and direct the user to the supported external-browser cookie workflow. The YouTube toolbar can open the current page in the system browser.

## 0.8.14
- Saved HTML pages can now open directly from disk (`file://`, the independent default) or through Yeal's optional local Python server (`127.0.0.1`). The server mode keeps embedded YouTube/Vimeo players working while Yeal runs; local-file mode needs no server or running app and links to the original site instead. Switching back to local-file mode also stops an active HTML server.
- Added the setting under Downloads and documented both modes in the German and English HTML manuals.

## 0.8.13
- Album with tracks: the HTML page (player + track list) is now also written into the album folder as `<folder name>.html` when Description or Online player is on.
- Album playlist (.m3u8) is written the way VLC and Windows players expect: `#EXTENC:UTF-8`, CRLF line ends, single-line titles. (If VLC still refuses it, please send the VLC error text.)

## 0.8.12
- YouTube view: dialogs (export to MP3, audio choice, playlist, ...) no longer interrupt the page. The web view is no longer destroyed while a dialog is open (that restarted the video); it is collapsed under the dialog and expanded again, and the page keeps playing. If the view comes back with a wrong size it is re-laid out, and only after repeated failures re-created as before.

## 0.8.11
- Browser view: Back / Forward work again after a dialog. The web view is re-created when a dialog opens, which wiped its history; Yeal now keeps its own page history as a fallback. Back uses a proper left arrow icon.
- Browser view: the sound is muted during ads and restored afterwards again (this was lost when WebPane.qml was overwritten); the ad skipper no longer leaves the video muted.
- Browser view: the dark-theme reload runs at most once per theme change, so a YouTube page that rewrites its own theme cookie cannot reload endlessly.
- Smaller exe: unused Qt modules (ShaderTools, QuickTest, Timeline, VectorImage, Particles, XmlListModel, LocalStorage), unused platform plugins, werkzeug / watchdog / pyreadline3 and editor backups are no longer packed (about 3.5 MB). `Build_Yeal_Exe.bat slim` also leaves out Qt's bundled FFmpeg (about 8 MB more; the preview player then uses the Windows media backend).
- New README with all functions, and docs/VERSIONING.md (every version is tagged and pushed).

## 0.8.10
- Drive dialog is now a dropdown. The top entry is always the Windows Downloads folder (default); the found drives follow, each with free/total space (TB for big disks).
- All non-system drives are found now, also USB SSDs/HDDs that Windows reports as SATA/SCSI/NVMe (e.g. WD_BLACK4TB on G:) and secondary internal disks. Detection uses the Win32 drive list instead of PowerShell bus-type filters.
- Pseudo drives are hidden: volumes under 1 GB (the 16 MB "Ugreen Driver" CD volume, empty card readers).

## 0.8.9
- Playlists: a playlist link now opens a list of all entries. Tick single entries, several (Shift+click for a range, Ctrl+A for all) or everything, then start the download.
- Playlists are always saved in `Playlists\<playlist name>\` inside the download folder, files numbered like in the playlist (001 - title ...).
- A playlist page `<playlist name>.html` is written into that folder: one player, the entry list below it, click to play, next entry follows automatically, link to each entry's own page when one was saved. "Open page" on the finished download opens it.

## 0.8.8
- Live streams: when a single link is a running live stream (the same "LIVE" the player shows, read from the stream data), the app asks whether to record it and for how long (until it ends, 15 min, 30 min, 1 h, 2 h or a number of minutes). The time limit needs ffmpeg.
- The link check before a download now runs for every single video link (it was audio-MP3 only).

## 0.8.7
- YouTube view: the sound is muted while an ad runs and comes back when the video starts (the mute state you had before the ad is restored; if you had muted the video yourself it stays muted). Works independently of the experimental ad skipper, which no longer mutes by itself.

## 0.8.6
- External drives: every newly connected drive is offered one after the other (before, only the first one was offered). USB SSDs that Windows reports as SCSI/UASP are found too.
- Drive and audio dialogs are wider; the drive text no longer breaks in the middle of the sentence.
- Start: the YouTube view stays hidden behind a large 50 % transparent Yeal logo until the page is loaded in the right theme, so there is no white flash when it switches to dark.

## 0.8.5
- Audio choice dialog: new order MP3 (default and recommended, always 320 kbps, never lower: otherwise no download), AAC (M4A), Original stream, and FLAC when the source is lossless.

## 0.8.4
- When the link in the field has a tracklist (timestamps) in its description, the app suggests saving it as an album (Tracks only / Tracks + full file / No thanks). Checked once per link in the background.

## 0.8.3
- Album choice in the bar: the "Album tracks" chip is blue like the others; "Tracks only" / "Tracks + full file" appear only when it is switched on.

## 0.8.2
- External drives: when a USB/external drive is plugged in (or already connected at start), the app offers to save downloads there. After you confirm it creates a folder in the root of the drive (default name "Yeal", editable before it is created) and uses it as download folder. "Not now" asks again next start, "Don't ask again" remembers that drive.

## 0.8.1
- Album: choose Whole / Tracks / Both (bar and profile editor). Tracks are named and tagged with the song titles from the tracklist; "Tracks" removes the full file after the split.
- The HTML page fits portrait videos (no black side bars).
- Audio format hint: MP3 is encoded at up to 320 kbps (as high as the source allows); order stays MP3, AAC, Opus, FLAC, Original.

## 0.8.0
- Menu buttons (Downloads / Profiles / Settings) sit in one row at the top of the bar next to the browser view.
- The download list scrolls and is grouped by date (Today, Yesterday, weekday, Week NN, year). Click a group header to collapse/expand it; the trash icon clears the finished items of that group.
- Finished downloads are remembered between starts (last 500). Adding a link that was already downloaded asks "Download again?" (or open the existing file).
- Collapsed groups and the list filter are saved with the other settings.
- Dialogs are confined to the content area next to the bar instead of the whole window.

## 0.7.9
- Browser view: the link of the playing video is now taken over reliably. YouTube switches videos without a page load and the web view did not always report it, so the address is read from the page once a second; a new video fills the link field (once per video, not again after you cleared it).

## 0.7.8
- Browser view: Back and Forward work again. The buttons were greyed out because the web view does not report YouTube's in-page navigation; they are now always active and use the page's own history. Added Alt+Left, Alt+Right and F5.

## 0.7.7
- When a download fails, the tile and the details dialog say in plain words why it stopped automatically and what to do (rate limit, private/age-restricted/members video, country block, removed video, no connection, ffmpeg, disk, YouTube change). The technical line from yt-dlp stays available below it.

## 0.7.6
- Optional parts no longer fail a download: if subtitles (e.g. HTTP 429), the cover image or the chosen quality are not available, Yeal continues without them (or with the best available quality) and keeps a hint on the tile.
- Click a download tile (or menu > Details) to open a dialog with state, hints, the full error text, copy and retry.
- Workflow header: the "Clear finished" button is icon-only in the sidebar (no overlap).

## 0.7.5
- Browser view: the link of the video you open is put into the link field automatically and replaced when you open the next one; nothing downloads until you press Download. The link is cleaned (only the video id; no mix/radio list, time stamp or tracking) and a hint line shows where it came from.

## 0.7.4
- Ad blocking is marked experimental and is now off by default (Settings > Browser).

## 0.7.3
- Settings > Admin: stored logins (service, user, password, note), locked with an admin password. Stored in the user's data folder, encrypted with Windows DPAPI plus a key derived from the admin password - copying the program or the file to another PC/account does not carry the logins. Auto-lock after 5 minutes, slowdown after wrong guesses, clipboard cleared after 30 s. Initial password as requested; the page recommends changing it. "Delete all logins" also removes the YouTube sign-in of the browser view at the next start.

## 0.7.2
- Ad blocking in the YouTube view (Settings, on by default, restart needed): a small local filter proxy refuses known ad/tracker domains (built-in list plus optional `blocklist.txt` in hosts format in the data folder; HTTPS is only tunnelled, never opened). A script hides ad slots on YouTube, presses "Skip" and jumps to the end of unskippable video ads.
- Download menu: "Play in VLC (fullscreen)" when VLC is installed.

## 0.7.1
- Audio: always picks the highest-bitrate source stream; the format choice dialog now appears from 120 kbps and explains that MP3 is a lossy copy of the source (Original / AAC keep more quality).
- New option **Lyrics**: looks up the song text online (LRCLIB, no key), else uses the captions. Saved as TXT, as LRC with timing, written into MP3/M4A tags (video: SRT subtitle file for VLC and other players) and shown in the HTML page, highlighted and clickable together with the local player.

## 0.7.0
- New layout (Windows): one bar with the navigation on top and our workflow (link, options, download, list) below, the YouTube view fills the rest. Drag the bar's edge to set its width; the swap button (workflow header) moves the bar to the other side. Width and side are remembered.
- Workflow controls moved into their own component (`WorkflowPanel.qml`); without the browser view the panel fills the Downloads page as before.

## 0.6.2
- The embedded YouTube view follows the app theme (dark/light) via YouTube's own theme setting, also when the theme is switched while the app runs.

## 0.6.1
- Gentle mode (on by default, Settings): pauses between requests, 3-8 s between playlist items, exponential back-off (2, 4, 8 ... 60 s) after errors.
- Rate limit / bot check answers (HTTP 429, "not a bot") pause the whole queue for 90 s and show a clear hint instead of hammering YouTube.
- Optional "Use browser login for downloads" (Firefox / Edge / Chrome cookies) for age-restricted, members-only and Premium videos. Off by default.

## 0.6.0
- Windows: embedded YouTube browser on the Downloads page (top), the app controls below; the divider can be dragged. Opening a video, Short or playlist puts its link into the link field - the download still starts only with "Download". Back/forward/reload/start page and a "Use this link" button.
- Uses the Microsoft Edge WebView2 that ships with Windows 11 (Qt's `qtwebview_webview2` plugin): no browser is bundled, the EXE grows by well under 1 MB. Login data is kept in the Yeal data folder (`webview2`).
- Switch in the page header and under Settings -> Browser. Not available on Android.
- The browser hides while a dialog is open (a native view cannot sit under dialogs).

## 0.5.6
- "Album tracks": with a tracklist in the description, Yeal saves the songs as an album in its own folder `<title> [id]\`: one file per song (`01 - Name.mp3`), tags (album, artist, track n/N, title) and a playlist `<title>.m3u8` in track order. The full file with markers stays next to the folder.

## 0.5.5
- Tracklists: if the description has a tracklist with timestamps, yt-dlp turns it into chapters and Yeal embeds them as markers (MP3, M4A, video) with "Embed metadata".
- New option "Album tracks" (chip + profile switch): see 0.5.6.
- The saved HTML page turns the timestamps of the tracklist into links that jump to that position in the player.

## 0.5.4
- Two separate progress bars per download: "Download" (0-100 %) and the creation step, e.g. "Creating MP3" (0-100 %), each with its own percentage, speed/ETA and step name.
- The creation bar follows the growing output file of the conversion, so it moves smoothly instead of jumping.

## 0.5.3
- Fix: YouTube embed error 153 (no HTTP referer when a page is opened from disk). New "Open page (with online player)" button/menu entry: Yeal serves the saved HTML on 127.0.0.1 and opens it in the browser, where the player works.
- Opened by double-click from disk, the page shows the video thumbnail with a link to the original site instead of a broken player.

## 0.5.2
- Paste button, "Paste from clipboard" and dropped links now only fill the link field. The download starts when you press "Download" (or Enter).

## 0.5.1
- Optional "Online player (HTML)": the saved HTML page also embeds the YouTube/Vimeo player (needs internet), with the local file player below. Chip on the download bar and switch in the profile editor.
- The HTML page uses the app theme (dark/light) that was active when the download was created.

## 0.5.0
- Audio: MP3 is the default and is always created at the maximum 320 kbps.
- Audio: if the source offers very high quality (160 kbps or more, or lossless), a dialog appears before the download starts: AAC (M4A), original stream, FLAC (lossless sources) or MP3.
- Progress: one bar with a real percentage for every step (preparing, download, converting, embedding cover, writing tags), plus the step name.
- The quick switch "Audio (MP3)" now really activates the MP3 profile.

## 0.4.6
- Fix: audio download failed with "Supported filetypes for thumbnail embedding ..." (profile "Audio original" = webm/opus). The cover is now embedded only for MP3/M4A/Opus and video.

## 0.4.5
- Extractor: new minimum interval 0.1 s (Shorts only, like 0.5 s).

## 0.4.4
- Extractor: PNG (lossless) is now the default image format.

## 0.4.3
- Extractor dialog no longer closes by itself: the result (count + folder) is shown inside, with "Open folder" and "Close".
- Slim portable EXE: Yeal.spec packs only the Qt/Python parts the app uses; ffmpeg/node sit in bin\ next to the exe (or inside with `Build_Yeal_Exe.bat embed`).

## 0.4.2
- EXE build is now a single standalone file (dist\Yeal.exe) with ffmpeg and node packed inside.

## 0.4.1
- Extractor: video files can also be dragged in from any folder (Explorer); the output folder stays the app's Frames folder.

## 0.4.0
- New image extractor workflow: in-app dialog with video tiles (no system file browser); drag a tile onto the extractor (or click it), pick the range on the film strip, set the interval, create the images. Opens from the new button in the Downloads header or from a finished download.
- Interval chips 0.5 / 1 / 2 / 5 / 10 / 30 / 60 s plus free input; 0.5 s only for Shorts (up to 3 minutes), otherwise 1 s or more. Image count preview.
- File names get a decimal for sub-second times (e.g. name_00h00m01.5s.jpg).
- Logo watermark in the list area now fills the field.

## 0.3.3
- Logo moved from the sidebar into the download list area as a subtle transparent watermark, scaled to fit.
- The app remembers the last window size, position and maximized state.

## 0.3.2
- Fixed: "Show in folder" opened Documents (Explorer /select argument was quoted wrongly).
- Fixed: split-into-images preview (filmstrip + selection frame) failed on Windows when ffmpeg output was not decodable; failures now show the reason in the dialog.
- Open / folder buttons fall back to the Video/Audio sub-folder of the download folder from Settings.

## 0.3.1 - 2026-10-23
- Downloads are sorted into `Video` and `Audio` sub-folders of the download folder.
- Description and transcript use the video's name (`name.html`, `name.txt`) in the same folder; the HTML embeds the video/audio player (relative link), so keep both files together.
- New: "Split into images" on finished videos (row menu / button): range + one image every N seconds (JPG/PNG), saved in `Frames/<video name>/` inside the download folder, one folder per video. Needs ffmpeg (desktop).
- Split into images: film strip with a red selection frame (drag handles / move range), preview player (play selection), JPG now at best quality.
- New default profile "Video 4K" (also added once to existing settings).
- Yeal logo: start screen, sidebar, window icon, exe icon and the About section in Settings.
- Fix: playlist links (e.g. youtube.com/playlist?list=...) now always download the whole playlist; one unavailable video no longer aborts it.
- Fix: "Open file" / "Show in folder" use the real final file (after merge/conversion) and fall back to the configured download folder.
- New: quick Video / Audio (MP3) switch on the Downloads page.
- New: optional description (HTML, clickable links) and transcript (TXT from subtitles); rows show whether they exist and were saved.

## 0.3.0 - 2026-10-22
- **New Apple-style interface** (light, dark or follow the system): sidebar on wide windows,
  bottom tab bar on narrow ones and on Android. Design tokens live in `qml/Theme.qml`.
- Downloads page: link card with profile picker, filter tabs (All/Active/Queued/Done/Failed),
  thumbnails, uploader/duration/size, speed and time left, drag & drop of links, status footer.
- **Download profiles:** named presets (format, quality, audio format, subtitles, playlists,
  metadata). Create, edit, duplicate, delete; old settings migrate to "My previous settings".
- Settings page: theme, download folder, parallel downloads, speed limit, proxy, yt-dlp update,
  ffmpeg / JavaScript runtime status, custom yt-dlp options (JSON).
- Shortcuts: Ctrl+1/2/3 switch pages, Ctrl+L focuses the link field.
- Style switched from Material to Basic (all controls are custom drawn).

## 0.2.0 - 2026-10-22
- **YouTube fix:** Yeal now keeps its own current yt-dlp + yt-dlp-ejs (downloaded from PyPI into
  `<data>/ytdlp`, sha256-checked, auto-checked every 3 days, button in Settings). The old
  "The page needs to be reloaded" error came from the 2025 yt-dlp in the central Python.
- JavaScript runtime for YouTube: Node is found automatically (`Tools_Central\Dependencies\node`,
  `bin\node.exe`, `YEAL_NODE`, PATH) and passed to yt-dlp. Settings warns when none is found.
- Right-click menus (long-press on touch): download cards, URL field, empty list area.
- Download folder can be chosen with the system folder dialog (desktop); "Default" resets it.
- "Show" now selects the file in Explorer; new "Open file" and "Copy link / error" actions.
- New tests: updater (fake PyPI, zip-slip, checksum, rollback), JS runtime, folder setting.

## 0.1.1 - 2026-10-22
- Project moved to the workspace folder `APK YEAL`; script and ffmpeg lookup paths adapted.

## 0.1.0 - 2026-10-22
- Initial scaffold: yt-dlp engine, parallel download queue, settings, QML UI (desktop + phone layout).
- Platform layer for Windows desktop and Android (no ffmpeg on Android yet).
- Tests: unit tests, QML offscreen smoke test, local end-to-end test with real yt-dlp + ffmpeg.
- Cloud build workflow for the APK (pyside6-android-deploy). NOT yet verified on a real run.
