import QtQuick

// Toggle pill (e.g. optional extras). Emits toggled(checked) on user action only.
Rectangle {
    id: root
    property string text
    property bool checked: false
    signal toggled(bool checked)

    implicitHeight: 32
    width: parent && parent.width > 0 ? Math.min(implicitWidth, parent.width) : implicitWidth     // never wider than its row
    // natural width from the metrics, not from the (elided) Text, so the width binding has no loop
    implicitWidth: Math.min(200, (root.checked ? 20 : 0) + Math.ceil(metrics.advanceWidth) + 2 * Theme.s3)   // long labels elide instead of widening narrow cards
    TextMetrics { id: metrics; text: root.text; font.pixelSize: Theme.footnote }
    radius: height / 2
    color: checked ? Theme.accentSoft : Theme.field
    border.width: activeFocus ? 2 : (checked ? 1 : 0)
    border.color: Theme.accent
    activeFocusOnTab: true
    Keys.onSpacePressed: root.toggled(!root.checked)
    Keys.onReturnPressed: root.toggled(!root.checked)
    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checked: checked

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Icon {
            visible: root.checked
            name: "check"
            size: 14
            strokeWidth: 2.2
            color: Theme.accent
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.text
            width: Math.min(implicitWidth, Math.max(10, root.width - 2 * Theme.s3 - (root.checked ? 20 : 0)))
            elide: Text.ElideRight
            font.pixelSize: Theme.footnote
            color: root.checked ? Theme.accent : Theme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    TapHandler { onTapped: root.toggled(!root.checked) }
}
