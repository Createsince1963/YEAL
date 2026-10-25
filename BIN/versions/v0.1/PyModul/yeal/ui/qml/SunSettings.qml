import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Content of the "Settings" planet: colour of the player, the band around the oval, shuffle, repeat and volume.
Flickable {
    id: root
    property var player
    contentHeight: col.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    ColumnLayout {
        id: col
        width: root.width - Theme.s2
        spacing: Theme.s2
        Text { text: qsTr("Colour"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Repeater {
                model: Theme.playerColors
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool picked: String(backend.settings.tidal_player_color) === modelData.name
                    width: 26; height: 26; radius: 13
                    color: modelData.value
                    border.width: picked ? 3 : 0
                    border.color: Theme.text
                    Accessible.role: Accessible.Button; Accessible.name: modelData.name
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: backend.setSetting("tidal_player_color", modelData.name) }
                }
            }
        }
        Text { text: qsTr("Band around the oval"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Chip { text: qsTr("Song"); checked: backend.settings.tidal_player_vis_mode === "song"
                   onToggled: backend.setSetting("tidal_player_vis_mode", "song") }
            Chip { text: qsTr("Running level"); checked: backend.settings.tidal_player_vis_mode === "flow"
                   onToggled: backend.setSetting("tidal_player_vis_mode", "flow") }
            Chip { text: qsTr("Off"); checked: backend.settings.tidal_player_vis_mode === "off"
                   onToggled: backend.setSetting("tidal_player_vis_mode", "off") }
        }
        Text { text: qsTr("Playing"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Chip { text: qsTr("Shuffle"); checked: root.player.shuffle; onToggled: root.player.toggleShuffle() }
            Chip { text: root.player.repeat === "one" ? qsTr("Repeat: single") : root.player.repeat === "all" ? qsTr("Repeat: all") : qsTr("Repeat: off")
                   checked: root.player.repeat !== "off"; onToggled: root.player.cycleRepeat() }
        }
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "volume"; size: 16; color: Theme.textSecondary }
            Slider {
                Layout.fillWidth: true
                from: 0; to: 100; stepSize: 1
                value: root.player.volume
                onMoved: root.player.setVolume(Math.round(value))
                Accessible.name: qsTr("Volume")
            }
            Text { text: root.player.volume + "%"; color: Theme.textSecondary; font.pixelSize: Theme.caption }
        }
    }
}
