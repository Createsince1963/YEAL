# Tool: TIDAL (Web, DIY and download)

## Identity
Name: TIDAL integration with three entries: TIDAL Web (embedded website), TIDAL DIY (native browser + player), TIDAL download (tiddl). Users: TIDAL subscribers in the family, each with their own account. Status: built 0.9.0.0 / 0.9.1.01-0.9.1.38; not hand-tested with a signed-in account after the later changes (see 12). Desktop only.

## Problem and benefit
Browse and play TIDAL in Yeal's design, edit own playlists/favorites, and download selections as FLAC or MP3 320 files with tags, covers, lyrics and HTML pages, using the owner's subscription.

## Functions
- Core: sign-in (device login confirmed in the embedded view), browse (Start, Explore, Feed, My collection, search, album/artist/playlist/mix), playback with queue, lyrics, favorites, playlist create/rename/delete/add/remove, download via tiddl, HTML link list without download.
- Secondary: layout docks (left/right/own window/hidden), tile size, sun view mode, drag and drop into queue and workflow.
- Not included: other TIDAL engines (D-004), Hi-Res playback (D-007), Android.

## Domain logic
Qualities and conversion: OR-010. Playback cap: D-007. Options as tiles: quality, videos, video quality, Atmos, singles, extras (lyrics, lrc, cover embed/file, m3u, html, no-skip, rewrite).
Errors: each area (feed, pages, lyrics) fails alone and shows a hint. Subscription notice `tidal.NOTICE` always visible when not signed in.

## Inputs / outputs
In: TIDAL links, tiddl `auth.json`, settings. Out: files under the `Tidal` folder, `.m3u`, HTML pages, link lists in `Tidal\Linklisten\`, `tidal_layout` setting. Formats in [04_DATA_MODEL.md](../04_DATA_MODEL.md).

## Architecture
`TidalHome.qml` -> context `tidal` (`TidalBackend`) -> `core/tidal_api.TidalApi` (stdlib); downloads -> `Backend.addUrls` -> `Engine._run_tidal` -> `core/tidal.run_download` (tiddl). See [../modules/tidal.md](../modules/tidal.md) and [../ARCHITECTURE.md](../ARCHITECTURE.md).

## Operation
[06_WORKFLOWS.md](../06_WORKFLOWS.md) W-03, W-04. Special cases: token expired -> one `tiddl auth refresh`; tiddl missing -> "Tidal helper missing"; hi-res stream -> badge shows 16-bit reason.

## Tests
`test_tidal` (40), `test_tidal_api` (20), `test_tidal_player` (40), `test_tidal_gui_qml` (19). Limits: no real account, no real playback.

## History and next steps
Plan: [../PLAN_TIDALGUI_0.9.1.md](../PLAN_TIDALGUI_0.9.1.md); history: [../HANDOFF_TIDALGUI.md](../HANDOFF_TIDALGUI.md). Open: KI-003, KI-004, KI-015; hand test with signed-in account.
