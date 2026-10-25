import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Yeal's own player for the DOWNLOADED songs (the fourth button next to YouTube / TIDAL Web / TIDAL DIY, or "Play in Yeal
// player" in the menu of a download). The oval track player on top, the library of the finished audio downloads
// below. STREAM plays the current song on the speaker / TV chosen under "Stream to box".
Item {
    id: view
    readonly property var player: backend.localPlayerObject

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.separator
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s2
        TidalTrackPlayer {
            id: oval
            Layout.fillWidth: true
            Layout.fillHeight: true
            player: view.player
            local: true
            panelOpen: true
            panelTab: "library"
            panelHeight: Math.max(220, view.height - 260)
        }
    }
}
