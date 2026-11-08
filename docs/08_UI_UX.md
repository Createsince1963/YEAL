# 08 UI / UX

Rules marked (OR-xxx) are in [13_OWNER_RULES.md](13_OWNER_RULES.md). Everything else is implemented behaviour from code/CHANGELOG.

## Structure
- `Main.qml`: window, `win.player` = youtube | tidal (Web) | tidaldiy | player (sidebar buttons with logos). Sidebar (wide) or bottom bar (`Theme.compact` below 720 px width).
  Pages: Downloads (workflow panel + browser view / TIDAL DIY / player view), Profiles, Settings; Ctrl+1/2/3 switch, Ctrl+L focuses the link field.
- Design system: `Theme.qml` singleton (light/dark tokens, type scale, spacing, radii); base controls `AppButton, IconButton, Segmented, AppSwitch, Stepper, AppField (secret: Show/Hide),
  AppMenu (width follows the widest item), SettingsGroup/Row/Item, Badge, Toast, Chip` use the Basic style and tokens only. Icons are 24x24 stroke paths (`IconPaths.qml`, `Icon.qml`).
- Brand: `BrandLogo.qml` (MediaOrbit vector logo, top left of the Player view); logos on the four player buttons; Yeal tile for window/taskbar/exe (`docs\brand\`).

## Sun view (players)
- `SunView.qml` (generic: zones left/right/top/bottom, slots, planets with own orbits by dragging, orbit slider and wheel) with `LocalPlayerView.qml` and `TidalSunView.qml` as thin wrappers.
- Planets: Library, Queue, Played, Folders (`SunSources`), Speaker (`SunSpeaker`), Sound (`SunSound`), Settings (`SunSettings`). Cards open on the side of their planet (`SunView.zoneOf`);
  `edit: true` cards zoom for editing. Song lists above/below the oval are vertical cards in front (`SunFan.qml`).
- Oval: `TidalTrackPlayer.qml` + `TidalTrackPanel.qml` (queue / playlists / search / lyrics), colours (named or own `#rrggbb`, max 5 own), glow, level band, outer list ring, volume slider, 10 s jump buttons.

## Binding GUI rules
- No cut-off buttons or chips: rows are `Flow`, not `Row`; `AppButton` clamps to its parent only inside Flow/Grid; `Chip` caps natural width at 200 px (OR-005).
- Every feature, setting, status and result must be visible and operable on screen (APK rule OR-012; applies to Android work).
- Settings: grouped by function, every group collapsed by default, expandable, icon per group; changes staged then saved or discarded; licences listed under Info.
- Right-click context menus; download folder via system dialog; drive/folder question with Continue / Change and "don't ask again".
- Direct Download button in the header, look/position adjustable (`dl_button_style`, `dl_button_pos`).
- Test the layout at 2560 x 1440, 100 % scaling and at small widths ([13_OWNER_RULES.md](13_OWNER_RULES.md) "Machines").
- QML naming: no `on` + capital property names; use `jobState` role.

## Embedded browser views
Back/Forward (Alt+Left/Right), Reload (F5), start page, "Open in your browser"; follows the app theme; mutes during ads and presses visible skip buttons (DE/EN). The web view is collapsed to 2x2 px
under dialogs instead of destroyed so the video keeps playing (0.8.12). Own page history. Only one media plays at a time (`single_playback`).

## Accessibility / localisation
UI strings are English with `qsTr`; German manual `help\manual-de.html`. No accessibility audit exists (not found in project files).
