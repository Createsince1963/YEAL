# 03 Domain model (terms and rules)

Only terms that appear in code, tests or project documents. Vocabulary of the sun view is from CLAUDE.md / CHANGELOG.md.

## Terms
| Term | Meaning | Source |
|---|---|---|
| Job | One download request (URL + options) with a state and progress | `core/models.py` |
| Profile | Named preset of download options (e.g. "Video 1080p", "Audio MP3") | `core/settings.py` |
| Gentle mode | Polite request pattern: pauses between requests, 3-8 s between playlist items, back-off; a rate limit / bot check pauses the whole queue 90 s | README, `core/queue.py` |
| Album mode / split chapters | A long file with a timestamp tracklist is split into tracks with tags and an `.m3u8` | `core/album.py` |
| Extras | Files next to a download: description HTML, transcript TXT, lyrics TXT/LRC, cover, HTML player page | `core/extras.py` |
| TIDAL Web | The embedded TIDAL website (`TidalPane.qml`) | PLAN_TIDALGUI |
| TIDAL DIY | Yeal's own native TIDAL browser + player (`TidalHome.qml`) | PLAN_TIDALGUI |
| tiddl | External command line tool (Apache-2.0) that downloads from TIDAL; the only TIDAL download engine | TIDAL_EVALUATION |
| Sun view | Player drawn as a small solar system: oval track player = sun, planets open cards | CLAUDE.md |
| Planet / card | A round button around the sun (Library, Queue, Played, Settings, Speaker, Sound, Folders ...) / the panel it opens | CHANGELOG 0.9.1.13-0.9.1.19 |
| Moon | A music folder (source) shown at the Folders planet | CHANGELOG 0.9.1.19 |
| Oval / track player | Stadium-shaped player with progress dot and loudness band | PLAN_PLAYER_TRACK |
| Band | Loudness band around the oval: `song` (whole-song profile) / `flow` (running level) / `off` | `tidal_player_vis_mode` |
| Song fan | Lists of next / last played songs above / below the sun (`SunFan.qml`, now vertical cards, no ring) | CHANGELOG 0.9.1.20, .36 |
| Own audio engine | ffmpeg -> float32 DSP chain -> QAudioSink; optional (needs numpy) | `core/dsp.py` |
| Stream to box | Play a finished file on a UPnP/DLNA speaker (KEF LS50 etc.), speaker fetches it from Yeal | `core/streaming.py` |
| Login pack | One password-encrypted file `*.yealpack` carrying TIDAL sign-in, cookie file, vault entries | `core/loginpack.py` |
| Admin vault | Encrypted store for logins (DPAPI + admin password) | `core/vault.py` |
| Interim version | `0.9.1.NN`, one per larger step, local commit + tag, not pushed | OR-002 |

## States
- Job: `queued -> fetching -> downloading -> processing -> done | error | canceled` (`JobState`; `finished` = done/error/canceled;
  `kind` groups for filters: queued / active / done / failed). Progress is playlist aware: `(index - 1 + fraction) / count`.
- Vault: locked / unlocked (auto-lock after 5 min); new vault starts with a default password that must be replaced before entries are available.
- Player: queue with shuffle (stable under manual moves) and repeat off/all/one (`QueueModel`, `TidalPlayer`).

## Business rules found in code and project files
(Owner-decided rules are in [13_OWNER_RULES.md](13_OWNER_RULES.md); the following are *implemented behaviour* and marked accordingly.)
- MP3 is always 320 kbps (`DownloadOptions.normalized`). Rule OR-009 (confirmation requested, Q-05).
- TIDAL qualities: `normal` (AAC 320 `.m4a`, converted to MP3 320 after download), `high` (FLAC 16-bit), `max` (FLAC up to 24-bit). `low` is gone; a saved `low` becomes `normal`. Rule OR-010 (confirmation requested, Q-05).
- TIDAL playback via the tiddl token is at most FLAC 16-bit / 44.1 kHz; the badge shows the real quality (implemented; consequence of TIDAL, not an owner rule).
- Duplicate check: asks "Download again?" or opens the existing file (`history.find_done`).
- Optional parts never fail a download: missing subtitles, cover or quality are skipped with a hint on the tile (README).
- Downloads are sorted into `Video\` and `Audio\`; playlists into `Playlists\<name>\`; frames into `Frames\<video>\` (README).
- HTML pages never overwrite existing link lists; numbered `(2).html` (PLAN_TIDALGUI 3c, `write_tidal_linklist`).
- Only one media plays at a time when `single_playback` is on (settings; web players are paused via JavaScript, others via player control).
- Android hides TIDAL DIY.

## Boundaries
No fachliche rule was invented for this file. Where a rule is only implied by code behaviour it is listed as "implemented behaviour"; confirmation requests are in [12_PROJECT_STATE.md](12_PROJECT_STATE.md) (open owner decisions).
