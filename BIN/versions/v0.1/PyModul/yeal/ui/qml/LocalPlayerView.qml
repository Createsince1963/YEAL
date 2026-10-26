import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Yeal's own player for the DOWNLOADED songs (the fourth button next to YouTube / TIDAL Web / TIDAL DIY, or "Play in Yeal
// player" in the menu of a download), as a solar system (SunView): the oval player is the sun, the planets are the library
// (left), the queue (right), the songs played (below), settings and the speaker (above, Stream to box).
SunView {
    id: view
    ns: "local"
    player: backend.localPlayerObject
    local: true
    planets: [
        { key: "library", icon: "library", label: qsTr("Library"), deg: 180, zone: "left" },
        { key: "queue", icon: "queueList", label: qsTr("Queue"), deg: 0, zone: "right", slot: 0 },
        { key: "sound", icon: "equalizer", label: qsTr("Sound"), title: qsTr("Sound"), deg: 30, zone: "right", slot: 1, edit: true },
        { key: "folders", icon: "folder", label: qsTr("Folders"), title: qsTr("Music folders"), deg: 150, zone: "left", slot: 1, edit: true },
        { key: "played", icon: "clock", label: qsTr("Played"), deg: 90, zone: "bottom", slot: 0 },
        { key: "settings", icon: "sliders", label: qsTr("Settings"), deg: 225, zone: "top", slot: 0, edit: true },
        { key: "stream", icon: "cast", label: qsTr("Speaker"), title: qsTr("Speaker / TV"), deg: 315, zone: "top", slot: 1, edit: true }]
    cards: ({ library: libraryCard, queue: queueCard, played: playedCard, settings: settingsCard, stream: speakerCard,
              sound: soundCard, folders: foldersCard })

    Component { id: libraryCard
        TidalTrackPanel { local: true; player: view.player; tab: "library"; showTabs: false; color: "transparent"; border.width: 0 } }
    Component { id: queueCard
        TidalTrackPanel { local: true; player: view.player; tab: "queue"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: playedCard
        TidalTrackPanel { local: true; player: view.player; tab: "played"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: foldersCard
        SunSources { player: view.player; tint: view.tint } }
    Component { id: settingsCard
        SunSettings { player: view.player } }
    Component { id: soundCard
        SunSound { tint: view.tint } }
    Component { id: speakerCard
        SunSpeaker { player: view.player; tint: view.tint } }
}
