import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Content of the "Speaker" planet: a small moon system. The speaker planet is in the middle, the places the music can go
// circle around it as moons; a click on a moon chooses it. Two groups (the buttons WLAN / THIS PC above the sky):
//  - WLAN: the speakers and TVs found in the network (Stream to box); "Play on speaker" sends the song there;
//  - THIS PC: the audio outputs of this computer - Windows shows Bluetooth headphones, HDMI monitors and wired speakers all
//    as outputs, so choosing a moon switches the player to them at once (also while a song plays).
// Left of the sky: the current song, play on the speaker, pause / continue / stop and searching again.
GridLayout {
    id: root
    // wide: the song and the buttons left of the moon system; in a narrow card (the right column) they sit above it
    columns: width < 380 ? 1 : 2
    columnSpacing: Theme.s3
    rowSpacing: Theme.s2
    property var player
    property color tint: Theme.accent
    property string mode: "both"                       // both: WLAN speakers and outputs of this PC; pc: only the outputs of this PC (Bluetooth planet)
    property string group: "pc"                        // wlan | pc
    Component.onCompleted: if (mode !== "pc") backend.scanStreamDevices()      // the network is only searched for the WLAN group

    // the moons of the chosen group, in one form: { id, name, selected, online, icon, tip }
    readonly property var devices: {
        var out = []
        if (group === "wlan") {
            var net = backend.streamDevices
            for (var i = 0; i < net.length; ++i)
                out.push({ id: net[i].id, name: net[i].name || net[i].host || "", selected: !!net[i].selected, online: !!net[i].online, icon: "cast",
                           tip: [net[i].name, net[i].manufacturer, net[i].model, net[i].host,
                                 net[i].online ? qsTr("online") : qsTr("not seen in the last search")].filter(function (t) { return !!t }).join("  ·  ") })
        } else {
            var pc = backend.audioOutputs
            for (var j = 0; j < pc.length; ++j)
                out.push({ id: pc[j].id, name: pc[j].name, selected: !!pc[j].selected, online: true,
                           icon: pc[j].kind === "headphones" ? "headphones" : pc[j].kind === "monitor" ? "window" : "speaker",
                           tip: pc[j].name + (pc[j].isDefault ? "  ·  " + qsTr("system default") : "") })
        }
        return out
    }
    function pick(id) { if (group === "wlan") backend.selectStreamDevice(id); else backend.selectAudioOutput(id) }
    readonly property string playingOn: {
        var pc = backend.audioOutputs
        for (var i = 0; i < pc.length; ++i) if (pc[i].selected) return pc[i].name
        return ""
    }
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
        visible: root.mode !== "pc"
        Layout.preferredWidth: root.columns === 1 ? -1 : 190
        Layout.maximumWidth: root.columns === 1 ? 100000 : 230
        Layout.fillWidth: root.columns === 1
        Layout.fillHeight: root.columns === 2
        spacing: Theme.s2
        Text {
            Layout.fillWidth: true
            text: root.player.current && root.player.current.title ? root.player.current.title : qsTr("Pick a song in the library first.")
            color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            visible: root.group === "pc" && root.playingOn !== ""
            text: qsTr("Playing on: %1").arg(root.playingOn)
            color: root.tint; font.pixelSize: Theme.caption; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
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

    // ---- only the outputs of this PC: what is playing where, and a hint
    ColumnLayout {
        visible: root.mode === "pc"
        Layout.preferredWidth: root.columns === 1 ? -1 : 170
        Layout.maximumWidth: root.columns === 1 ? 100000 : 200
        Layout.fillWidth: root.columns === 1
        Layout.fillHeight: root.columns === 2
        spacing: Theme.s2
        Text {
            Layout.fillWidth: true
            text: qsTr("Play on")
            color: Theme.textSecondary; font.pixelSize: Theme.caption
        }
        Text {
            Layout.fillWidth: true
            text: root.playingOn !== "" ? root.playingOn : qsTr("the system default")
            color: root.tint; font.pixelSize: Theme.footnote; font.weight: Font.Bold
            wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            text: qsTr("Switch your Bluetooth headphones on: Windows lists them as an output and they appear here as a moon. Choose the stereo entry for the best sound.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }
        Item { Layout.fillHeight: true }
    }

    // ---- the moon system
    Item {
        id: sky
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 150
        Layout.minimumWidth: 150
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
        Row {                        // the two groups
            visible: root.mode !== "pc"
            anchors.left: parent.left; anchors.top: parent.top
            spacing: Theme.s3
            z: 3
            Repeater {
                model: [{ v: "pc", t: qsTr("THIS PC") }, { v: "wlan", t: qsTr("WLAN") }]
                delegate: Text {
                    required property var modelData
                    text: modelData.t
                    color: root.group === modelData.v ? root.tint : Theme.textSecondary
                    font.family: "Consolas"; font.pixelSize: 11; font.letterSpacing: 1
                    font.weight: root.group === modelData.v ? Font.Bold : Font.Normal
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.group = modelData.v }
                }
            }
        }
        Rectangle {                  // the speaker planet in the middle; it glows while music plays on a speaker
            x: sky.cx - 24; y: sky.cy - 24; width: 48; height: 48; radius: 24
            color: backend.streamPlaying && root.mode !== "pc" ? root.tint : Theme.surface
            border.width: 1.5; border.color: backend.streamPlaying ? root.tint : Qt.alpha(Theme.text, 0.4)
            Icon { anchors.centerIn: parent; name: root.mode === "pc" ? "bluetooth" : root.group === "pc" ? "headphones" : "speaker"; size: 22
                   color: backend.streamPlaying ? "#0b0b0c" : Theme.text }
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
                Accessible.name: modelData.name
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
                    Icon { anchors.centerIn: parent; name: modelData.icon; size: 16; color: modelData.selected ? "#0b0b0c" : Theme.text }
                }
                Text {
                    anchors.top: ball.bottom; anchors.topMargin: 1
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.name
                    elide: Text.ElideRight
                    color: modelData.selected ? root.tint : Theme.textSecondary
                    font.pixelSize: 10
                    font.weight: modelData.selected ? Font.Bold : Font.Normal
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.pick(modelData.id) }
                ToolTip.visible: hover.hovered
                ToolTip.delay: 500
                ToolTip.text: modelData.tip
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: sky.cy + 30
            visible: root.devices.length === 0
            text: root.group === "wlan" ? (backend.streamScanning ? qsTr("Searching ...") : qsTr("No speaker found yet.")) : qsTr("No audio output found.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption
        }
    }
}
