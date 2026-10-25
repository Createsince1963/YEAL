import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// "My collection" of the TIDAL DIY view: playlists, albums, artists, tracks, mixes, videos.
Item {
    id: col
    property var ctl
    property string part: "playlists"
    readonly property var parts: [
        { text: qsTr("Playlists"), value: "playlists" }, { text: qsTr("Albums"), value: "albums" },
        { text: qsTr("Artists"), value: "artists" }, { text: qsTr("Tracks"), value: "tracks" },
        { text: qsTr("Mixes"), value: "mixes" }, { text: qsTr("Videos"), value: "videos" }]

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s3
        RowLayout {
            Layout.fillWidth: true
            Text { text: qsTr("My collection"); font.pixelSize: Theme.title; font.weight: Font.DemiBold; color: Theme.text }
            Item { Layout.fillWidth: true }
            Segmented {
                options: col.parts
                current: col.part
                implicitWidth: 520
                onActivated: (v) => col.part = v
            }
        }
        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: gridComp
            // a new grid per part, so each part loads its own list
            property string part: col.part
            onPartChanged: { sourceComponent = null; sourceComponent = gridComp }
        }
    }
    Component {
        id: gridComp
        TidalGrid {
            ctl: col.ctl
            route: col.part === "mixes" ? "mixes" : "favorites"
            arg: col.part === "mixes" ? "" : col.part
        }
    }
}
