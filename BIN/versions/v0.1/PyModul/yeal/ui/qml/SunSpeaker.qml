import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Content of the "Speaker" planet (player for downloaded files): a small moon system. The speaker planet is in the middle,
// the speakers and TVs found in the network circle around it as moons; a click on a moon chooses it (Stream to box). Left of
// it: the current song, play on the speaker, pause / continue / stop and searching again.
RowLayout {
    id: root
    property var player
    property color tint: Theme.accent
    spacing: Theme.s3
    Component.onCompleted: backend.scanStreamDevices()

    readonly property var devices: backend.streamDevices
    // moons per ring: up to 6 on the inner ring, the rest on rings further out
    readonly property int ringCount: Math.max(1, Math.ceil(devices.length / 6))
    function moonPlace(index) {                        // [ring, position on the ring, moons on that ring]
        var left = devices.length, start = 0
        for (var k = 0; k < ringCount; ++k) {
            var n = Math.ceil(left / (ringCount - k))
            if (index < start + n) return [k, index - start, n]
            start += n
            left -= n
        }
        return [0, 0, 1]
    }

    // ---- the song and the controls
    ColumnLayout {
        Layout.preferredWidth: 190
        Layout.maximumWidth: 230
        Layout.fillHeight: true
        spacing: Theme.s2
        Text {
            Layout.fillWidth: true
            text: root.player.current && root.player.current.title ? root.player.current.title : qsTr("Pick a song in the library first.")
            color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
        }
        AppButton {
            Layout.fillWidth: true
            text: qsTr("Play on speaker"); kind: "primary"; iconName: "cast"
            enabled: backend.streamAvailable && !!(root.player.current && root.player.current.file) && !backend.streamBusy
            onClicked: backend.streamFile(root.player.current.file, root.player.current.title)
        }
        Row {
            spacing: Theme.s1
            IconButton { iconName: "pause"; tip: qsTr("Pause on the speaker"); enabled: backend.streamPlaying; onClicked: backend.pauseStream() }
            IconButton { iconName: "play"; tip: qsTr("Continue on the speaker"); onClicked: backend.resumeStream() }
            IconButton { iconName: "x"; tip: qsTr("Stop the speaker"); onClicked: backend.stopStream() }
            IconButton { iconName: "retry"; tip: qsTr("Search for speakers again"); onClicked: backend.scanStreamDevices() }
        }
        Text {
            Layout.fillWidth: true
            text: backend.streamStatus
            visible: text !== ""
            color: Theme.textSecondary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
        }
        Item { Layout.fillHeight: true }
    }

    // ---- the moon system
    Item {
        id: sky
        Layout.fillWidth: true
        Layout.fillHeight: true
        readonly property real cx: width / 2
        readonly property real cy: height / 2
        readonly property real rx: Math.max(40, width / 2 - 46)
        readonly property real ry: Math.max(34, height / 2 - 34)
        function ringFactor(k) { return root.ringCount === 1 ? 1 : 0.62 + 0.38 * k / (root.ringCount - 1) }

        Canvas {
            id: orbits
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.lineWidth = 1
                for (var k = 0; k < root.ringCount; ++k) {
                    var f = sky.ringFactor(k)
                    ctx.strokeStyle = Qt.alpha(root.tint, 0.35)
                    ctx.beginPath()
                    ctx.ellipse(sky.cx - sky.rx * f, sky.cy - sky.ry * f, 2 * sky.rx * f, 2 * sky.ry * f)
                    ctx.stroke()
                }
            }
            Connections { target: sky; function onWidthChanged() { orbits.requestPaint() }
                                       function onHeightChanged() { orbits.requestPaint() } }
            Connections { target: root; function onRingCountChanged() { orbits.requestPaint() } }
            onVisibleChanged: requestPaint()
        }
        Rectangle {                  // the speaker planet in the middle; it glows while music plays on a speaker
            x: sky.cx - 24; y: sky.cy - 24; width: 48; height: 48; radius: 24
            color: backend.streamPlaying ? root.tint : Theme.surface
            border.width: 1.5; border.color: backend.streamPlaying ? root.tint : Qt.alpha(Theme.text, 0.4)
            Icon { anchors.centerIn: parent; name: "speaker"; size: 22; color: backend.streamPlaying ? "#0b0b0c" : Theme.text }
        }
        Repeater {
            model: root.devices
            delegate: Item {
                id: moon
                objectName: "moon"
                required property var modelData
                required property int index
                readonly property var place: root.moonPlace(index)
                readonly property real f: sky.ringFactor(place[0])
                // the moons of a ring are spread evenly, the first one at the top
                readonly property real angle: -Math.PI / 2 + 2 * Math.PI * place[1] / place[2] + (place[0] % 2) * Math.PI / place[2]
                x: sky.cx + sky.rx * f * Math.cos(angle) - width / 2
                y: sky.cy + sky.ry * f * Math.sin(angle) - 17
                width: 84; height: 52
                Accessible.role: Accessible.Button
                Accessible.name: modelData.name || modelData.host || ""
                Accessible.checked: modelData.selected
                Rectangle {
                    id: ball
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 34; height: 34; radius: 17
                    color: modelData.selected ? root.tint : Theme.surface
                    border.width: 2
                    border.color: modelData.selected ? root.tint : (modelData.online ? Theme.success : Qt.alpha(Theme.text, 0.25))
                    opacity: modelData.online || modelData.selected ? 1 : 0.6
                    scale: hover.hovered ? 1.12 : 1
                    Behavior on scale { NumberAnimation { duration: Theme.durFast } }
                    Icon { anchors.centerIn: parent; name: "cast"; size: 16; color: modelData.selected ? "#0b0b0c" : Theme.text }
                }
                Text {
                    anchors.top: ball.bottom; anchors.topMargin: 1
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.name || modelData.host || ""
                    elide: Text.ElideRight
                    color: modelData.selected ? root.tint : Theme.textSecondary
                    font.pixelSize: 10
                    font.weight: modelData.selected ? Font.Bold : Font.Normal
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: backend.selectStreamDevice(modelData.id) }
                ToolTip.visible: hover.hovered
                ToolTip.delay: 500
                ToolTip.text: [modelData.name, modelData.manufacturer, modelData.model, modelData.host,
                               modelData.online ? qsTr("online") : qsTr("not seen in the last search")]
                              .filter(function (t) { return !!t }).join("  ·  ")
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: sky.cy + 30
            visible: root.devices.length === 0
            text: backend.streamScanning ? qsTr("Searching ...") : qsTr("No speaker found yet.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption
        }
    }
}
