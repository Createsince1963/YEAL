import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

// Content of the "Settings" planet: colour of the player, the band around the oval, shuffle, repeat and volume.
Flickable {
    id: root
    property var player
    property bool local: true                          // false: TIDAL songs, which can be liked
    property int favTick: 0
    readonly property bool fav: favTick >= 0 && !local && !!player.current && !!player.current.id
                                && tidal.isFavorite("track", player.current.id)
    Connections { target: tidal; function onFavoritesChanged() { root.favTick++ } }
    readonly property var custom: backend.settings.custom_colors || []
    function addCustom(hex) {
        var h = String(hex).toLowerCase()
        if (custom.indexOf(h) >= 0) { backend.setSetting("tidal_player_color", h); return }
        if (custom.length >= 5) return
        backend.setSetting("custom_colors", custom.concat([h]))
        backend.setSetting("tidal_player_color", h)
    }
    function removeCustom(hex) {
        backend.setSetting("custom_colors", custom.filter(function (c) { return c !== hex }))
        if (String(backend.settings.tidal_player_color) === hex) backend.setSetting("tidal_player_color", "green")
    }
    ColorDialog {
        id: colorDialog
        title: qsTr("Your own colour")
        onAccepted: root.addCustom(selectedColor.toString().slice(0, 7))
    }
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
        Text { text: qsTr("Your colours (at most 5): + makes a new one, a right click removes one"); color: Theme.textTertiary
               font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Repeater {
                model: root.custom
                delegate: Rectangle {
                    required property string modelData
                    readonly property bool picked: String(backend.settings.tidal_player_color) === modelData
                    width: 26; height: 26; radius: 13
                    color: modelData
                    border.width: picked ? 3 : 0
                    border.color: Theme.text
                    Accessible.role: Accessible.Button; Accessible.name: modelData
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: backend.setSetting("tidal_player_color", modelData) }
                    TapHandler { acceptedButtons: Qt.RightButton; onTapped: root.removeCustom(modelData) }
                    TapHandler { onLongPressed: root.removeCustom(modelData) }
                }
            }
            Rectangle {
                visible: root.custom.length < 5
                width: 26; height: 26; radius: 13
                color: "transparent"
                border.width: 1; border.color: Theme.textSecondary
                Accessible.role: Accessible.Button; Accessible.name: qsTr("Add a colour")
                Text { anchors.centerIn: parent; text: "+"; color: Theme.textSecondary; font.pixelSize: 16 }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: { colorDialog.selectedColor = Theme.playerColor(backend.settings.tidal_player_color); colorDialog.open() } }
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
        Text { text: qsTr("Band strength"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            Slider {
                Layout.fillWidth: true
                from: 50; to: 300; stepSize: 10
                value: backend.settings.level_amp || 100
                onMoved: backend.setSetting("level_amp", Math.round(value))
                Accessible.name: qsTr("Band strength")
            }
            Text { text: (backend.settings.level_amp || 100) + "%"; color: Theme.textSecondary; font.pixelSize: Theme.caption
                   Layout.preferredWidth: 40; horizontalAlignment: Text.AlignRight }
        }
        Text { text: qsTr("Glow around the inner lane (swells with the loud parts)"); color: Theme.textSecondary
               font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            Slider {
                Layout.fillWidth: true
                from: 0; to: 300; stepSize: 10
                value: backend.settings.glow_amp === undefined ? 100 : backend.settings.glow_amp
                onMoved: backend.setSetting("glow_amp", Math.round(value))
                Accessible.name: qsTr("Glow")
            }
            Text { text: (backend.settings.glow_amp === undefined ? 100 : backend.settings.glow_amp) + "%"; color: Theme.textSecondary
                   font.pixelSize: Theme.caption; Layout.preferredWidth: 40; horizontalAlignment: Text.AlignRight }
        }
        Text { text: qsTr("Outer ring"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Chip { text: qsTr("Playlist / folder / queue"); checked: (backend.settings.outer_ring || "list") === "list"
                   onToggled: backend.setSetting("outer_ring", "list") }
            Chip { text: qsTr("Off"); checked: backend.settings.outer_ring === "off"
                   onToggled: backend.setSetting("outer_ring", "off") }
        }
        Text { text: qsTr("Seamless change to the next song"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Repeater {
                model: [{ v: 0, t: qsTr("Off") }, { v: 5, t: qsTr("5 s") }, { v: 8, t: qsTr("8 s") }, { v: 10, t: qsTr("10 s") }]
                delegate: Chip {
                    required property var modelData
                    text: modelData.t
                    checked: (backend.settings.crossfade || 0) === modelData.v
                    onToggled: backend.setSetting("crossfade", modelData.v)
                }
            }
        }
        Text { text: qsTr("Playing"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Chip { text: qsTr("Shuffle"); checked: root.player.shuffle; onToggled: root.player.toggleShuffle() }
            Chip { visible: !root.local && !!root.player.current && !!root.player.current.id
                   text: root.fav ? qsTr("Liked") : qsTr("Like this song"); checked: root.fav
                   onToggled: tidal.toggleFavorite("track", root.player.current.id) }
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

        // ---- the sound check: finds the smallest sound buffer without dropouts and checks for slowing down (runs as its own process)
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.separator }
        Text { text: qsTr("Sound check"); color: Theme.textSecondary; font.pixelSize: Theme.caption; font.weight: Font.Bold }
        Text {
            Layout.fillWidth: true
            text: qsTr("Tests the real playback chain on the chosen output while the window is busy, finds the smallest sound buffer without dropouts and, in the long test, checks that nothing grows with every song. The music is paused meanwhile; the test is silent.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s1
            AppButton { text: qsTr("Quick check (1 min)"); iconName: "gauge"; enabled: !backend.calibration.running
                        onClicked: backend.calibration.start("quick") }
            AppButton { text: qsTr("Long check (4 min)"); iconName: "gauge"; enabled: !backend.calibration.running
                        onClicked: backend.calibration.start("stress") }
            AppButton { visible: backend.calibration.running; text: qsTr("Cancel"); iconName: "x"; onClicked: backend.calibration.cancel() }
        }
        Text {
            Layout.fillWidth: true
            visible: backend.calibration.status !== ""
            text: backend.calibration.status
            color: backend.calibration.running ? Theme.accent : Theme.text
            font.pixelSize: Theme.footnote; wrapMode: Text.Wrap
        }
        Repeater {
            model: backend.calibration.verdicts
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.s2
                Rectangle {
                    implicitWidth: 44; implicitHeight: 20; radius: 10
                    Layout.alignment: Qt.AlignTop
                    color: modelData.level === "PASS" ? Theme.successSoft : modelData.level === "WARN" ? Theme.warningSoft : Theme.dangerSoft
                    Text { anchors.centerIn: parent; text: modelData.level; font.pixelSize: 10; font.weight: Font.Bold
                           color: modelData.level === "PASS" ? Theme.success : modelData.level === "WARN" ? Theme.warning : Theme.danger }
                }
                Text { Layout.fillWidth: true; text: modelData.text; color: Theme.textSecondary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap }
            }
        }
        Text {
            Layout.fillWidth: true
            visible: backend.calibration.hasResult
            text: qsTr("Recommended: sound buffer %1 ms, picture %2 times a second. Now: %3 ms, %4 Hz.")
                  .arg(backend.calibration.profile.audio_buffer_ms).arg(backend.calibration.profile.ui_refresh_hz)
                  .arg(backend.settings.audio_buffer_ms).arg(backend.settings.ui_refresh_hz)
            color: Theme.text; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }
        Flow {
            Layout.fillWidth: true
            visible: backend.calibration.hasResult
            spacing: Theme.s1
            AppButton { text: qsTr("Use the recommended values"); kind: "primary"; iconName: "check"; onClicked: backend.calibration.apply() }
        }
    }
}
