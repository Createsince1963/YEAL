# Changelog

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
