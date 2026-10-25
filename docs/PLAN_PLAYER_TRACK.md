# Idea: "track" player for TIDAL DIY (concept study, not built yet)

Source of the idea: a concept video from the r/TIdaL community (kept locally as `docs/optional/m2-res_480p.mp4`, not part of
the repository, not ours to redistribute). This page only records what was seen, in our own words, and how it could map
to Yeal. Status: proposal, waiting for the user's decision.

## What the concept shows (42 s, frames checked at 2 s steps)
1. **Stadium shape instead of a bar.** The player is one rounded "running track". The title and artist sit on the left
   inside, previous / play-pause / next on the right inside. Several thin outer rings give depth.
2. **The progress bar is the track.** A small white dot (the "runner") moves along the lower edge; the part already played
   is drawn in the accent colour. Track = song, lap = progress.
3. **VIS (visualisation).** A green band follows the inner outline; its thickness changes with the loudness of the music,
   so the band is thicker in loud parts and thin in quiet ones. Switchable (text button "VIS").
4. **VOL.** Hovering / dragging the volume text turns the band yellow and shows the value large in the middle ("72 %").
   The band width mirrors the volume.
5. **EQ.** A row of 8 vertical sliders (60 Hz ... 16 kHz) with RESET replaces the title area.
6. **PLAYLIST.** Opens a panel below the track with a search field and three tabs: Queue, Playlists, Search results;
   rows have cover, title, artist and length.
7. **Text controls under the track:** REPEAT SINGLE, SHUFFLE on the left; PLAYLIST, VIS, EQ, VOL on the right; the active
   ones are white, the rest grey. No icons, very small type.

## Mapping to Yeal (proposal)
| Concept | Yeal today | Proposal |
|---|---|---|
| Track-shaped player | `TidalPlayerBar.qml` (flat bar) | New `TidalTrackPlayer.qml` as an alternative look, switch in the bar menu / settings (`tidal_player_style`: bar / track) |
| Dot + played part | Slider | custom `Shape` path (rounded rectangle), progress = path length fraction; click / drag on the path seeks |
| Loudness band (VIS) | none | Needs audio levels. `QAudioBufferOutput` (Qt 6.8+) gives the samples of the playing stream; a level per ~30 ms is enough. Fallback: smooth fake level only while playing (clearly an effect, not data) |
| VOL display | slider + mute | text button; hover shows the large number and colours the band |
| EQ | none | QMediaPlayer has no equaliser. Would need own audio processing (decode, filter, output). Large; leave out of the first version |
| Playlist panel | `TidalQueue.qml` (own area) | Reuse the existing queue as the drop-down of the track player |
| Repeat / shuffle | icon buttons | text buttons (same functions) |

## Open points for the decision
- Alternative look (switchable, default stays the bar) or replacement? Proposal: switchable.
- VIS with real levels (`QAudioBufferOutput`, check availability in the bundled PySide6) or without?
- EQ: skip in the first version?
- Size: the track needs about 420 x 150 px; where does it sit (own dock area, or replaces the player bar)?
