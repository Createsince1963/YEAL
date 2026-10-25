import QtQuick
import QtQuick.Layouts

// One accordion row of the Settings page (SettingsItem). Collapsed by default: icon, label and the current value on one line; a click opens the
// hint and the controls (accordion).
Item {
    id: root
    property string label
    property string hint: ""
    property string icon: "sliders"
    property string summary: ""
    property bool expanded: false
    property bool stacked: Theme.compact
    default property alias control: slot.data
    readonly property bool first: root.parent ? root.parent.children[0] === root : true

    Layout.fillWidth: true
    implicitHeight: col.implicitHeight + 2 * Theme.s2
    Behavior on implicitHeight { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
    clip: true

    Rectangle {
        visible: !root.first
        height: 1
        color: Theme.separator
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s4
    }

    // ---- accordion layout
    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Theme.s2
        anchors.leftMargin: Theme.s4
        anchors.rightMargin: Theme.s4
        spacing: Theme.s2

        RowLayout {
            id: head
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.touch
            spacing: Theme.s3
            Accessible.role: Accessible.Button
            Accessible.name: root.label + (root.summary !== "" ? ": " + root.summary : "")
            Accessible.onPressAction: root.expanded = !root.expanded
            Rectangle {
                implicitWidth: 30; implicitHeight: 30
                radius: 8
                color: root.expanded ? Theme.accentFill : Theme.field
                Icon { anchors.centerIn: parent; size: 17; name: root.icon
                       color: root.expanded ? "white" : Theme.textSecondary }
            }
            Text {
                text: root.label
                color: Theme.text
                font.pixelSize: Theme.body
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                visible: root.summary !== "" && !Theme.compact
                text: root.summary
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                elide: Text.ElideMiddle
                horizontalAlignment: Text.AlignRight
                Layout.maximumWidth: 260
            }
            Icon {
                name: "chevronDown"
                size: 15
                color: Theme.textSecondary
                rotation: root.expanded ? 0 : -90
                Behavior on rotation { NumberAnimation { duration: 120 } }
            }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.expanded = !root.expanded }
        }
        Text {
            visible: root.expanded && root.hint !== ""
            text: root.hint
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            Layout.leftMargin: 30 + Theme.s3
        }
        RowLayout {
            id: slot
            visible: root.expanded
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.leftMargin: 30 + Theme.s3
            Layout.bottomMargin: Theme.s2
        }
    }
}
