import QtQuick
import QtQuick.Layouts

// One row of a SettingsGroup: label (+ optional hint) on the left, control(s) on the right.
// With `stacked: true` the control goes below the label (used on narrow windows and for wide controls).
Item {
    id: root
    property string label
    property string hint: ""
    property bool stacked: Theme.compact
    default property alias control: slot.data
    readonly property bool first: root.parent ? root.parent.children[0] === root : true

    Layout.fillWidth: true
    implicitHeight: Math.max(Theme.touch + 14, inner.implicitHeight + 2 * Theme.s3)

    Rectangle {
        visible: !root.first
        height: 1
        color: Theme.separator
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s4
    }
    GridLayout {
        id: inner
        anchors.fill: parent
        anchors.leftMargin: Theme.s4
        anchors.rightMargin: Theme.s4
        columns: root.stacked ? 1 : 2
        rowSpacing: Theme.s2
        columnSpacing: Theme.s4

        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            Text {
                text: root.label
                color: Theme.text
                font.pixelSize: Theme.body
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Text {
                visible: root.hint !== ""
                text: root.hint
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }
        RowLayout {
            id: slot
            spacing: Theme.s2
            Layout.fillWidth: root.stacked
            Layout.alignment: root.stacked ? Qt.AlignLeft : (Qt.AlignRight | Qt.AlignVCenter)
        }
    }
}
