import QtQuick

// Film strip with a red selection frame. Drag the red handles to set start/end, drag the frame
// to move the whole range. `startSec`/`endSec` are in seconds; signal `scrubbed` reports the
// time under the finger so a preview can follow.
Item {
    id: root
    property real duration: 0
    property var urls: []
    property real startSec: 0
    property real endSec: 0
    signal scrubbed(real seconds)
    signal edited()

    readonly property color frameColor: "#FF3B30"
    readonly property real minSpan: Math.min(0.5, duration)
    readonly property real x1: duration > 0 ? startSec / duration * width : 0
    readonly property real x2: duration > 0 ? endSec / duration * width : width

    implicitHeight: 72
    Accessible.role: Accessible.Slider
    Accessible.name: qsTr("Selected range of the video")

    Rectangle { anchors.fill: parent; radius: 8; color: "#000000" }
    Row {
        anchors.fill: parent
        Repeater {
            model: root.urls
            delegate: Image {
                required property string modelData
                width: root.width / Math.max(1, root.urls.length)
                height: root.height
                source: modelData
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                sourceSize.height: 120
            }
        }
    }
    // dimmed outside the selection
    Rectangle { x: 0; width: root.x1; height: parent.height; color: "#AA000000" }
    Rectangle { x: root.x2; width: root.width - root.x2; height: parent.height; color: "#AA000000" }
    // red frame
    Rectangle {
        x: root.x1
        width: Math.max(8, root.x2 - root.x1)
        height: parent.height
        color: "transparent"
        border.width: 3
        border.color: root.frameColor
        radius: 4
    }
    Repeater {
        model: 2
        delegate: Rectangle {
            required property int index
            x: index === 0 ? root.x1 - 1 : root.x2 - 11
            width: 12
            height: root.height
            radius: 4
            color: root.frameColor
            Column {
                anchors.centerIn: parent
                spacing: 3
                Repeater { model: 3; Rectangle { width: 2; height: 10; radius: 1; color: "#FFFFFF"; opacity: 0.9 } }
            }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        preventStealing: true
        cursorShape: Qt.SizeHorCursor
        property string mode: ""
        property real grab: 0

        function secAt(px) { return Math.max(0, Math.min(root.duration, px / root.width * root.duration)) }

        onPressed: (e) => {
            if (root.duration <= 0) return
            var nearL = Math.abs(e.x - root.x1) < 18, nearR = Math.abs(e.x - root.x2) < 18
            if (nearL && (!nearR || Math.abs(e.x - root.x1) <= Math.abs(e.x - root.x2))) mode = "start"
            else if (nearR) mode = "end"
            else if (e.x > root.x1 && e.x < root.x2) { mode = "move"; grab = secAt(e.x) - root.startSec }
            else mode = Math.abs(e.x - root.x1) < Math.abs(e.x - root.x2) ? "start" : "end"
            update(e.x)
        }
        onPositionChanged: (e) => update(e.x)
        onReleased: mode = ""

        function update(px) {
            var t = secAt(px)
            if (mode === "start") {
                root.startSec = Math.min(t, root.endSec - root.minSpan)
                root.scrubbed(root.startSec)
            } else if (mode === "end") {
                root.endSec = Math.max(t, root.startSec + root.minSpan)
                root.scrubbed(root.endSec)
            } else if (mode === "move") {
                var span = root.endSec - root.startSec
                var s = Math.max(0, Math.min(root.duration - span, t - grab))
                root.startSec = s
                root.endSec = s + span
                root.scrubbed(s)
            }
            root.edited()
        }
    }
}
