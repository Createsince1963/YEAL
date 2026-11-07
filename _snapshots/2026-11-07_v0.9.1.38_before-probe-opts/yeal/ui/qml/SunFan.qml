import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A vertical list of songs next to the sun (the player), like the library: above the sun the songs that come next, below it the
// songs played last. It is a card in front of the planets (like the queue card) that fades and slides in. A double click plays a
// song. The first song of the list is index 0.
//   dir: -1 = the list opens upwards (up next), 1 = downwards (played)
Rectangle {
    id: fan
    property var songs: []
    property int dir: -1
    property bool shown: false
    property color tint: Theme.accent
    property string caption: ""
    signal played(int index)

    readonly property int rowH: 44
    readonly property int count: songs ? songs.length : 0
    readonly property var ordered: songs || []          // top to bottom in playing order, like the queue

    width: 300
    height: 16 + 18 + count * rowH + 8
    radius: 18
    color: Qt.alpha(Theme.surface, 0.97)
    border.width: 1
    border.color: Qt.alpha(tint, 0.55)
    clip: true

    property real progress: shown ? 1 : 0
    Behavior on progress { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    opacity: progress
    visible: progress > 0.01
    transform: Translate { y: (1 - fan.progress) * (fan.dir < 0 ? 12 : -12) }

    Text {
        id: head
        x: 14; y: 10
        text: fan.caption
        color: fan.tint
        font.pixelSize: Theme.footnote; font.weight: Font.Bold; font.letterSpacing: 1
    }
    Column {
        x: 6; y: 34
        width: parent.width - 12
        Repeater {
            model: fan.ordered
            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                width: parent.width
                height: fan.rowH
                radius: 10
                color: hover.hovered ? Qt.alpha(Theme.text, 0.08) : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6; anchors.rightMargin: 8
                    spacing: Theme.s2
                    Rectangle {
                        implicitWidth: 34; implicitHeight: 34; radius: 5; color: Theme.field; clip: true
                        Image { anchors.fill: parent; source: row.modelData.cover || ""; sourceSize.width: 80
                                fillMode: Image.PreserveAspectCrop; asynchronous: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text { text: row.modelData.title || ""; Layout.fillWidth: true; elide: Text.ElideRight
                               color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium }
                        Text { text: row.modelData.subtitle || ""; Layout.fillWidth: true; elide: Text.ElideRight
                               color: Theme.textSecondary; font.pixelSize: Theme.caption }
                    }
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onDoubleTapped: fan.played(row.index) }
                ToolTip.visible: hover.hovered
                ToolTip.delay: 700
                ToolTip.text: qsTr("Double click to play")
            }
        }
    }
}
