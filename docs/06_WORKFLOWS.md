# 06 Workflows

## W-01 First start
`FirstRunDialog.qml` asks for the cookie browser (Chrome default) and the download folder; new data folder -> `setup_complete = False` until done.
Yeal always starts in the default GUI (workflow sidebar + embedded YouTube view), regardless of saved state (OR-011).

## W-02 Download from the YouTube view
1. User opens a video/Short/playlist in the embedded browser -> the link field is filled with a cleaned link (video id only); nothing downloads yet.
2. User picks a profile / audio-video, presses Download.
3. Duplicate check (history) -> maybe "Download again?" / open existing.
4. For audio sources of better quality: audio choice dialog (F-02). For playlist links: playlist dialog (F-03). For tracklists: album dialog (F-04). For live streams: live dialog (F-05).
5. Job runs; tile shows progress, phase, speed, ETA; finished tile offers show-in-folder, play in VLC / in Yeal player, stream to box, MP3 tag editor prompt (default No).
Special cases: errors are explained in plain language; gentle mode pauses; cookies unreadable -> note on the tile.

## W-03 Download from TIDAL
Link from TIDAL Web / TIDAL DIY (a click on TIDAL content writes the canonical link into the workflow) or dropped on the workflow panel (`DropArea`) -> tiddl job. TIDAL options are
pulldown tiles (quality, videos, video quality, Atmos, singles, extras). Quality Normal ends as MP3 320 (conversion step shown). Sign-in: embedded browser view confirms tiddl's device login.

## W-04 Listen in TIDAL DIY
Sign in -> `TidalHome`: playlists column | tabs Start / Explore / Feed / My collection + page | queue; player bar or oval/sun view. Double click plays; drag tiles into queue; edit playlists/favorites;
save a playlist as HTML link list; download a selection. Docks can be moved, detached to own windows, hidden; layout saved in `tidal_layout`, "Reset layout" in Settings > Tidal.

## W-05 Player for downloaded files (MediaOrbit sun view)
Sidebar "Player" -> `LocalPlayerView`: library of finished audio downloads or a chosen music folder ("Folders" planet), queue card with Clear all / Save list, played list, song fans above/below, Speaker card
(audio output choice, stream to box), Sound card (EQ, crossfeed, crossfade ...), Settings card with the sound check. Cards open on the side of their planet; edit mode zooms a card.

## W-06 Sound check
Settings planet -> Quick check (1 min) or Long check (4 min): its own process (`calibration_runner`), progress line, PASS/WARN/FAIL list, recommended buffer and repaint rate, "Use the recommended values" writes
`audio_buffer_ms` and `ui_refresh_hz`. Music pauses while it runs; Cancel stops it.

## W-07 Take the logins to another PC
Admin area unlocked with a private password -> "Take the logins with you" (pack password >= 10 chars) -> `*.yealpack`. On the other PC "Open pack..." with the same password: TIDAL sign-in (only if newer),
cookie file, missing vault entries. Browser-view sign-in must be repeated (DPAPI-bound).

## W-08 Update yt-dlp
Automatic check every 3 days (`auto_update`) or Settings button; new wheels into `<data>/ytdlp`, atomic swap, effective on next import.

## W-09 Frame extraction
Drag a video into the frame dialog (or choose a tile), pick interval and format, selection frame on the film strip; output `Frames\<video>\`.

## W-10 Release / version handling (developer workflow, owner rule)
Snapshot -> bump `VERSION`, `yeal/__init__.py`, `pyproject.toml`, `CHANGELOG.md` together -> tests -> local commit + tag `vX.Y.Z.NN` -> no push, no EXE unless the owner names it (OR-002, OR-003).
The central AI protocol's phases A-F apply on top ([13_OWNER_RULES.md](13_OWNER_RULES.md)).
