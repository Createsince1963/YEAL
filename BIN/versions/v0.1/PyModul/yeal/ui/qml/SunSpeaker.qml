import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Content of the "Speaker" planet (player for downloaded files): the speakers / TVs of the network (Stream to box) and
// playing the current song there.
ColumnLayout {
    id: root
    property var player
    property color tint: Theme.accent
    spacing: Theme.s2
    Component.onCompleted: backend.scanStreamDevices()

    Text {
        Layout.fillWidth: true
        text: root.player.current && root.player.current.title ? qsTr("Song: %1").arg(root.player.current.title) : qsTr("Pick a song in the library first.")
        color: Theme.text; font.pixelSize: Theme.footnote; elide: Text.ElideRight
    }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.s2
        AppButton {
            text: qsTr("Play on speaker"); kind: "primary"; iconName: "cast"
            enabled: backend.streamAvailable && !!(root.player.current && root.player.current.file) && !backend.streamBusy
            onClicked: backend.streamFile(root.player.current.file, root.player.current.title)
        }
        IconButton { iconName: "pause"; tip: qsTr("Pause on the speaker"); enabled: backend.streamPlaying; onClicked: backend.pauseStream() }
        IconButton { iconName: "play"; tip: qsTr("Continue on the speaker"); onClicked: backend.resumeStream() }
        IconButton { iconName: "x"; tip: qsTr("Stop the speaker"); onClicked: backend.stopStream() }
        IconButton { iconName: "retry"; tip: qsTr("Search for speakers again"); onClicked: backend.scanStreamDevices() }
    }
    Text {
        Layout.fillWidth: true
        text: backend.streamStatus
        visible: text !== ""
        color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight
    }
    ListView {
        id: devices
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 2
        model: backend.streamDevices
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        delegate: Rectangle {
            required property var modelData
            width: devices.width - 6
            height: 36
            radius: 8
            color: modelData.selected ? Qt.alpha(root.tint, 0.18) : devHover.hovered ? Theme.hover : "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s2; anchors.rightMargin: Theme.s2
                spacing: Theme.s2
                Rectangle { width: 8; height: 8; radius: 4; color: modelData.online ? Theme.success : Theme.textTertiary }
                Text { text: modelData.name || modelData.host || ""; Layout.fillWidth: true; elide: Text.ElideRight
                       color: Theme.text; font.pixelSize: Theme.footnote; font.weight: modelData.selected ? Font.Bold : Font.Normal }
                Icon { visible: modelData.selected; name: "check"; size: 14; color: root.tint }
            }
            HoverHandler { id: devHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.selectStreamDevice(modelData.id) }
        }
        Text {
            anchors.centerIn: parent
            visible: devices.count === 0
            text: backend.streamScanning ? qsTr("Searching ...") : qsTr("No speaker found yet.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption
        }
    }
}
