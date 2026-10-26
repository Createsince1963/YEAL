import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A fan of songs next to the sun (the player): above it the songs that come next, below it the songs played last. The
// songs fly out of the oval one after the other and an oval ring grows around them; folding them away reverses it.
// A double click on a song plays it. The nearest song to the sun is index 0.
//   dir: -1 = the fan opens upwards (up next), 1 = downwards (played)
Item {
    id: fan
    property var songs: []
    property int dir: -1
    property bool shown: false
    property color tint: Theme.accent
    property string caption: ""
    signal played(int index)

    readonly property int pillH: 34
    readonly property int pitch: 38
    readonly property int pad: 30
    readonly property int count: songs ? songs.length : 0
    readonly property real fanW: Math.min(width, 380)
    implicitHeight: pad * 2 + count * pitch
    height: implicitHeight
    visible: progress > 0.01
    clip: false

    property real progress: shown ? 1 : 0                // 0 folded, 1 open; the songs follow one after the other
    Behavior on progress { NumberAnimation { duration: 520; easing.type: Easing.OutCubic } }
    function stage(i) { return Math.max(0, Math.min(1, progress * 1.7 - i * 0.2)) }

    Canvas {                                             // the oval ring around the songs
        id: ring
        width: fan.fanW + 40
        height: parent.height
        x: (parent.width - width) / 2
        opacity: Math.min(1, fan.progress * 1.4)
        scale: 0.55 + 0.45 * fan.progress
        transformOrigin: fan.dir < 0 ? Item.Bottom : Item.Top
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var a = width / 2 - 2, b = height / 2 - 2
            var g = ctx.createRadialGradient(width / 2, height / 2, Math.min(a, b) * 0.2, width / 2, height / 2, a)
            g.addColorStop(0, Qt.alpha(fan.tint, 0.10))
            g.addColorStop(1, Qt.alpha(fan.tint, 0.0))
            ctx.fillStyle = g
            ctx.beginPath(); ctx.ellipse(2, 2, 2 * a, 2 * b); ctx.fill()
            ctx.lineWidth = 1.2
            ctx.strokeStyle = Qt.alpha(fan.tint, 0.55)
            ctx.beginPath(); ctx.ellipse(2, 2, 2 * a, 2 * b); ctx.stroke()
            ctx.setLineDash([2, 6])
            ctx.strokeStyle = Qt.alpha(fan.tint, 0.28)
            ctx.beginPath(); ctx.ellipse(8, 8, 2 * a - 12, 2 * b - 12); ctx.stroke()
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: fan; function onTintChanged() { ring.requestPaint() } }
        Component.onCompleted: requestPaint()
    }
    Text {                                               // what the fan is, on the far side of the sun
        anchors.horizontalCenter: parent.horizontalCenter
        y: fan.dir < 0 ? 8 : fan.height - height - 8
        text: fan.caption
        color: fan.tint
        opacity: fan.progress
        font.pixelSize: 10; font.letterSpacing: 1.5; font.weight: Font.Bold
    }

    Repeater {
        model: fan.songs
        delegate: Rectangle {
            id: pill
            required property var modelData
            required property int index
            readonly property real t: fan.stage(index)
            readonly property real nearY: fan.dir < 0 ? fan.height - fan.pillH : 0                     // beside the sun
            readonly property real farY: fan.dir < 0 ? fan.height - fan.pad - (index + 1) * fan.pitch + (fan.pitch - fan.pillH) / 2
                                                     : fan.pad + index * fan.pitch + (fan.pitch - fan.pillH) / 2
            width: fan.fanW - 40 - index * 6
            height: fan.pillH
            radius: height / 2
            x: (fan.width - width) / 2
            y: nearY + (farY - nearY) * t
            opacity: t * (1 - 0.13 * index)
            scale: 0.8 + 0.2 * t
            color: hover.hovered ? Qt.alpha(Theme.text, 0.16) : Qt.alpha(Theme.surface, 0.96)
            border.width: 1
            border.color: Qt.alpha(fan.tint, hover.hovered ? 0.9 : 0.45)
            Behavior on color { ColorAnimation { duration: Theme.durFast } }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 4; anchors.rightMargin: 14
                spacing: Theme.s2
                Rectangle {
                    implicitWidth: 26; implicitHeight: 26; radius: 13; color: Theme.field; clip: true
                    Image { anchors.fill: parent; source: pill.modelData.cover || ""; sourceSize.width: 60
                            fillMode: Image.PreserveAspectCrop; asynchronous: true }
                }
                Text {
                    Layout.fillWidth: true
                    text: (pill.modelData.title || "") + (pill.modelData.subtitle ? "  ·  " + pill.modelData.subtitle : "")
                    elide: Text.ElideRight
                    color: Theme.text; font.pixelSize: Theme.footnote
                }
            }
            HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onDoubleTapped: fan.played(pill.index) }
            ToolTip.visible: hover.hovered
            ToolTip.delay: 600
            ToolTip.text: qsTr("Double click to play")
        }
    }
}
