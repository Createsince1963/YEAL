# Yeal architecture

```
 QML (Main -> Downloads / Profiles / Settings pages; Theme singleton + base controls)
        |  context properties: backend, jobModel
 ui/backend.py  Backend(QObject) + JobModel + JobFilterModel (filter/search)
        |  worker threads -> Qt queued signals (_jobChanged / _jobRemoved)
 core/queue.py  DownloadQueue  (4 daemon workers, `max_parallel` gate, cancel/retry/remove)
        |  runner(job, cancel_event, notify)
 core/engine.py Engine.run     (yt-dlp YoutubeDL, progress + postprocessor hooks)
        |  updater.activate(data_dir) before the first `import yt_dlp`
 core/updater.py               (PyPI wheels -> <data>/ytdlp, sha256 + zip-slip checks, atomic swap)
        |  build_ydl_opts(options, PlatformInfo)
 core/presets.py               (format selectors, postprocessors, custom-option sanitizing)
        |
 platforms/     PlatformInfo   (paths, ffmpeg, is_mobile)  desktop.py | android.py
```

Rules that keep both targets working:

1. `core/` imports no Qt and no platform code; it only receives a `PlatformInfo`.
2. Anything that differs per OS lives in `platforms/`. Capability, not OS name, drives behaviour:
   `PlatformInfo.can_merge` (ffmpeg present) switches format selectors and postprocessors.
3. Worker threads never touch QML objects. They hand job *snapshots* to Qt signals.
4. Python 3.11 compatible (the Android wheels are cp311) although desktop runs 3.13.
5. Only `QtCore`, `QtGui`, `QtQml`, `QtQuick`, `QtQuickControls2` - no `QtWidgets`.

`yt_dlp` is imported lazily, only after `updater.activate()`; never import it at module level.
`PlatformInfo.js_runtime` (Node) is passed as `js_runtimes` - YouTube cannot be extracted without one.

Job states: queued -> fetching -> downloading -> processing -> done | error | canceled.
Progress is playlist aware: `(index - 1 + fraction) / count`.

Custom yt-dlp options are filtered by `FORBIDDEN_KEYS` (exec hooks, postprocessor chain,
external downloaders, output paths, browser cookies) before they are merged.

## UI design system (`yeal/ui/qml`)

- `Theme.qml` (singleton): semantic color tokens for light/dark, type scale, spacing, radii.
  `Main.qml` binds `Theme.dark` to `settings.theme` / system color scheme and `Theme.compact`
  to `window.width < 720` (bottom tab bar instead of sidebar, single action per row).
- Base controls (`AppButton`, `IconButton`, `Segmented`, `AppSwitch`, `Stepper`, `AppField`,
  `AppMenu`, `SettingsGroup/Row`, `Badge`, `Toast`) use the Basic style and the tokens only.
- Icons are 24x24 stroke paths (`IconPaths.qml`) drawn with `Shape`, so they follow theme colors.
- Profiles are stored in `settings.json`; `Settings.to_options()` turns the active profile plus
  global limits (rate, proxy, custom options) into `DownloadOptions` per job.
- Property naming: no `on` + capital names (QML signal syntax); roles use `jobState`, not `state`.

## TIDAL DIY (0.9.1)

```
 QML  TidalHome (SplitView of TidalDock areas + page Loader + TidalPlayerBar; pages Tidal*.qml)
        |  context property: tidal            (QML never talks to the API directly)
 ui/tidal_backend.py  TidalBackend(QObject)   load(route, arg) -> pageLoaded / pageFailed, library, favorites,
        |                                     playlist edits, download(urls), link lists
        |             TidalPlayer + QueueModel  QMediaPlayer + QAudioOutput, queue, shuffle, repeat, lyrics, badge
        |  worker threads (ThreadPoolExecutor) -> queued signals
 core/tidal_api.py    TidalApi   (standard library only, no Qt; tiddl sign-in, token refresh, 5 min cache, 2 parallel)
 core/tidal.py        tiddl helper (download command, own tiddl folder, login) - downloads only
```

- Rule 5 has one deliberate exception: `ui/tidal_backend.py` also uses `QtMultimedia` (own player). The module is
  imported lazily by the player (`_ensure`), so a build without it still starts and shows an error toast on play.
- Downloads of TIDAL DIY go through the normal job path (`Backend.addUrls` -> tiddl); dropping a TIDAL link on the
  workflow panel (`WorkflowPanel.qml`, `DropArea`) does the same.
- Layout: setting `tidal_layout` (validated in `core/settings.py`: dock side, widths, own-window rectangle, player
  top/bottom). `TidalHome.arrange()` re-parents the areas in the SplitView; `Backend.setSetting` converts
  `QJSValue` objects sent from QML.
- Android hides TIDAL DIY; it is desktop only.
- Tests: `test_tidal_api.py` (fake TIDAL server), `test_tidal_player.py` (queue, player logic, link list),
  `test_tidal_gui_qml.py` (all components load without QML warnings, layout is saved and reset).
