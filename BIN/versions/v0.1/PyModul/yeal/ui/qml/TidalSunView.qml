import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The TIDAL DIY player as a solar system (SunView): the oval player is the sun, the planets are your playlists (left), the
// queue (right), the songs played and the settings (below), the search and the lyrics (above). Titles, albums and
// playlists dropped on the sun play at once. The house button leads back to the normal TIDAL pages.
SunView {
    id: view
    ns: "diy"
    player: tidal.playerObject
    dropPlay: true
    canExit: true
    planets: [
        { key: "playlists", icon: "library", label: qsTr("Playlists"), deg: 180, zone: "left" },
        { key: "queue", icon: "queueList", label: qsTr("Queue"), deg: 0, zone: "right", slot: 0 },
        { key: "played", icon: "clock", label: qsTr("Played"), deg: 135, zone: "bottom", slot: 0 },
        { key: "settings", icon: "sliders", label: qsTr("Settings"), deg: 45, zone: "bottom", slot: 1 },
        { key: "search", icon: "search", label: qsTr("Search"), deg: 225, zone: "top", slot: 0 },
        { key: "lyrics", icon: "lyrics", label: qsTr("Lyrics"), deg: 315, zone: "top", slot: 1 },
        { key: "bluetooth", icon: "bluetooth", label: qsTr("Bluetooth"), title: qsTr("Audio output"), deg: 90, zone: "right", slot: 1 }]
    cards: ({ playlists: playlistsCard, queue: queueCard, played: playedCard, settings: settingsCard,
              search: searchCard, lyrics: lyricsCard, bluetooth: outputCard })

    Component { id: playlistsCard
        TidalTrackPanel { ctl: view.ctl; tab: "playlists"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: queueCard
        TidalTrackPanel { ctl: view.ctl; tab: "queue"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: playedCard
        TidalTrackPanel { ctl: view.ctl; tab: "played"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: settingsCard
        SunSettings { player: view.player; local: false } }
    Component { id: searchCard
        TidalTrackPanel { ctl: view.ctl; tab: "results"; showTabs: false; color: "transparent"; border.width: 0 } }
    Component { id: lyricsCard
        TidalTrackPanel { ctl: view.ctl; tab: "lyrics"; showTabs: false; showSearch: false; color: "transparent"; border.width: 0 } }
    Component { id: outputCard
        SunSpeaker { mode: "pc"; group: "pc"; player: view.player; tint: view.tint } }
}
