import QtQuick
import QtQuick.Layouts

// One labelled progress bar with its own 0-100 %: caption left, percentage and detail right.
ColumnLayout {
    id: root
    property string caption: ""
    property string detail: ""
    property real value: 0          // 0..1
    property bool waiting: false    // grey, nothing started yet
    spacing: 2

    RowLayout {
        spacing: Theme.s2
        Layout.fillWidth: true
        Text {
            text: root.caption
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
            font.weight: Font.Medium
        }
        Text {
            text: root.detail
            color: Theme.textTertiary
            font.pixelSize: Theme.caption
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: Math.round(root.value * 100) + "%"
            color: root.waiting ? Theme.textTertiary : Theme.text
            font.pixelSize: Theme.caption
            font.weight: Font.Medium
        }
    }
    Rectangle {
        implicitHeight: 4
        radius: 2
        color: Theme.track
        clip: true
        Layout.fillWidth: true
        Accessible.role: Accessible.ProgressBar
        Accessible.name: root.caption + " " + Math.round(root.value * 100) + "%"
        Rectangle {
            height: parent.height
            width: parent.width * Math.max(0, Math.min(1, root.value))
            radius: 2
            color: root.waiting ? Theme.textTertiary : Theme.accentFill
            Behavior on width { NumberAnimation { duration: Theme.durFast } }
        }
    }
}
